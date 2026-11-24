# Graph Style Change Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** แยก Gain/Phase ของกราฟ AC เป็น 2 panel, คำนวณ phase จากผลต่างจริงของ ngspice และลบการ์ดกราฟ Q-point ออกจากหน้า DC Bias

**Architecture:** ใช้ข้อมูลจาก `wrdata` ของ ngspice เหมือนเดิม เพิ่มคอลัมน์ `vp(5)` เพื่อหัก phase จริง แล้วให้ `spice_plots.build_plots()` วาด 2 subplot บนแกนความถี่ log ร่วมกัน; ลบเฉพาะการ์ด Q-point ใน template ไม่แตะโมดูลคำนวณ

**Tech Stack:** Python 3, Flask, matplotlib (Agg), ngspice 47, unittest

**Spec:** `docs/superpowers/specs/2026-11-24-graph-style-change-design.md`

## Global Constraints

- ห้ามแก้ `bjt.py`, `diagrams.py`, `units.py`
- ผล/graf ต้องมาจากผลรันจริงเท่านั้น ห้าม mock data
- subprocess ต้องเป็น list ไม่ใช้ `shell=True`
- เทสต์เดิมทั้งหมดต้องผ่าน

## Review Focus

- กราฟ AC ต้องมีแกน X log frequency พร้อมหน่วย Hz และแกน Y แยก dB/deg
- phase ต้องเป็นผลต่าง `vp(6) - vp(5)` ไม่ใช่ค่าสัมบูรณ์
- หลังลบการ์ด Q-point หน้า `/` ต้องยังแสดง schematic และผลคำนวณครบ
- กราฟ Transient ยังมีป้ายเวลา/แรงดันและไม่ถูกแทนที่ด้วยภาพจำลอง

---

### Task 1: AC phase from real ngspice data and two-panel plot

**Files:**
- Modify: `bjt-bias/spice.py` (netlist `wrdata` columns)
- Modify: `bjt-bias/spice_plots.py` (add `ac_metrics`, two subplots)
- Modify: `bjt-bias/spice_routes.py` (`_ac_summary`)
- Test: `bjt-bias/tests/test_spice.py`, `bjt-bias/tests/test_spice_routes.py`

**Interfaces:**
- Consumes: `run.ac.rows` (frequency, vdb6, vp6, vdb5, vp5) and `run.op`
- Produces: `ac_metrics(row) -> (gain_db, phase_deg)`; `build_plots(op, ac_rows, tran_rows)` ยังคงคืน dict ของ SVG

- [ ] **Step 1: Write failing tests** — เพิ่มการตรวจ `(gain_db, phase_deg)` ของ `ac_metrics`, คอลัมน์ `vp(5)` ใน netlist และ phase ติดลบNear 180° เมื่อ input เฟส 170°
- [ ] **Step 2: Run `.\.venv\Scripts\python -m unittest tests.test_spice -v`** — Expected: FAIL (ImportError/AssertionError)
- [ ] **Step 3: Implement** — เปลี่ยน `wrdata ac.csv vdb(6) vp(6) vdb(5) vp(5)`; `ac_metrics(row)=(row[1]-row[3], row[2]-row[4])`; วาด 2 subplot แนวตั้งใช้ grid/legend/หน่วย; ให้ `_ac_summary` เรียก `ac_metrics`
- [ ] **Step 4: Run tests** — `tests.test_spice` และ `tests.test_spice_routes` ต้อง PASS; รันจริงแล้ว phase @1kHz ต้องอยู่ในช่วงที่เชื่อถือได้
- [ ] **Step 5: Commit** — `git commit -m "feat: split AC gain/phase panels using real source phase"`

### Task 2: Remove Q-point graph card

**Files:**
- Modify: `bjt-bias/templates/index.html` (remove load-line card)
- Test: `bjt-bias/tests/test_app.py`

**Interfaces:**
- Consumes: existing `render_page` context
- Produces: หน้า `/` ไม่มีข้อความ “กราฟ load line และจุดทำงาน Q”

- [ ] **Step 1: Write failing test** — เปลี่ยน `test_post_valid_shows_schematic_and_load_line` ให้ตรวจว่าไม่มีข้อความกราฟ Q-point แต่ยังมี schematic และ “VB = 1.94 V”
- [ ] **Step 2: Run `tests.test_app -v`** — Expected: FAIL
- [ ] **Step 3: Implement** — ลบ block `<section>` การ์ด load line ออกจาก `templates/index.html` เท่านั้น
- [ ] **Step 4: Run full suite** — 78+ tests ต้อง PASS
- [ ] **Step 5: Commit** — `git commit -m "chore: remove Q-point graph card from DC bias page"`

### Task 3: Evidence and docs

**Files:**
- Modify: `bjt-bias/docs/validation.md`, `bjt-bias/README.md`
- Create: screenshots under `bjt-bias/docs/captures/`

- [ ] **Step 1:** เก็บ screenshot หน้า `/spice` หลังการรันจริง (desktop + mobile) และหน้า `/` ที่ลบการ์ดแล้ว
- [ ] **Step 2:** อัปเดต validation ด้วยผล B1–B8 และหมายเหตุว่า Playwright MCP ไม่มีในเซสชันนี้
- [ ] **Step 3:** Commit และ push ตามความเหมาะสม
