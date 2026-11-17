# BJT Bias Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มโหมด Fixed Bias และ Emitter Bias (แหล่งจ่ายเดียว) ในแอป Flask เดิม โดยผลของ Divider คงเดิมทุกตัวเลข

**Architecture:** `bjt.py` แยก input/solver ต่อโหมดและมี dispatcher `solve_for_mode()`; ทุกโหมดคืน `BiasResult` (SI) แล้วแปลงเป็น dict กลางด้วย `result_payload()`; `app.py` เลือกช่องฟอร์ม/ตรวจอินพุตตามโหมด; `diagrams.py` วาดผังตามโหมด; template ใช้ตารางผลชุดเดียว

**Tech Stack:** Python 3.12, Flask, inline SVG, stdlib `unittest` (ไม่เพิ่มเทสต์ใหม่)

**Spec:** `docs/superpowers/specs/2026-11-17-bjt-bias-modes-design.md`

## Global Constraints

- **ห้ามแก้หรือเพิ่ม unittest** — เก็บ tests เดิม 58 ตัวให้ผ่านทั้งหมด; ตรวจรับผ่าน Browser ด้วยตารางค่าคาดหวังที่คำนวณแยกจากโค้ดแอป
- **ผล Divider ต้องคงเดิมเป๊ะ** — ห้ามแก้ `solve_thevenin`, `solve_nodal`, `parse_input` path เดิม, `units.py`
- `bjt.py` รับ **SI เท่านั้น** (V, Ω, β ไม่มีหน่วย); การแปลงหน่วยเกิดที่ `app.parse_form()` → `units.to_si()` ครั้งเดียว
- สูตรตามใบงาน: `Fixed: IB=(VCC−VBE)/RB`; `Emitter: IB=(VCC−VBE)/(RB+(1+β)RE)`; `Divider: IB=(VTH−VBE)/(RTH+(1+β)RE)`
- ผลลัพธ์ dict คีย์/หน่วยเดียวกันทุกโหมด: `VB,VE,VC,VCE` = V · `IB` = µA · `IC,IE` = mA
- ช่องที่ไม่ใช้ในโหมดนั้นต้องไม่ถูกอ่าน/ไม่ทำให้ error
- ไม่ใช้ JavaScript; เลือกโหมดด้วยแท็บ GET `/?mode=divider|fixed|emitter`

## Review Focus

1. ค่าเดียวกันแต่หน่วยต่างกัน (RB 470 kΩ vs 470000 Ω) ต้องให้ผลเท่ากัน — ตรวจใน Browser
2. ช่องของโหมดอื่นที่ค้างอยู่ใน POST ต้องไม่ทำให้เกิด error — ตรวจด้วย curl/Browser
3. Fixed bias ต้องได้ `VE = 0.00 V` และ `VB = VBE` ไม่ใช่ค่าค้างจากโหมดก่อน
4. Divider ต้องได้ 12.3 µA / 1.23 mA / 8.05 V และ "ตรงกัน" เหมือนก่อนแก้
5. ป้ายในผังโหมดใหม่ (RB/RE/Q1) ต้องไม่ทับกันและอยู่ใน viewBox

---

### Task 1: Mode logic ใน `bjt.py`

**Files:** Modify `bjt-bias/bjt.py`

**Interfaces:**
- Produces: `MODE_DIVIDER/MODE_FIXED/MODE_EMITTER`, `MODES`, `MODE_LABELS`, `MODE_FIELDS`, `FixedBiasInput`, `EmitterBiasInput`, `parse_input(raw, mode="divider")`, `solve_fixed_bias(b)`, `solve_emitter_bias(b)`, `solve_for_mode(mode, b)`, `result_payload(result)`
- Consumes: `BiasResult`, `classify`, `BiasError` เดิม

- [ ] **Step 1:** เพิ่มค่าคงที่โหมด + `FIELD_LABELS["rb"]="RB"` + `MODE_FIELDS`
- [ ] **Step 2:** แยก body เดิมของ `parse_input` เป็น `_parse_divider(raw)`; `parse_input(raw, mode)` dispatch ไป `_parse_fixed` / `_parse_emitter`; ตัวช่วย `_read_field` ใช้ข้อความ error รูปแบบเดิม
- [ ] **Step 3:** เพิ่ม `FixedBiasInput`, `EmitterBiasInput`, `solve_fixed_bias`, `solve_emitter_bias` (คืน `BiasResult` + warning saturation/near-sat)
- [ ] **Step 4:** เพิ่ม `solve_for_mode` และ `result_payload`
- [ ] **Step 5:** รัน `.\.venv\Scripts\python -m unittest discover -s tests` → 58 OK
- [ ] **Step 6:** Commit `feat: add fixed and emitter bias solvers`

### Task 2: Mode-aware form และ route ใน `app.py`

