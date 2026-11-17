# BJT Bias Modes — Expected Values (Browser Acceptance Table)

**วันที่:** 2026-11-17
**วิธีคำนวณ:** แทนค่าลงสูตรในสไลด์โดยตรง (สคริปต์แยก ไม่ import `bjt.py`/`app.py`)
**ตรวจแล้ว:** Browser `http://127.0.0.1:5000/` — ผลตรงทุกช่อง (ดูหลักฐานท้ายไฟล์)

## 1) เคสปกติ (ค่า default ของแต่ละโหมด)

| โหมด | อินพุต | VB | VE | VC | VCE | IB | IC | IE | สถานะ |
|---|---|---|---|---|---|---|---|---|---|
| Divider | VCC 12.0 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1.0 kΩ, β 100, VBE 0.70 V | 1.94 V | 1.24 V | 9.29 V | 8.05 V | 12.3 µA | 1.23 mA | 1.24 mA | Active + ตรงกัน |
| Fixed | VCC 12.0 V, RB 470 kΩ, RC 2.2 kΩ, β 100, VBE 0.70 V | 0.70 V | 0.00 V | 6.71 V | 6.71 V | 24 µA | 2.4 mA | 2.43 mA | Active |
| Emitter | VCC 12.0 V, RB 470 kΩ, RC 2.2 kΩ, RE 1.0 kΩ, β 100, VBE 0.70 V | 2.70 V | 2.00 V | 7.65 V | 5.65 V | 19.8 µA | 1.98 mA | 2 mA | Active |

> ตัวเลขเป็นข้อความที่หน้าเว็บแสดง (แรงดัน 2 ตำแหน่ง, กระแส 3 significant digits)

## 2) เคสสลับหน่วย (ต้องได้ผลเท่ากับข้อ 1 เป๊ะ)

| โหมด | อินพุตที่กรอก | ผลที่ต้องได้ |
|---|---|---|
| Fixed | VCC 12000 mV, RB 470000 Ω, RC 2200 Ω, β 100, VBE 700 mV | เท่ากับ Fixed ในข้อ 1 |
| Emitter | VCC 12000 mV, RB 470000 Ω, RC 2200 Ω, RE 1000 Ω, β 100, VBE 700 mV | เท่ากับ Emitter ในข้อ 1 |
| Divider | VCC 12000 mV, R1 100000 Ω, R2 22000 Ω, RC 2200 Ω, RE 1000 Ω, β 100, VBE 700 mV | เท่ากับ Divider ในข้อ 1 |

## 3) เคสผิดพลาด (ต้องขึ้นข้อความ ไม่คำนวณ)

| โหมด | กรอก | ข้อความที่ต้องเห็น |
|---|---|---|
| Fixed | RB = 0 | `RB ต้องมีค่ามากกว่าศูนย์` |
| Fixed | RB ว่าง | `กรุณาระบุค่า RB` |
| Fixed | RB = abc | `RB ต้องเป็นตัวเลขที่ถูกต้อง` |
| Emitter | RE ว่าง | `กรุณาระบุค่า RE` |
| Emitter | RE = 0 | `RE ต้องมีค่ามากกว่าศูนย์` |
| ทุกโหมด | VBE = 15 V (VCC 12 V) | `VBE ต้องอยู่ระหว่าง 0 ถึง VCC (น้อยกว่า VCC)` |
| ทุกโหมด | หน่วย `furlong` | `... ไม่รู้จักหน่วย 'furlong' ...` |

## 4) เคสอิ่มตัว (ต้องขึ้นการ์ดแดง + ค่าไม่ถูก clamp)

| โหมด | กรอก | VC | VCE | สถานะ |
|---|---|---|---|---|
| Fixed | RC = 100 kΩ | −228.43 V | −228.43 V | Saturation — linear model invalid |
| Emitter | RC = 100 kΩ | −185.90 V | −187.90 V | Saturation — linear model invalid |

## 5) หลักฐานการตรวจ Browser (2026-11-17)

- Divider: `VB 1.94 / VE 1.24 / VC 9.29 / VCE 8.05 / IB 12.3 µA / IC 1.23 mA / IE 1.24 mA` · `Thevenin ≈ Nodal: ตรงกัน (Δ 4.34e-19)`
- Fixed: `VB 0.70 / VE 0.00 / VC 6.71 / VCE 6.71 / IB 24 µA / IC 2.4 mA / IE 2.43 mA` · ไม่มีตารางเทียบ (ถูกต้องตามโหมด)
- Emitter: `VB 2.70 / VE 2.00 / VC 7.65 / VCE 5.65 / IB 19.8 µA / IC 1.98 mA / IE 2 mA`
- สลับหน่วย Fixed (mV/Ω) → ผลเท่าเดิมทุกช่อง
- Fixed RB=0 → `RB ต้องมีค่ามากกว่าศูนย์`; Emitter RE ว่าง → `กรุณาระบุค่า RE`
- Fixed RC=100 kΩ → `Saturation — linear model invalid`, VCE = −228.43 V (ไม่ clamp)
- ผังวงจร: Fixed มี RB ไม่มี RE; Emitter มี RB + RE; Divider มี R1/R2/RE
- Console: ไม่มี error
