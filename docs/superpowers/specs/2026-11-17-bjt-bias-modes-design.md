# BJT Bias Modes (Divider / Fixed / Emitter) — Short Design

**วันที่:** 2026-11-17
**สถานะ:** อนุมัติและดำเนินการแล้ว (implemented & verified 2026-11-17)

## Intent

เพิ่มโหมดคำนวณ 2 โหมดในแอป Lab 02 เดิม โดย **ผลของโหมด Divider ต้องคงเดิมทุกตัวเลข**:

1. **Fixed Bias** (ไบอัสฐานด้วยตัวต้านทาน RB ตัวเดียวจาก VCC)
2. **Emitter Bias แบบแหล่งจ่ายเดียว** (RB จาก VCC + RE ลงกราวด์)

สมการแยกเป็นฟังก์ชัน Python, ผลลัพธ์ออกเป็น dict ที่มี **ชื่อคีย์และหน่วยเหมือนกันทุกโหมด**, เลือกฟังก์ชันตามโหมด และตรวจอินพุตเฉพาะช่องที่โหมดนั้นใช้

## สิ่งที่มีอยู่ (จากโครง Lab 2)

- `bjt-bias/bjt.py` — `parse_input()` → `BiasInput` (SI: V, Ω) → `solve_thevenin()` / `solve_nodal()` → `BiasResult` (SI)
- `bjt-bias/units.py` — `to_si(text, unit, kind)` แปลงหน่วยฟอร์ม (V/mV, Ω/kΩ/MΩ) เป็น SI ฝั่ง server
- `bjt-bias/app.py` — `FIELD_META` 7 ช่อง, `parse_form()`, route `/` (GET/POST), `build_status()`
- `bjt-bias/diagrams.py` — ผังวงจร divider + load line (inline SVG)
- `bjt-bias/templates/index.html`, `static/style.css` — หน้า 3 คอลัมน์
- tests เดิม 58 tests (bjt 18, app 16, diagrams 15, units 9) — **ห้ามแก้/ห้ามเพิ่ม unittest ใหม่**

## Approaches ที่พิจารณา

| ทาง | ข้อดี | ข้อเสีย | เลือก |
|---|---|---|---|
| A. ขยาย `BiasInput` เดียว + if/else ใน solver เดียว | ชนิดข้อมูลน้อย | สมการปนกัน, `BiasInput` ถูกสร้างแบบ positional ในเทสต์เดิม (เสี่ยงพัง) | ไม่ |
| B. แยก input/solver ต่อโหมด + dispatcher (แนะนำ) | สมการแยกชัด, divider path เดิมไม่ถูกแตะ, ตรงกับ "แยกสมการ" | มีชนิดข้อมูลเพิ่ม 2 ตัว | **ใช้** |
| C. solver รับ/คืน dict ล้วน | ยืดหยุ่น | เสีย type safety, ต้องรื้อเทสต์เดิม | ไม่ |

**UI เลือกโหมด:** แท็บลิงก์ `/?mode=divider|fixed|emitter` (GET) + hidden `mode` ตอน POST — ไม่ใช้ JavaScript, เปลี่ยนโหมดแล้วฟอร์มแสดงเฉพาะช่องของโหมดนั้น

## สูตรที่ใช้ (สมมติฐานจากใบงานมาตรฐาน Boylestad)

### Divider (เดิม — ไม่แก้)
```
VBB = VCC·R2/(R1+R2),  RB = R1||R2
IB  = (VBB − VBE) / (RB + (1+β)·RE)
IC  = β·IB,  IE = (1+β)·IB
VE  = IE·RE,  VB = VBE + VE,  VC = VCC − IC·RC,  VCE = VC − VE
```

### Fixed Bias
```
IB  = (VCC − VBE) / RB
IC  = β·IB,  IE = (1+β)·IB
VB  = VBE,  VE = 0
VC  = VCC − IC·RC,  VCE = VC
```

