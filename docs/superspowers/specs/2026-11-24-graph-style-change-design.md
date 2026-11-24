# Design: แยกแกน Gain/Phase และลบกราฟ Q-point (2026-11-24)

## Intent / why
ผู้ใช้ต้องการกราฟ AC ที่อ่านง่ายขึ้น: แยก Gain (dB) กับ Phase (deg) เป็น 2 panel
บนแกนความถี่ log เดียวกัน และลบการ์ด “กราฟ load line และจุดทำงาน Q” ออกจาก
หน้า DC Bias เนื่องจากไม่ต้องการแสดงผลนั้นอีก

## Goals
- กราฟ AC แสดง 2 subplot แนวตั้ง: Gain (dB) และ Phase (deg) แกน X = Frequency (Hz, log)
- กราฟ Transient ยังแสดง Vin/Vout ตามเวลาพร้อมหน่วย
- ค่า phase ที่แสดงเป็น phase ของ Vout เทียบกับ Vin จากผล ngspice จริง
- ลบการ์ด Q-point ออกจาก `templates/index.html`
- gain/phase/grid/legend ยังคำนวณจากผลรันจริงเท่านั้น ไม่ใช้ mock data

## Non-goals / anti-goals
- ไม่เปลี่ยนสมการ dc_bias/bjt.py, diagrams.py, units.py
- ไม่เปลี่ยนผลคำนวณหรือ 3 โหมด DC Bias เดิม
- ไม่เพิ่ม backend ใหม่ หรือเปลี่ยนวิธีเรียก ngspice แบบ list/subprocess

## Constraints
- ห้ามแก้ `bjt.py`, `diagrams.py`, `units.py`
- เทสต์เดิมทั้งหมดต้องผ่าน
- netlist ต้องยังรันจริงได้ด้วย ngspice 47

## Approaches
1. **แยก 2 subplot ใน matplotlib (เลือก)** — ใช้ผลลัพธ์เดิม เพียงเพิ่ม `vp(5)` ใน netlist
   เพื่อหัก phase แล้ววาด 2 axes; อ่านง่ายและเสี่ยงต่ำสุด
2. ใช้ twin-axis แบบเดิม — ไม่ตรงความต้องการของผู้ใช้
3. เขียน SVG เอง — ไม่คุ้มและเสี่ยงผิดหน่วย/แกน

## Implementation notes
- `spice.py::build_netlists` เปลี่ยนบรรทัด `wrdata ac.csv ...` เป็น
  `wrdata ac.csv vdb(6) vp(6) vdb(5) vp(5)`
- `spice_plots.py` เพิ่ม `ac_metrics(row) -> (gain_db, phase_deg)` และใช้วาด 2 panel
- `spice_routes.py::_ac_summary` ใช้ `ac_metrics` ตัวเดียวกัน
- `templates/index.html` ลบ block การ์ด load line; `tests/test_app.py` ปรับความคาดหวัง
- อัปเดตเทสต์ใน `tests/test_spice.py` ให้ครอบคลุมคอลัมน์ใหม่และ phase difference

## Remaining to builder
- ทำ TDD ให้เทสต์ใหม่แดงก่อนแล้วค่อยแก้
- รันชุดเทสต์ทั้งหมดและเก็บ screenshot ก่อน/หลังจริง