**Files:** Modify `bjt-bias/app.py`

**Interfaces:**
- Consumes: Task 1 ทั้งหมด
- Produces: `FIELD_META` (dict ทุกช่อง), `fields_for(mode)`, `default_form(mode)`, `default_units(mode)`, `parse_form(form, mode)`, `build_status(primary, bias, rows, mode)`, route รับ `mode`

- [ ] **Step 1:** เปลี่ยน `FIELD_META` เป็น dict 8 ช่อง (เพิ่ม `rb` default 470 kΩ) + `fields_for`
- [ ] **Step 2:** `parse_form(form, mode)` วนเฉพาะ `MODE_FIELDS[mode]`
- [ ] **Step 3:** route อ่าน `mode` จาก query/POST (fallback divider), เรียก `parse_input(si, mode)`, `solve_for_mode`, `result_payload`; `compare` เฉพาะ divider
- [ ] **Step 4:** `schematic_for(mode, values, nodes)` และ load line ใช้ `re=0` เมื่อ fixed
- [ ] **Step 5:** `build_status` แสดง VBB เฉพาะ divider; โหมดอื่นใช้ VCE/VCC
- [ ] **Step 6:** รัน suite → 58 OK; smoke GET/POST ด้วย Flask test client
- [ ] **Step 7:** Commit `feat: route bias modes through the app`

### Task 3: ผังวงจรตามโหมดใน `diagrams.py`

**Files:** Modify `bjt-bias/diagrams.py`

**Interfaces:**
- Produces: `schematic_svg(vcc, r1, r2, rc, re, beta, vbe, nodes=None, mode="divider", rb=0.0)`
- Consumes: `_zigzag`, `_line`, `_text`, `_circle` เดิม

- [ ] **Step 1:** เพิ่มพารามิเตอร์ `mode`, `rb` (default ต้องทำให้การเรียกเดิมในเทสต์ยังใช้ได้)
- [ ] **Step 2:** fixed: RB จาก VCC→base, ไม่มี R2/RE, emitter ต่อกราวด์ตรง; emitter: RB + RE; divider: โค้ดเดิม
- [ ] **Step 3:** ย้ายสัญลักษณ์กราวด์ไปใต้สาขาที่ต่อกราวด์จริง (divider x=130, fixed/emitter x=245)
- [ ] **Step 4:** รัน `tests.test_diagrams` + ตรวจผังใหม่ด้วยสคริปต์ overlap (ไม่เพิ่ม unittest)
- [ ] **Step 5:** Commit `feat: draw fixed and emitter bias schematics`

### Task 4: Template + CSS

**Files:** Modify `bjt-bias/templates/index.html`, `bjt-bias/static/style.css`

**Interfaces:**
- Consumes: `mode`, `mode_label`, `modes`, `fields`, `results.payload`, `results.status`, `results.rows`

- [ ] **Step 1:** เพิ่มแท็บโหมด 3 แท็บ + hidden `mode`
- [ ] **Step 2:** ตาราง DC Bias Results วนจาก `results.payload` (คีย์/หน่วยชุดเดียว)
- [ ] **Step 3:** แสดงการ์ดเทียบ Thevenin/Nodal และบรรทัด "ตรงกัน" เฉพาะ divider
- [ ] **Step 4:** สูตรท้ายหน้าเปลี่ยนตามโหมด; หัวข้อการ์ดวงจรตามโหมด
- [ ] **Step 5:** เพิ่มสไตล์ `.mode-tabs`, `.mode-tab`, `.mode-tab.active`
- [ ] **Step 6:** รัน suite → 58 OK
- [ ] **Step 7:** Commit `feat: mode tabs and shared results table`

### Task 5: README + ตารางตรวจรับ + Browser + push

- [ ] **Step 1:** อัปเดต `bjt-bias/README.md` (3 โหมด, สูตร, default, ตัวอย่าง)
- [ ] **Step 2:** สร้างตารางค่าคาดหวังด้วยสคริปต์แยก (ไม่ import `bjt.py`) ตามสูตรใบงาน 3 โหมด + เคส error
- [ ] **Step 3:** เปิดเซิร์ฟเวอร์ 1 instance และตรวจ Browser เทียบตาราง (ค่า/หน่วย/สถานะ/แท็บ)
- [ ] **Step 4:** ตรวจ Divider ยังได้ 12.3 µA / 1.23 mA / 8.05 V / ตรงกัน
- [ ] **Step 5:** รัน suite เต็ม + ตรวจไฟล์แลปเดิมไม่เปลี่ยน
- [ ] **Step 6:** Commit + push `main`

## Completion

`main` สะอาด, 58 tests OK, Browser แสดง 3 โหมดตรงตาราง, Divider ผลเดิม, ไม่มี JavaScript และไม่มีการเพิ่ม unittest
