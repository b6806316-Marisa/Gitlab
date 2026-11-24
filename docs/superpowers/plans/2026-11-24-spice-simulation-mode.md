# SPICE Simulation Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มหน้า `/spice` ที่รัน ngspice จริงสำหรับวงจร CE Voltage Divider (`.op`, `.ac`, `.tran`) แสดงตัวเลข กราฟ และ provenance โดยไม่กระทบ DC Bias 3 โหมดเดิม

**Architecture:** `spice.py` สร้าง netlist จากค่าที่ validate แล้ว, เรียก `ngspice -b` ผ่าน `subprocess`, parse log/`wrdata` CSV; `spice_plots.py` วาดกราฟ matplotlib เป็น SVG; `spice_routes.py` เป็น Blueprint แยกจาก route เดิม; template/สไตล์ใหม่หนึ่งชุด

**Tech Stack:** Python 3.12, Flask, matplotlib (Agg), py7zr (setup เท่านั้น), ngspice 47 portable

**Spec:** `docs/superpowers/specs/2026-11-24-spice-simulation-mode-design.md`

## Global Constraints

- ห้ามแก้ `bjt.py`, `diagrams.py`, `units.py`, `tests/` เดิม — เทสต์เดิม 58 ตัวต้องผ่าน
- `app.py` เพิ่มได้เฉพาะ import + `register_blueprint` ของ `spice_routes`
- อินพุตทุกช่องต้องผ่าน `float()` + ช่วงค่า; ห้ามเอา string ผู้ใช้ต่อเข้า netlist โดยตรง
- หน่วยในฟอร์มคงที่: V, kΩ, µF, mV, Hz, µs, ms — แปลงเป็น SI ครั้งเดียวใน `parse_spice_form`
- จำกัด ngspice 15 วินาทีต่อ analysis; ไฟล์ชั่วคราวอยู่ `bjt-bias/var/spice/` (gitignored)
- ไม่ใช้ JavaScript; กราฟเป็น SVG ฝังในหน้า
- เครื่องที่ไม่มี ngspice ต้องเห็นคำแนะนำรัน `setup_spice.ps1` ไม่ใช่ 500
- ค่า default: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ, C1 10 µF, CE 100 µF, C2 10 µF, BF 200, SIN 10 mV @ 1 kHz, AC 10 Hz–1 MHz 50 pts/dec, tran 0–200 ms step 20 µs
- เทสต์ใหม่ใช้ `unittest` (คลาส `TestCase`) ตามสไตล์เดิม; integration test ใช้ `skipUnless(find_ngspice())`

## Review Focus

1. ไม่มี ngspice ในเครื่อง → หน้า `/spice` ต้องแสดงวิธีติดตั้ง ไม่ crash (Task 7)
2. ngspice เขียน CSV ว่าง/ผิดรูป → ต้องแจ้ง error พร้อม log ไม่ใช่กราฟเปล่า (Task 5)
3. ค่าที่ทำให้ netlist พัง (0, ติดลบ, `1e309`, ตัวอักษร) → ต้องถูกปฏิเสธก่อนรัน (Task 2)
4. เวลา transient สั้นเกินไป → กราฟต้องไม่หลอกว่าเป็น steady state (Task 6/7: default 200 ms + ข้อความ "startup")
5. แก้ template/nav แล้ว 3 โหมดเดิมหรือเทสต์เดิมพัง → รัน 58 เทสต์ทุก task ที่แตะ app/template (Task 7)

---

### Task 1: ติดตั้ง ngspice แบบ portable + dependency

**Files:**
- Create: `bjt-bias/setup_spice.ps1`
- Modify: `bjt-bias/requirements.txt`
- Modify: `.gitignore`
- Test: รันคำสั่งจริง (ไม่มี unittest)

**Interfaces:**
- Produces: `bjt-bias/tools/ngspice/` ที่มี `ngspice.exe` (gitignored) และคำสั่ง `--version` ใช้ได้

- [ ] **Step 1: เพิ่ม dependency** — ต่อท้าย `requirements.txt`

```text
matplotlib>=3.8
py7zr>=0.21
```

- [ ] **Step 2: เพิ่ม ignore** — ต่อท้าย `.gitignore`

```text
bjt-bias/tools/
bjt-bias/var/
```

