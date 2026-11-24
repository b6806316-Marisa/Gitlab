# SPICE Simulation Mode (CE Voltage Divider) — Design

**วันที่:** 2026-11-24
**สถานะ:** รออนุมัติ design (ยังไม่ลงโค้ด)
**เจ้าของงาน:** นักศึกษา ENG29 2121 (Lab 02)

## Intent และเหตุผล

เพิ่มโหมดที่ 4 ในเว็บแอป Flask เดิม เพื่อให้นักศึกษา **รัน ngspice จริง** กับวงจร CE Voltage Divider หนึ่งวงจร ปรับค่าชิ้นส่วน/สัญญาณได้ และเห็นทั้งตัวเลขและกราฟที่มาจากผลรันจริง พร้อมตรวจที่มาของผลได้ (netlist, version, log, hash) และเพื่อน clone repo ไปรันซ้ำได้ โดย **ไม่กระทบ DC Bias 3 โหมดเดิม**

## Goals

1. แท็บใหม่ **SPICE (CE Divider)** ที่ `/spice` — แยกจาก `/?mode=divider|fixed|emitter`
2. ฟอร์มปรับค่าได้: VCC, R1, R2, RC, RE, RL, C1, CE, C2, β (BF) และพารามิเตอร์สัญญาณ (AC amplitude, fstart/fstop/points, SIN amplitude/frequency, tstop/tstep)
3. ปุ่ม Run → รัน ngspice 3 งานจริง: `.op`, `.ac`, `.tran`
4. แสดงผล:
   - `.op`: ตาราง V(b), V(c), V(e), V(out), IC, IB, IE, VBE, VCE
   - `.ac`: กราฟ Bode (gain dB + phase องศา vs frequency log scale)
   - `.tran`: กราฟ Vin/Vout vs time
   - การ์ดเทียบ `.op` กับสูตร DC Bias (β = BF, VBE = 0.7 V) พร้อม % ต่าง
5. การ์ด **Provenance**: netlist ต่อ analysis, คำสั่งที่รัน, `ngspice --version`, timestamp UTC, SHA-256 ของ netlist/ผล, exit code และ log excerpt
6. `setup_spice.ps1` สำหรับติดตั้ง portable ngspice (ทางเลือก A) และ README วิธีรันซ้ำ
7. เทสต์เดิม 58 ตัวต้องผ่านครบ; เพิ่มเทสต์ใหม่แยกไฟล์

## Non-goals

- ไม่เป็น netlist editor ทั่วไป / รองรับวงจรอื่น
- ไม่ทำ model browser หรือเลือก transistor หลายรุ่น (ใช้ Q2N2222 ตัวเดียว)
- ไม่ใช้ JavaScript; ไม่มี auth/ฐานข้อมูล
- ไม่แก้ `bjt.py`, `solve_thevenin`, `solve_nodal`, โหมดเดิมหรือหน้าตาเดิม

## Anti-goals (ถือว่าล้มเหลวถ้าเกิด)

- กราฟ/ตัวเลขที่แต่งขึ้นหรือคำนวณเองแทน ngspice
- โหมดเดิมตัวเลขเปลี่ยน หรือเทสต์เดิมพัง
- เพื่อน clone แล้วรันซ้ำไม่ได้โดยไม่มีคำอธิบาย
- รับค่าที่ทำให้เกิด netlist injection หรือรันค้างเกินเวลา

## Constraints

- Windows + PowerShell; ไม่ต้องสิทธิ์ admin
- ต้องรันได้หลัง `setup_spice.ps1` ครั้งเดียว (ต่อเน็ตครั้งแรกเท่านั้น)
- ngspice 47 (SourceForge `ngspice-47_64.7z`) — ตรวจโครงสร้างไฟล์จริงตอน implement
- อินพุตทุกช่องเป็นตัวเลขผ่าน `float()` + ช่วงค่าที่สมเหตุสมผล (กัน netlist injection)
- จำกัดเวลา ngspice ต่อ analysis (timeout ~15 s)
- หน้าเว็บเป็น server-rendered; กราฟฝังในหน้าเป็น SVG/PNG จาก matplotlib
- ไฟล์ชั่วคราวอยู่ `bjt-bias/var/spice/` (gitignored)

## Approaches (ติดตั้ง ngspice)

| ทาง | ข้อดี | ข้อเสีย | สรุป |
|---|---|---|---|
| **A. Setup script + portable (เลือก)** | repo ไม่บวม, ไม่ต้อง admin, รันครั้งเดียว | ต่อเน็ตครั้งแรก ~14 MB | **เลือก** |
| B. Chocolatey | โค้ดง่ายสุด | ต้อง admin + เพื่อนต้องมี choco | ไม่เลือก |
| C. ฝัง binary ใน repo | รันซ้ำง่ายสุด | repo บวมถาวร + GPL source offer | ไม่เลือก |

