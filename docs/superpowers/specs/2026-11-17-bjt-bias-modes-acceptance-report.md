# BJT Bias Modes — A1–A5 Acceptance Report

**วันที่:** 2026-11-17
**แอป:** `http://127.0.0.1:5000/` (Flask, `bjt-bias`)
**Repo:** https://github.com/b6806316-Marisa/Gitlab/tree/main/bjt-bias
**HEAD:** `7b4c0dd` (previous: `8580d61`, `6d2e768`, `305bb14`, `5bfc51b`, `2532b4c`)

## 1) ตาราง A1–A5 — อินพุต / ค่าคาดหมาย / ผลจริง / หน่วย / วิธีตรวจ / สถานะ

ค่าร่วมทุกกรณี: `VCC = 12.0 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`

| กรณี | อินพุต | ค่าคาดหมาย (หน่วย) | ผลจริงจากหน้าเว็บ (หน่วย) | วิธีตรวจ | สถานะ |
|---|---|---|---|---|---|
| **A1** Divider เดิม | `R1 100 kΩ, R2 22 kΩ, RE 1.0 kΩ` | VB 1.94 V · VE 1.24 V · VC 9.29 V · VCE 8.05 V · IB 12.3 µA · IC 1.23 mA · IE 1.24 mA · Thevenin ≈ Nodal **ตรงกัน** | VB 1.94 V · VE 1.24 V · VC 9.29 V · VCE 8.05 V · IB 12.3 µA · IC 1.23 mA · IE 1.24 mA · `ตรงกัน (Δ 4.34e-19)` | เปิด `/` → กรอกฟอร์ม → submit → อ่านตาราง + บรรทัดเทียบ; เทียบกับค่าอ้างอิงอิสระ | ✅ ผ่าน (ผลเดิมไม่เปลี่ยน) |
| **A2** Fixed | `RB 1 MΩ` (ไม่มีช่อง RE) | VB 0.70 V · VE 0.00 V · VC 9.51 V · VCE 9.51 V · IB 11.3 µA · IC 1.13 mA · IE 1.14 mA | ตรงทุกช่อง · status `Active region approximation OK` | เปิด `/?mode=fixed` → เปลี่ยน RB เป็น `1 MΩ` → submit → อ่านตาราง + รายการช่องฟอร์ม | ✅ ผ่าน (ไม่ต้องกรอก RE) |
| **A3** Emitter | `RB 1 MΩ, RE 1 kΩ` | VB 1.74 V · VE 1.04 V · VC 9.74 V · VCE 8.71 V · IB 10.3 µA · IC 1.03 mA · IE 1.04 mA | ตรงทุกช่อง · status `Active` | เปิด `/?mode=emitter` → เปลี่ยน RB/RE → submit → อ่านตาราง + ผัง + ข้อความผล (ดูหลักฐานข้อ 2) | ✅ ผ่าน (ใช้ RE จริง) |
| **A4** เปลี่ยนค่าเดียว | `RB 1 MΩ, RE 2 kΩ` | IC **ลดลง** จาก A3 → 0.94 mA · VCE 8.03 V · IB 9.4 µA · VE 1.90 V · VC 9.93 V | IC 0.94 mA · VCE 8.03 V · IB 9.4 µA · VE 1.90 V · VC 9.93 V · IE 0.95 mA | ทำนายก่อนว่า IC ลด (RE เพิ่ม → ตัวส่วนเพิ่ม) แล้ว submit จริงเทียบ | ✅ ผ่าน (ทิศทางและตัวเลขตรง) |
| **A5** อินพุตผิด | `RB = 0` (Fixed) | ขึ้นข้อความแก้ RB · ไม่แสดงผลรอบก่อน | `RB ต้องมีค่ามากกว่าศูนย์` · ไม่มีตารางผลลัพธ์ · ไม่มี load line | เปิด `/?mode=fixed` → ใส่ 0 → submit → ตรวจ `ul.error` และจำนวน `.result-table` เทียบ 0 | ✅ ผ่าน |

