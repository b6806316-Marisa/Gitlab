# Lab UI Redesign — Plan (BJT CE DC Bias, ENG29 2121)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ปรับหน้าเว็บให้ตรงกับภาพเป้าหมายของอาจารย์: header + 3 คอลัมน์ (Input / Circuit / DC Bias Results) + การ์ดสถานะ Active region + Week 2 Goal, พร้อม dropdown หน่วยต่อช่อง (V/mV, Ω/kΩ/MΩ)

**Architecture:** โมดูลใหม่ `units.py` แปลงค่าตามหน่วยที่เลือกเป็นหน่วยฐาน (V, Ω) ฝั่ง server โดยไม่ใช้ JS; `bjt.py` (engineering logic) ไม่เปลี่ยน; `app.py` ประกอบข้อมูลให้ template; `diagrams.py` วาดผังวงจรใหม่ตามภาพ (ตัวต้านทานซิกแซ็ก, Q1 NPN) และคงกราฟ load line เดิม

**Tech Stack:** Python 3.12, Flask, stdlib `unittest`, inline SVG

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md` + ไฟล์ภาพเป้าหมายของอาจารย์ (layout ตามภาพ, ตัวเลขผลลัพธ์คำนวณด้วยวิธี Thevenin มาตรฐาน)

## Global Constraints

- หน่วยฐานเดิมของ `bjt.py` เป็น V และ Ω — ห้ามเปลี่ยน signature ของ `parse_input`/`solve_thevenin`/`solve_nodal`
- ไม่มี JavaScript ทั้งหน้า; การแปลงหน่วยทำฝั่ง server
- ค่า default ใหม่ (ตามภาพเป้าหมาย): VCC 12.0 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1.0 kΩ, β 100, VBE 0.70 V
- ผลลัพธ์ที่ถูกต้องของค่า default (Thevenin): IB 12.3 µA, IC 1.23 mA, IE 1.24 mA, VB 1.94 V, VE 1.24 V, VC 9.29 V, VCE 8.05 V, Active
- การ์ดเปรียบเทียบ Thevenin vs Nodal ต้องยังอยู่ (ข้อกำหนดเดิม) + บรรทัดสรุปในการ์ดสถานะ
- หน่วยในป้ายผลลัพธ์: V (3 หลักนัยสำคัญ), µA สำหรับ IB, mA สำหรับ IC/IE

## Review Focus

1. ค่าเดียวกันคนละหน่วย (100 kΩ vs 100000 Ω, 12 V vs 12000 mV) ต้องให้ผลลัพธ์เท่ากันเป๊ะ — Pinned by Task 1 tests.
2. หน่วยที่ไม่รู้จัก/เว้นว่าง ต้องไม่ทำให้แอปพัง และต้องยังรายงานข้อผิดพลาดเดิม — Pinned by Task 1 tests.
3. ค่าที่กรอกต้องถูก echo กลับในฟอร์ม (หน่วยตามที่เลือก) และค่าในผังวงจรต้องแสดง SI เสมอ — Pinned by Task 2 tests.
4. ภาวะ cutoff/saturation ต้องเปลี่ยนการ์ดสถานะจากเขียวเป็นเตือน/แดง พร้อมเหตุผล — Pinned by Task 2 tests.
5. ผังวงจรใหม่ต้องมีป้าย R1/R2/RC/RE/Q1/NPN/VCC และตัวเลขที่ป้อน และยังไม่มีป้ายทับกัน — Pinned by Task 3 tests.

---

### Task 1: หน่วยในฟอร์ม (`units.py`)

**Files:**
- Create: `bjt-bias/units.py`
- Test: `bjt-bias/tests/test_units.py`

**Interfaces:**
- Produces:
  ```python
  VOLTAGE_UNITS = (("v", "V"), ("mv", "mV"))
  RESISTANCE_UNITS = (("ohm", "Ω"), ("kohm", "kΩ"), ("mohm", "MΩ"))
  def to_si(value_text: str, unit_key: str, kind: str) -> str
      # kind: "voltage" | "resistance"; คืนข้อความค่าในหน่วยฐาน
      # ถ้าแปลงไม่ได้ (ค่าว่าง/ไม่ใช่ตัวเลข) คืนค่าเดิม ให้ bjt.parse_input จัดการข้อความต่อ
  def unit_label(kind: str, unit_key: str) -> str
  ```

- [ ] **Step 1: Write failing tests**: `test_voltage_units`, `test_resistance_units`, `test_millivolts_to_volts`, `test_kilo_ohms_to_ohms`, `test_blank_is_unchanged`, `test_non_numeric_is_unchanged`, `test_unknown_unit_falls_back_to_base`, `test_unit_label`.
- [ ] **Step 2: Run** `.\.venv\Scripts\python -m unittest tests.test_units -v` → FAIL (no module `units`).
- [ ] **Step 3: Implement** `units.py` per interface.
- [ ] **Step 4: Run** → OK.
- [ ] **Step 5: Commit** `feat: unit conversion helpers`.

### Task 2: ฟอร์มหน่วย + เลย์เอาต์หน้าใหม่

**Files:**
- Modify: `bjt-bias/app.py`, `bjt-bias/templates/index.html`, `bjt-bias/static/style.css`
- Test: `bjt-bias/tests/test_app.py`

**Interfaces:**
- Consumes: `units.to_si`, `units.VOLTAGE_UNITS`, `units.RESISTANCE_UNITS`
- Produces: `FIELD_META` = รายการ dict `{name, sym, sub, desc, units, default, default_unit}`; `parse_form(form)` → `(si_texts, display_texts)`; หน้าเว็บมี header, 3 คอลัมน์, results panel, status card, Week 2 Goal

- [ ] **Step 1: Write failing tests**: unit select ปรากฏใน GET; POST ค่าเดียวกันคนละหน่วยได้ผลเท่ากัน; หน่วยที่ไม่รู้จักไม่ทำให้พัง; echo ค่าเดิม; หัวข้อ "Lab 02: BJT DC Bias Web App"; มีข้อความ Week 2 Goal; status card เปลี่ยนสีเมื่อเข้า saturation.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**: `app.py` (FIELD_META ใหม่, `parse_form`, context ใหม่: `status` object), `templates/index.html` (header/3 คอลัมน์/results panel/status card/Week 2 Goal/การ์ดเทียบ+สูตร), `style.css` (header, grid 3 คอลัมน์, badges ของหน่วย, สีสถานะ).
- [ ] **Step 4: Run ทั้งชุด** → OK.
- [ ] **Step 5: Commit** `feat: lab-style layout with unit selectors`.

### Task 3: ผังวงจรใหม่ตามภาพ

**Files:**
- Modify: `bjt-bias/diagrams.py`
- Test: `bjt-bias/tests/test_diagrams.py`

**Interfaces:**
- Produces: `schematic_svg(vcc, r1, r2, rc, re, beta, vbe, nodes=None)` — รูปแบบใหม่: ตัวต้านทานซิกแซ็ก, ราง VCC, กราวด์, ป้าย `Q1`, `NPN`, `(β = ...)`

- [ ] **Step 1: Write failing tests**: มี "Q1", "NPN", "R1", "RC", "RE", "R2", "VCC = ... V"; ค่าความต้านทานแสดงเป็น kΩ; ยังไม่มีป้ายทับกัน; geometry อยู่ใน viewBox.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** ผังวงจรใหม่ใน `diagrams.py` (zigzag resistor path, ground symbol, วงจรคอลเลกเตอร์-อีมิตเตอร์).
- [ ] **Step 4: Run ทั้งชุด** → OK.
- [ ] **Step 5: Commit** `feat: redesign schematic to match lab reference`.

### Task 4: README + ตรวจสอบ + push + เดโม

- [ ] **Step 1**: อัปเดต `bjt-bias/README.md` (ค่า default ใหม่ + ผลลัพธ์ที่ถูกต้อง + หมายเหตุหน่วย)
- [ ] **Step 2**: `.\.venv\Scripts\python -m unittest discover -s tests -v` → ผ่านทั้งหมด
- [ ] **Step 3**: ยืนยันไฟล์เดิมของแลป DC ไม่เปลี่ยน
- [ ] **Step 4**: สตาร์ทเซิร์ฟเวอร์ 1 instance และตรวจ GET/POST ด้วยค่า default ใหม่ + ตรวจภาพในเบราว์เซอร์
- [ ] **Step 5**: commit + push `main`

## Completion

`main` สะอาดและ sync กับ `origin/main`, ชุดทดสอบผ่าน, เดโมทำงานบน `http://127.0.0.1:5000/`