- [ ] **Step 3: เขียน `setup_spice.ps1`** ให้: ตรวจ `tools/ngspice/**/ngspice.exe` ก่อน; ถ้าไม่มี ดาวน์โหลด `https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/ngspice-47_64.7z/download` ไป `tools/ngspice-47.7z`; ติดตั้ง/ใช้ `py7zr` จาก venv เพื่อแตกไป `tools/ngspice/`; ค้นหา `ngspice.exe` แล้วรัน `--version`; พิมพ์ path สุดท้าย

- [ ] **Step 4: ติดตั้งและตรวจ**

Run: `cd bjt-bias; .\setup_spice.ps1; .\.venv\Scripts\python -m pip install -r requirements.txt`
Expected: พิมพ์เวอร์ชัน ngspice 47 และ path ของ `ngspice.exe`

- [ ] **Step 5: Commit**

```bash
git add bjt-bias/setup_spice.ps1 bjt-bias/requirements.txt .gitignore
git commit -m "chore: add portable ngspice setup and dependencies"
```

### Task 2: `SpiceInput` + validation/unit conversion

**Files:**
- Create: `bjt-bias/tests/test_spice.py`
- Create: `bjt-bias/spice.py`

**Interfaces:**
- Produces:
  - `SPICE_DEFAULTS: dict[str, str]` (ค่าเริ่มต้นตามหน่วยฟอร์ม)
  - `@dataclass(frozen=True) SpiceInput` fields: `vcc_v, r1_ohm, r2_ohm, rc_ohm, re_ohm, rl_ohm, c1_f, ce_f, c2_f, bf, sin_amp_v, sin_freq_hz, ac_fstart_hz, ac_fstop_hz, ac_ppd, tran_tstep_s, tran_tstop_s`
  - `parse_spice_form(form) -> tuple[SpiceInput | None, list[str]]`
  - `default_spice_form() -> dict[str, str]`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน** ใน `tests/test_spice.py`

```python
import unittest

from spice import default_spice_form, parse_spice_form

DEFAULT_FORM = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "rl": "10",
    "c1": "10", "ce": "100", "c2": "10", "bf": "200",
    "sin_amp": "10", "sin_freq": "1000",
    "ac_fstart": "10", "ac_fstop": "1e6", "ac_ppd": "50",
    "tran_tstep": "20", "tran_tstop": "200",
}


class TestParseSpiceForm(unittest.TestCase):
    def test_defaults_convert_to_si(self):
        inp, errors = parse_spice_form(DEFAULT_FORM)
        self.assertEqual(errors, [])
        self.assertEqual(inp.r1_ohm, 100_000)
        self.assertAlmostEqual(inp.c1_f, 10e-6)
        self.assertAlmostEqual(inp.sin_amp_v, 10e-3)
        self.assertAlmostEqual(inp.tran_tstop_s, 200e-3)

    def test_default_form_is_valid(self):
        inp, errors = parse_spice_form(default_spice_form())
        self.assertEqual(errors, [])
        self.assertIsNotNone(inp)

    def test_rejects_zero_negative_and_non_numeric(self):
        _, errors = parse_spice_form(dict(DEFAULT_FORM, rc="0"))
        self.assertTrue(any("RC" in e for e in errors))
        _, errors = parse_spice_form(dict(DEFAULT_FORM, r1="abc"))
        self.assertTrue(any("R1" in e for e in errors))
        _, errors = parse_spice_form(dict(DEFAULT_FORM, vcc="-12"))
        self.assertTrue(any("VCC" in e for e in errors))

    def test_rejects_bad_frequency_and_time_windows(self):
        _, e1 = parse_spice_form(dict(DEFAULT_FORM, ac_fstop="10"))
        _, e2 = parse_spice_form(dict(DEFAULT_FORM, tran_tstep="20", tran_tstop="0.1"))
        _, e3 = parse_spice_form(dict(DEFAULT_FORM, ac_ppd="2"))
        self.assertTrue(e1)
        self.assertTrue(e2)
        self.assertTrue(e3)

    def test_rejects_netlist_injection_text(self):
        _, errors = parse_spice_form(dict(DEFAULT_FORM, r1="1; shell"))
        self.assertTrue(errors)
```

- [ ] **Step 2: รันให้เห็น fail**

Run: `cd bjt-bias; .\.venv\Scripts\python -m unittest tests.test_spice -v`
Expected: ERROR `ModuleNotFoundError: No module named 'spice'`