### Emitter Bias (แหล่งจ่ายเดียว)
```
IB  = (VCC − VBE) / (RB + (1+β)·RE)
IC  = β·IB,  IE = (1+β)·IB
VE  = IE·RE,  VB = VBE + VE,  VC = VCC − IC·RC,  VCE = VC − VE
```

## อินพุตและตรวจสอบตามโหมด

| โหมด | ช่องที่ใช้ | เงื่อนไข |
|---|---|---|
| divider | VCC, R1, R2, RC, RE, β, VBE | VCC>0, R1/R2/RC/RE>0, β>0, 0≤VBE<VCC (เหมือนเดิม) |
| fixed | VCC, RB, RC, β, VBE | VCC>0, RB/RC>0, β>0, 0≤VBE<VCC |
| emitter | VCC, RB, RC, RE, β, VBE | VCC>0, RB/RC/RE>0, β>0, 0≤VBE<VCC |

ช่องที่ไม่ใช้ในโหมดนั้น **ไม่ถูกอ่านและไม่ถูกตรวจ** (ไม่ทำให้ error)

## การแปลงหน่วย

- ทำที่ `app.parse_form(form, mode)` เท่านั้น โดยเรียก `units.to_si()` ต่อช่อง
- `bjt.py` รับ **SI เสมอ** (V, Ω, β ไม่มีหน่วย) — ไม่รู้จัก mV/kΩ
- RB ใช้ dropdown Ω/kΩ/MΩ เหมือน RC/RE; VBE/VCC ใช้ V/mV

## ผลลัพธ์ (dict คีย์/หน่วยตรงกันทุกโหมด)

`bjt.result_payload(result)` คืน:

```python
{
  "VB":  {"value": 1.94, "unit": "V",  "text": "1.94"},
  "VE":  {"value": 1.24, "unit": "V",  "text": "1.24"},
  "VC":  {"value": 9.29, "unit": "V",  "text": "9.29"},
  "VCE": {"value": 8.05, "unit": "V",  "text": "8.05"},
  "IB":  {"value": 12.3, "unit": "µA", "text": "12.3"},
  "IC":  {"value": 1.23, "unit": "mA", "text": "1.23"},
  "IE":  {"value": 1.24, "unit": "mA", "text": "1.24"},
}
```

- คีย์/หน่วยชุดเดียวกันทุกโหมด → template ใช้ตารางเดียว
- Fixed bias: `VE = 0.00 V`, `VB = VBE`
- ยังคืน `BiasResult` ภายใน (SI) เพื่อให้เทสต์เดิมและ `classify()` ใช้ต่อ

## ฟังก์ชันใหม่ / เปลี่ยน

| ไฟล์ | สิ่งที่ทำ |
|---|---|
| `bjt-bias/bjt.py` | `MODE_*`, `MODE_FIELDS`; `FixedBiasInput`, `EmitterBiasInput`; `parse_input(raw, mode="divider")`; `solve_fixed_bias()`, `solve_emitter_bias()`; `solve_for_mode(mode, input)`; `result_payload(result)` — **ไม่แตะ `solve_thevenin`/`solve_nodal`** |
| `bjt-bias/app.py` | `FIELD_META` แยกเป็น field กลาง + รายการต่อโหมด; `parse_form(form, mode)`; อ่าน `mode` จาก query/POST; dispatch; `build_status` ตามโหมด; load line ใช้ `re=0` ใน fixed |
| `bjt-bias/diagrams.py` | `schematic_svg(..., mode="divider")` วาด RB แทน R1/R2 ใน fixed/emitter และไม่มี RE ใน fixed; `load_line_svg` เดิม |
| `bjt-bias/templates/index.html` | แท็บโหมด, hidden `mode`, ฟอร์มตามโหมด, ตารางผลจาก payload, การ์ดเทียบ Thevenin/Nodal เฉพาะ divider, สูตรท้ายหน้าตามโหมด |
| `bjt-bias/static/style.css` | สไตล์แท็บโหมด |
| `bjt-bias/README.md` | โหมด/สูตร/ค่าตัวอย่าง |