**หน่วยที่ใช้ตรวจ:** แรงดัน V (แสดง 2 ตำแหน่ง) · IB µA · IC/IE mA (3 significant digits) — ใช้ชุดเดียวกันทุกโหมด

## 2) หลักฐานจากหน้าเว็บ (A3 — Emitter Bias)

ข้อความที่คัดจากหน้าเว็บหลังกด **Calculate DC Bias** (แบบคำต่อคำ):

```text
DC Bias Results
VB 1.74 V   VE 1.04 V   VC 9.74 V   VCE 8.71 V
IB 10.3 µA  IC 1.03 mA  IE 1.04 mA
✓ Active region approximation OK
VCE = 8.71 V > 0.2 V (transistor in active region)
```

ข้อมูลประกอบจากหน้าเดียวกัน:
- แท็บที่ active: `Emitter Bias`
- ผังวงจร: `VCC = 12 V · RB 1000 kΩ · RC 2.2 kΩ · Q1 NPN (β = 100) · RE 1 kΩ · VBE = 0.7 V · VB = 1.74 V · VE = 1.04 V · VC = 9.74 V`
- URL: `http://127.0.0.1:5000/?mode=emitter` · title `Lab 02: BJT DC Bias Web App — ENG29 2121`
- ภาพหน้าจอ (full page): [`evidence/2026-11-17-A3-emitter.jpeg`](evidence/2026-11-17-A3-emitter.jpeg)
- Console error: ไม่มี

## 3) การเปลี่ยนเครื่องมือ — สาเหตุและวิธีที่ใช้แทน

- **ต้องการตามเดิม:** Playwright MCP (`browser_navigate` / `browser_snapshot`)
- **สาเหตุที่ใช้ไม่ได้:** เซสชันนี้ไม่มี Playwright MCP — `search(namespace: "playwright")` คืนรายการว่าง และ `tools.opencode.list_mcp_resources({})` คืน `resources: []`
- **วิธีแทน:** ใช้เบราว์เซอร์ในตัว OpenCode — `tools.browser.tabs.open`, `tools.browser.navigate`, `tools.browser.snapshot`, `tools.browser.evaluate` (กรอกฟอร์ม/g.requestSubmit/อ่านตาราง), `tools.browser.screenshot` — ทำหน้าที่เดียวกัน: เปิดหน้า, อ่าน accessibility snapshot, กรอกฟอร์ม, กดปุ่ม, เก็บหลักฐาน
- บทบาท MCP โดยทั่วไป: เป็นสะพาน (Model Context Protocol) ที่ให้โมเดลเรียกเครื่องมือภายนอก เช่น browser แทนการพิมพ์คำสั่งเอง เมื่อ MCP ตัวใดไม่มี จึงต้องใช้เครื่องมืออื่นที่ให้ผลเท่ากันและระบุไว้ตรง ๆ
- **การให้คะแนน:** ผลจากสคริปต์อิสระ, Flask test client, Browser/MCP และการคำนวณด้วยมือ มีน้ำหนัก **เท่ากัน** — ผ่านเฉพาะเมื่อทุกวิธีตรงกัน

## 4) ค่าอ้างอิงอิสระของโหมดใหม่ (A3 — Emitter Bias)

คำนวณแทนสูตรสไลด์โดยตรง **ไม่ import `bjt.py` หรือ `app.py`** (สคริปต์แยกอิสระ):