- [ ] **Step 3: implement** `spice.py` — dataclass, `SPICE_DEFAULTS`, `default_spice_form`, `parse_spice_form` (แปลง kΩ×1e3, µF×1e-6, mV×1e-3, µs×1e-6, ms×1e-3; ตรวจ finite/positive, `ac_fstop > ac_fstart`, `10 <= ac_ppd <= 500`, `tran_tstep < tran_tstop/10`; ข้อความ error ภาษาไทย `กรุณาระบุค่า ...`, `... ต้องเป็นตัวเลขที่ถูกต้อง`, `... ต้องมีค่ามากกว่าศูนย์`)

- [ ] **Step 4: รันเทสต์**

Run: `cd bjt-bias; .\.venv\Scripts\python -m unittest tests.test_spice -v`
Expected: 5 tests OK

- [ ] **Step 5: Commit**

```bash
git add bjt-bias/spice.py bjt-bias/tests/test_spice.py
git commit -m "feat: add SPICE input model and validation"
```

### Task 3: netlist builder

**Files:**
- Modify: `bjt-bias/spice.py`
- Modify: `bjt-bias/tests/test_spice.py`

**Interfaces:**
- Consumes: `SpiceInput`
- Produces: `build_netlists(inp: SpiceInput) -> dict[str, str]` คีย์ `"op"`, `"ac"`, `"tran"`

- [ ] **Step 1: เพิ่มเทสต์**

```python
class TestNetlists(unittest.TestCase):
    def test_netlists_use_inputs_and_three_analyses(self):
        inp, _ = parse_spice_form(DEFAULT_FORM)
        nets = build_netlists(inp)
        self.assertEqual(set(nets), {"op", "ac", "tran"})
        self.assertIn("R1 1 2 100000", nets["op"])
        self.assertIn("BF=200", nets["op"])
        self.assertIn("ac dec 50 10 1000000", nets["ac"])
        self.assertIn("tran 2e-05 0.2", nets["tran"])
        self.assertIn("@q1[ic]", nets["op"])
```

- [ ] **Step 2: รันให้ fail** — Expected: `NameError: build_netlists`

- [ ] **Step 3: implement** topology ตาม design: nodes 1=VCC, 2=base, 3=collector, 4=emitter, 5=source, 6=out; `VS 5 0 DC 0 AC 1 SIN(0 amp freq)`; model line `Q2N2222` พร้อม `BF` เป็นเลข; control block ต่อ analysis (`op`+`print`, `ac dec`+`set wr_singlescale`+`wrdata ac.csv vdb(6) vp(6) vdb(5)`, `tran`+`wrdata tran.csv v(5) v(6)`)

- [ ] **Step 4: รันเทสต์** — Expected: 6 tests OK

- [ ] **Step 5: Commit** — `feat: generate ngspice netlists`

### Task 4: ngspice runner + `.op` parser + provenance

**Files:**
- Modify: `bjt-bias/spice.py`
- Modify: `bjt-bias/tests/test_spice.py`

**Interfaces:**
- Produces:
  - `find_ngspice() -> pathlib.Path | None`
  - `@dataclass AnalysisRun`: `analysis, netlist, log, rows, exit_code, command, netlist_sha, result_sha, result_name`
  - `@dataclass SpiceRun`: `op: dict[str, float], ac: AnalysisRun, tran: AnalysisRun, version: str, timestamp_utc: str, workdir: str`
  - `run_simulations(inp: SpiceInput, base_dir: pathlib.Path) -> SpiceRun`
  - `parse_op_log(text: str) -> dict[str, float]`

- [ ] **Step 1: เพิ่มเทสต์ parser + integration**

```python
OP_LOG = """v(2) = 1.8e+00
v(3) = 7.3e+00
v(4) = 1.1e+00
v(6) = 7.3e+00
@q1[ic] = 1.2e-03
@q1[ib] = 6.0e-06
@q1[ie] = 1.2e-03
"""

class TestOpParseAndRun(unittest.TestCase):
    def test_parse_op_log(self):
        op = parse_op_log(OP_LOG)
        self.assertGreater(op["vc"], 7)
        self.assertEqual(op["ic"], 1.2e-03)

    @unittest.skipUnless(find_ngspice(), "ngspice not installed")
    def test_real_op_is_in_active_region(self):
        inp, _ = parse_spice_form(DEFAULT_FORM)
        run = run_simulations(inp, Path(tempfile.mkdtemp()))
        self.assertGreater(run.op["vce"], 0.2)
        self.assertGreater(run.op["ic"], 0.2e-3)
        self.assertLess(run.op["ic"], 5e-3)
        self.assertTrue(run.version)
```