**ไม่แตะ:** `units.py`, `tests/`, `electrical.py`, `test_electrical.py`, root `README.md`

## ค่า default ของโหมดใหม่ (ให้ตรงกันตอนตรวจ Browser)

| โหมด | VCC | RB | RC | RE | β | VBE | ผลคาดหวัง |
|---|---|---|---|---|---|---|---|
| fixed | 12 V | 470 kΩ | 2.2 kΩ | — | 100 | 0.70 V | IB 24.0 µA, IC 2.40 mA, IE 2.43 mA, VB 0.70 V, VE 0 V, VC 6.71 V, VCE 6.71 V |
| emitter | 12 V | 470 kΩ | 2.2 kΩ | 1 kΩ | 100 | 0.70 V | IB 19.8 µA, IC 1.98 mA, IE 2.00 mA, VB 2.70 V, VE 2.00 V, VC 7.65 V, VCE 5.65 V |

## การตรวจรับ

1. `python -m unittest discover -s tests -v` → 58 tests OK (ไม่เพิ่มเทสต์)
2. Divider: POST ค่าเดิม → ผลเท่าเดิมเป๊ะ (IB 12.3 µA, IC 1.23 mA, VCE 8.05 V, Active, ตรงกัน)
3. Browser: ตรวจ 3 โหมดเทียบกับ **ตารางของผู้ใช้** (ทั้งค่าและหน่วย)
4. ตรวจเคสผิดพลาด: RB=0, ช่องว่าง, หน่วยแปลก, VBE≥VCC → error ตามโหมด
5. `git status` สะอาด, commit + push

## ยืนยันจากใบงานแล้ว (2026-11-17)

ตารางจากใบงานยืนยันตำแหน่งอุปกรณ์ตรงกับสมมติฐานทุกข้อ:

| โหมด | อินพุตเพิ่ม | ตำแหน่งตัวต้านทาน |
|---|---|---|
| Fixed Bias | RB | RB จาก VCC ไป Base และ Emitter ต่อลงกราวด์โดยตรง |
| Emitter Bias | RB, RE | RB จาก VCC ไป Base และ RE จาก Emitter ลงกราวด์ |
| Voltage Divider Bias | R1, R2, RE | R1 จาก VCC ไป Base, R2 จาก Base ลงกราวด์, RE จาก Emitter ลงกราวด์ |

→ สูตรในหัวข้อก่อนหน้าถูกต้องตามใบงาน (Fixed: ไม่มี RE, VE=0; Emitter: RB ตัวเดียวจาก VCC)

สไลด์ "หากระแสฐาน IB ตามวงจรที่เลือก" ยืนยันสูตรตรงกับข้อเสนอทุกบรรทัด:
`Fixed: IB=(VCC−VBE)/RB` · `Emitter: IB=(VCC−VBE)/(RB+(β+1)RE)` ·
`Divider: IB=(VTH−VBE)/(RTH+(β+1)RE)` โดย `VTH=VCC·R2/(R1+R2)`, `RTH=R1R2/(R1+R2)`
(ในโค้ดเดิมใช้ชื่อ VBB/RB ซึ่งเป็นค่าเดียวกัน) และคำสั่ง "แปลง kΩ→Ω ที่จุดรับข้อมูลครั้งเดียว" ตรงกับ `app.parse_form` → `units.to_si` ในแผนนี้

## สถานะการยืนยัน

- ตารางค่าตรวจ Browser: จัดทำและตรวจครบแล้ว — ดู `2026-11-17-bjt-bias-modes-expected-values.md`
- การอนุมัติแผน: อนุมัติแล้วและลงโค้ดเสร็จ (58 tests OK, Browser ผ่านทุกเคส)