แอปหา ngspice ตามลำดับ: `NGSPICE_BIN` → `bjt-bias/tools/ngspice/**/ngspice.exe` → `ngspice` ใน PATH

## การออกแบบ

### วงจรอ้างอิง (หนึ่งวงจร)

```
VCC ──┬── R1 ──┬── base ── Q1 (Q2N2222)
      │        │              │
      │        R2             ├── collector ── RC ── VCC
      │        │              │
      │       GND             └── emitter ── RE ── GND
      │                              │
      │                             CE (bypass)
      └── (ฝั่งสัญญาณ)
VS ── C1 ── base ; collector ── C2 ── out ── RL ── GND
```

- Q1 = Q2N2222 model, `BF` ปรับได้ (default 200)
- C1 = coupling input, CE = bypass emitter, C2 = coupling output, RL = load
- VS = `DC 0 AC 1 SIN(0 <amp> <freq>)` — ใช้ทั้ง AC และ transient
- ค่า default: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ, C1 10 µF, CE 100 µF, C2 10 µF, BF 200, AC amp 1 mV, AC 10 Hz–1 MHz (50 pts/decade), SIN 10 mV @ 1 kHz, tran 0–5 ms, tstep 5 µs

### โครงสร้างไฟล์

| ไฟล์ | หน้าที่ |
|---|---|
| `bjt-bias/spice.py` | dataclass `SpiceInput`, validate/parse, `build_netlists()`, `run_ngspice()`, parsers (`op`/`ac`/`tran`), `build_plots()`, provenance |
| `bjt-bias/spice_routes.py` | Flask Blueprint `/spice` (GET/POST) — ไม่แตะ route เดิม |
| `bjt-bias/templates/spice.html` | ฟอร์ม, ผล 3 การ์ด, provenance |
| `bjt-bias/static/style.css` | เพิ่มสไตล์เฉพาะหน้า SPICE (ไม่แก้ของเดิม) |
| `bjt-bias/setup_spice.ps1` | ดาวน์โหลด + แตก + ตรวจ `ngspice --version` |
| `bjt-bias/tests/test_spice.py`, `test_spice_routes.py` | netlist/parser/validation/route |
| `bjt-bias/requirements.txt` | เพิ่ม `matplotlib`, `py7zr` |
| `README.md` | วิธีติดตั้ง/รัน SPICE + ตัวอย่างผล |

### การรัน ngspice และการอ่านผล

- สร้าง **3 netlist** จาก topology เดียวกัน (แยก control เพื่อ parse ง่าย):
  - `op.cir`: `.op` + `print` ค่า node/device → parse จาก log
  - `ac.cir`: `.ac dec <n> <fstart> <fstop>` + `set wr_singlescale` + `wrdata ac.csv vdb(out) vp(out)`
  - `tran.cir`: `.tran <tstep> <tstop>` + `wrdata tran.csv v(in) v(out)`
- รันด้วย `subprocess.run([ngspice, "-b", "-o", log, netlist], cwd=workdir, timeout=15, capture_output=True)`
- ตรวจ exit code + ไฟล์ CSV มีข้อมูล; ถ้าผิดพลาดแสดง log excerpt ไม่ crash
- เก็บ `workdir = var/spice/<timestamp>-<short-uuid>/` และเก็บ manifest JSON (netlist, version, hashes, เวลา)

### กราฟ

- ใช้ matplotlib (Agg) สร้าง SVG แล้วฝัง inline (ไม่พึ่ง JS)
- AC: แกน x log, แกนซ้าย gain dB, แกนขวา phase (°), grid, ชื่อ/หน่วยชัด
- Tran: แกน x ms, แกน y mV; เส้น Vin และ Vout พร้อม legend
- ถ้า matplotlib ไม่มี → หน้าแจ้งข้อผิดพลาดพร้อมวิธีติดตั้ง (ไม่ทำให้โหมดอื่นพัง)

### Provenance

แสดงในหน้า:
- netlist ทั้ง 3 (ใน `<details>`)
- คำสั่งจริง, เวอร์ชัน ngspice, exit code, เวลา UTC
- SHA-256 ของ netlist และไฟล์ผล
- log excerpt 20 บรรทัดแรก + บรรทัด error ถ้ามี
- หมายเหตุว่ากราฟสร้างจากไฟล์ CSV ที่ ngspice เขียน ไม่ใช่ค่าที่แอปคำนวณ

### Validation และ error handling

- ตัวเลข: finite, VCC/R/C > 0, BF > 0, fstart/fstop > 0 และ fstop > fstart, points 10–500, tstop > 0, tstep > 0 และ tstep < tstop/10
- ช่องว่าง/ตัวอักษร → ข้อความภาษาไทยรูปแบบเดียวกับโหมดเดิม
- ไม่พบ ngspice → การ์ดแดงบอกให้รัน `./setup_spice.ps1` หรือตั้ง `NGSPICE_BIN`
- timeout → ข้อความ "ngspice ใช้เวลาเกิน 15 วินาที" + log เท่าที่มี