- [ ] **Step 2: รันให้ fail** — Expected: `parse_op_log`/`find_ngspice` ไม่มี

- [ ] **Step 3: implement** `find_ngspice` (env → `tools/ngspice/**/ngspice.exe` → PATH), `run_ngspice` (`subprocess.run([...], cwd=workdir, timeout=15, creationflags=CREATE_NO_WINDOW)`, เขียน netlist, เก็บ log, sha256), `parse_op_log` (regex `key = value`, map node 2/3/4/6 → vb/vc/ve/vout, คำนวณ vbe=vb-ve, vce=vc-ve), `run_simulations` (รัน op/ac/tran, workdir `var/spice/<timestamp>-<uuid>`), version จาก `--version`

- [ ] **Step 4: รันเทสต์**

Run: `cd bjt-bias; .\.venv\Scripts\python -m unittest tests.test_spice -v`
Expected: 8 tests OK (integration รันจริงเพราะติดตั้งแล้ว)

- [ ] **Step 5: Commit** — `feat: run ngspice and parse operating point`

### Task 5: parser ของ `.ac`/`.tran` + ตรวจ CSV ว่าง

**Files:**
- Modify: `bjt-bias/spice.py`
- Modify: `bjt-bias/tests/test_spice.py`

**Interfaces:**
- Produces:
  - `parse_wrdata(text: str) -> list[tuple[float, ...]]` (ข้าม comment/บรรทัดว่าง, รองรับ `1.0e+03`)
  - `SpiceError(Exception)` มี `message` ภาษาไทย

- [ ] **Step 1: เพิ่มเทสต์**

```python
class TestWrdata(unittest.TestCase):
    def test_parse_wrdata_columns(self):
        rows = parse_wrdata("10 1.5 -30\n100 2.5 -45\n")
        self.assertEqual(rows, [(10.0, 1.5, -30.0), (100.0, 2.5, -45.0)])

    def test_empty_output_raises_spice_error(self):
        with self.assertRaises(SpiceError):
            parse_wrdata("\n# comment only\n")
```

- [ ] **Step 2: fail → implement → pass**
- [ ] **Step 3: Commit** — `feat: parse ngspice wrdata output`

### Task 6: กราฟ SVG + ตารางเทียบสูตรมือ

**Files:**
- Create: `bjt-bias/spice_plots.py`
- Modify: `bjt-bias/spice.py`
- Modify: `bjt-bias/tests/test_spice.py`

**Interfaces:**
- Produces:
  - `build_plots(op: dict, ac_rows: list[tuple], tran_rows: list[tuple]) -> dict[str, str]` คีย์ `"ac"`, `"tran"` เป็น SVG string (ไม่มี XML header)
  - `hand_calc_op(inp: SpiceInput) -> dict[str, float]` (สูตร DC Bias, VBE=0.7, β=BF)
  - `percent_diff(hand: dict, op: dict) -> dict[str, float]`

- [ ] **Step 1: เพิ่มเทสต์**

```python
class TestPlotsAndCompare(unittest.TestCase):
    def test_plots_are_svg_with_labels(self):
        op = {"vout": 7.0}
        ac = [(10, 20, -10, 0), (100, 30, -30, 0)]
        tran = [(0, 0, 7.0), (0.001, 0.01, 7.01)]
        plots = build_plots(op, ac, tran)
        self.assertTrue(plots["ac"].startswith("<svg"))
        self.assertIn("Frequency", plots["ac"])
        self.assertIn("Gain", plots["ac"])
        self.assertIn("Phase", plots["ac"])
        self.assertTrue(plots["tran"].startswith("<svg"))
        self.assertIn("Time", plots["tran"])

    def test_hand_calc_uses_bf_as_beta(self):
        inp, _ = parse_spice_form(DEFAULT_FORM)
        hand = hand_calc_op(inp)
        self.assertGreater(hand["ic"], 0)
        self.assertGreater(hand["vce"], 0)
```