| ปริมาณ | สมการ (หน่วย) | ค่า | ค่าที่แอปแสดง |
|---|---|---|---|
| IB | `(VCC − VBE) / [RB + (1+β)RE]` = `(12 V − 0.70 V) / (1,000,000 Ω + 101 × 1000 Ω)` = `11.3 V / 1,101,000 Ω` | `10.2634e-6 A = 10.26 µA` | `10.3 µA` ✅ |
| IC | `β × IB` = `100 × 10.2634 µA` | `1.02634 mA` | `1.03 mA` ✅ |
| IE | `(1+β) × IB` = `101 × 10.2634 µA` | `1.03660 mA` | `1.04 mA` ✅ |
| VE | `IE × RE` = `1.03660 mA × 1000 Ω` | `1.0366 V` | `1.04 V` ✅ |
| VB | `VE + VBE` = `1.0366 V + 0.70 V` | `1.7366 V` | `1.74 V` ✅ |
| VC | `VCC − IC × RC` = `12 V − 1.02634 mA × 2200 Ω` | `9.7421 V` | `9.74 V` ✅ |
| VCE | `VC − VE` = `9.7421 V − 1.0366 V` | `8.7054 V` | `8.71 V` ✅ |

ค่าแตกต่างจากการแสดงผลเกิดจากการ format (แรงดัน 2 ตำแหน่ง, กระแส 3 significant digits) เท่านั้น

## 5) ส่วนที่ AI สร้าง / ส่วนที่นักศึกษาตรวจ / ตำแหน่งโค้ด

**AI (OpenCode) สร้าง:**
- `bjt/bjt.py` — mode constants + `MODE_FIELDS`, `FixedBiasInput`/`EmitterBiasInput`, `_parse_fixed`/`_parse_emitter`, `solve_fixed_bias`, `solve_emitter_bias`, `solve_for_mode`, `result_payload`
- `bjt/app.py` — `FIELD_META`, `fields_for`, `parse_form`, route ตามโหมด, `build_status`, `schematic_for`
- `bjt/diagrams.py` — `schematic_svg(..., mode, rb)`
- `templates/index.html`, `static/style.css` — แท็บโหมด, ตารางผลชุดเดียว, การ์ดเทียบเฉพาะ Divider
- README, design/plan/expected-values/รายงานนี้

**นักศึกษาตรวจ (ต้องลงมือเองจึงนับว่าเป็นการทวนของนักศึกษา):**
- ทวน A3 ด้วยมือตามข้อ 4 แล้วเทียบกับข้อความผลจริงในข้อ 2
- ทวน A1 ว่า Divider ได้ `12.3 µA / 1.23 mA / 8.05 V / ตรงกัน` เหมือนก่อนเพิ่มโหมด
- ทวน A5 ว่า RB = 0 ขึ้น error และไม่แสดงผลเก่า
- ทวน A4 ว่าปรับ RE เป็น 2 kΩ แล้ว IC ลดจริง
- กดสลับหน่วย (เช่น RB 470000 Ω + VBE 700 mV) แล้วเทียบผลกับหน่วย kΩ/V

**ตำแหน่งโค้ดที่เกี่ยวข้อง (บรรทัดปัจจุบัน):**

| สิ่ง | ไฟล์:บรรทัด |
|---|---|
| เลือกฟังก์ชันตามโหมด (dispatcher) | `bjt/bjt.py:434` `solve_for_mode` · `bjt/bjt.py:225` `parse_input(raw, mode)` |
| สมการ Fixed / Emitter | `bjt/bjt.py:388` `solve_fixed_bias` · `bjt/bjt.py:411` `solve_emitter_bias` |
| ส่งผลเป็น dict (คีย์/หน่วยชุดเดียว) | `bjt/bjt.py:443` `result_payload` |
| แปลงหน่วยครั้งเดียวที่จุดรับข้อมูล | `bjt/app.py:117` `parse_form` → `bjt/units.py:32` `to_si` (kΩ→Ω, mV→V) |
| ตรวจอินพุตแยกตามโหมด | `bjt/bjt.py:225` → `_parse_divider` / `_parse_fixed` / `_parse_emitter` |
| Divider เดิม (ไม่แตะ) | `bjt/bjt.py` `solve_thevenin`, `solve_nodal`, `compare` |

**ผลที่ได้:** ทั้งสามโหมดคำนวณถูก หน่วยชัดเจน มีค่าอ้างอิงอิสระ และ Divider ไม่เสียจากการเปลี่ยนแปลง — ตรวจแล้ว 58 unittest ผ่าน + ตาราง A1–A5 ผ่านครบ