### เทสต์

- `test_spice.py`: netlist มีค่าถูกต้อง/ไม่มีอินพุตแปลกปลอม, parser อ่าน CSV ตัวอย่าง, validation ครบเคสผิด
- `test_spice_routes.py`: GET `/spice` แสดงฟอร์ม; POST ค่าผิดแสดง error; POST โดยไม่มี ngspice แสดงคำแนะนำ (ไม่ 500)
- integration: ถ้าเจอ ngspice ให้รัน `.op` จริงและเทียบ VCE กับสูตรภายใน tolerance; ถ้าไม่เจอ → `skipUnless`
- เทสต์เดิม `tests/` ทั้ง 58 ตัวไม่แก้

### ผลกระทบต่อโหมดเดิม

- ไม่แก้ `bjt.py`, `diagrams.py`, `units.py` หรือ route `index`
- `app.py` เพิ่มเพียง `from spice_routes import spice_bp` + `app.register_blueprint(spice_bp)` (2 บรรทัด)
- แท็บใหม่เพิ่มใน template เดิม (ลิงก์ `/spice`) — ไม่แก้ตารางผล/สูตรของ 3 โหมด
- รัน `unittest discover` ต้องได้ 58 เดิม + เทสต์ใหม่ผ่าน

## สิ่งที่เหลือให้ builder ตัดสิน

- โครงสร้างโฟลเดอร์ภายใน `ngspice-47_64.7z` และชื่อ executable จริง
- รูปแบบ/ตำแหน่งไฟล์ CSV และการ parse จุดทศนิยมของ ngspice
- โทนสี/ขนาดกราฟให้เข้ากับ CSS เดิม
- จำนวนจุดสูงสุดที่ยังเรนเดอร์ไหว

## ข้อตัดสินใจหลัง builder check

### 1) โมเดล Q2N2222 — รอผู้ใช้อนุมัติ (มีผลต่อการตีความผล)

- **ทาง A (แนะนำ): โมเดล 2N2222 สมจริง** เก็บ parameter set ไว้ใน `spice.py` (ไม่ดาวน์โหลด) โดย `BF` ถูกแทนค่าจากฟอร์ม → `.op` จะได้ VBE ≈ 0.60–0.65 V และ IC/VC ต่างจากสูตรมือ (VBE = 0.7 V) พอสมควร
  - การ์ดเทียบจะแสดง **สองค่า并列** (สูตรมือ vs ngspice) พร้อมระบุว่าต่างเพราะ VBE ของโมเดล ไม่ใช่ความผิดพลาด
  - integration test ตรวจเพียงค่าสมเหตุสมผล (finite, VCE > 0.2 V, IC ใกล้สูตรภายใน ~30%) ไม่ตั้ง tolerance แคบ
- **ทาง B: ปรับ `IS` ให้ VBE ≈ 0.7 V** เพื่อให้ `.op` ใกล้สูตรมือมาก
  - ข้อดี: ตัวเลขเทียบกันสวย
  - ข้อเสีย: ไม่ใช่ 2N2222 จริง; AC/transient จะไม่สมจริงเท่า

### 2) ค่า default ของ transient — my call

ขยาย `tstop` เป็น **200 ms** และ `tstep` 20 µs (~10,000 จุด) เพื่อให้เห็น steady-state หลัง capacitor charge; จำกัดจุดสูงสุด 200,000 จุด และมีหมายเหตุ "ช่วงต้นเป็น startup transient"

### 3) โหนดและแกนของกราฟ transient — my call

- `in` = โหนดก่อน C1 (แหล่งสัญญาณ) → Vin เป็น sine สะอาด
- พล็อต **Vin (mV)** และ **Vout − Vout(DC)** (mV) โดย `Vout(DC)` มาจาก `.op` ของ ngspice เอง
- ระบุในหน้าและ provenance ว่ามีการลบ DC operating point ออกจาก Vout เพื่อแสดง swing (ค่าที่ลบมาจาก ngspice ไม่ใช่คำนวณเอง)

### 4) AC amplitude — my call

- ใช้ `AC 1` คงที่ใน netlist (linear analysis ไม่ขึ้นกับขนาดสัญญาณ)
- ฟอร์มปรับ "Signal amplitude/frequency" สำหรับ SIN (transient) เท่านั้น
- Bode พล็อต **normalized gain** `vdb(out) − vdb(in)` และ phase ของ out → ไม่มี −60 dB shift
- ระบุใน UI ว่า AC amplitude ไม่มีผลต่อ gain เพราะเป็น线性 analysis