- [ ] **Step 2: fail → implement** (`matplotlib.use("Agg")`; AC: x log, gain = `vdb(6)-vdb(5)`, phase; tran: Vin mV และ `Vout-vout_op` mV; คืน SVG จาก `savefig(StringIO, format="svg")` แล้วตัด header; `hand_calc_op` ใช้ `IB=(VTH−VBE)/(RTH+(1+β)RE)` กับ RTH=R1||R2)

- [ ] **Step 3: Commit** — `feat: render SPICE plots and hand-calculation comparison`

### Task 7: route + template + nav + เทียบผล/provenance

**Files:**
- Create: `bjt-bias/spice_routes.py`
- Create: `bjt-bias/templates/spice.html`
- Modify: `bjt-bias/app.py` (2 บรรทัด)
- Modify: `bjt-bias/templates/index.html` (เพิ่มลิงก์แท็บ 1 บรรทัด)
- Modify: `bjt-bias/static/style.css`
- Create: `bjt-bias/tests/test_spice_routes.py`

**Interfaces:**
- Consumes: Task 2–6 ทั้งหมด
- Produces: Blueprint `spice_bp` ที่ route `GET/POST /spice`

- [ ] **Step 1: เขียนเทสต์ route**

```python
import unittest
from unittest.mock import patch

from app import create_app
from spice import default_spice_form
import spice_routes

FORM = default_spice_form()


class TestSpiceRoutes(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_spice_shows_form(self):
        body = self.client.get("/spice").get_data(as_text=True)
        for name in ("r1", "rc", "ce", "sin_amp", "ac_fstop", "tran_tstop"):
            self.assertIn(f'name="{name}"', body)

    def test_post_invalid_shows_error(self):
        body = self.client.post("/spice", data=dict(FORM, rc="0")).get_data(as_text=True)
        self.assertIn("RC", body)
        self.assertIn("มากกว่าศูนย์", body)
        self.assertIn("startup", body)  # หมายเหตุ transient

    @patch.object(spice_routes, "find_ngspice", return_value=None)
    def test_missing_ngspice_shows_setup_hint(self, _):
        body = self.client.post("/spice", data=FORM).get_data(as_text=True)
        self.assertIn("setup_spice.ps1", body)

    def test_get_still_serves_bias_modes(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("Voltage Divider Bias", body)
        self.assertIn("Fixed Bias", body)
        self.assertIn("Emitter Bias", body)
```

- [ ] **Step 2: fail → implement** route/template/provenance card (`<details>` netlist, version, command, hashes, log `<pre>`), schematic จากการใช้ `diagrams.schematic_svg` กับค่าที่แปลงแล้ว, ปุ่ม Run, error card, ตารางเทียบ `.op` กับ `hand_calc_op` + `%diff`

- [ ] **Step 3: รันทั้งชุด**

Run: `cd bjt-bias; .\.venv\Scripts\python -m unittest discover -s tests -v`
Expected: 58 เดิม + เทสต์ใหม่ผ่านทั้งหมด

- [ ] **Step 4: Commit** — `feat: add SPICE simulation page`

### Task 8: ตรวจ Browser + README + push

**Files:**
- Modify: `bjt-bias/README.md`
- Add: `docs/superpowers/specs/2026-11-24-spice-evidence.md`

- [ ] **Step 1: รันแอป** (`flask --app app run`) แล้วเปิด `/spice` ผ่าน browser: รัน default, เปลี่ยน R1/RE/ความถี่ 1 ครั้ง, ตรวจ `.op`/`.ac`/`.tran`/provenance
- [ ] **Step 2: เก็บหลักฐาน** — คัดข้อความผล + screenshot; ตรวจว่า netlist/hash/version ตรงกับที่แสดง
- [ ] **Step 3: ตรวจโหมดเดิม** — A1–A5 ยังได้ค่าเดิม; `unittest discover` 58+ ผ่าน
- [ ] **Step 4: README** — วิธีติดตั้ง `setup_spice.ps1`, วิธีรัน, ค่า default, ตัวอย่างผล, ลิงก์ design/plan/evidence
- [ ] **Step 5: Commit + push**

```bash
git add bjt-bias docs/superpowers
git commit -m "docs: document SPICE mode and record browser evidence"
git push origin main
```
