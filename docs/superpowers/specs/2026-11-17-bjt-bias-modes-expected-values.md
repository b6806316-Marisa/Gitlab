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

## 6) ตาราง A1–A5 — อ้างอิงผลที่เห็นจริงจาก Browser

ค่า default ที่ใช้ร่วมกัน: VCC 12 V, RC 2.2 kΩ, β 100, VBE 0.70 V

| กรณี | โหมด / ค่าที่กรอก | ผลที่เห็นจริง |
|---|---|---|
| A1 | Divider · R1 100 kΩ, R2 22 kΩ, RE 1 kΩ | IC **1.23 mA**, VCE **8.05 V**; VB 1.94, VE 1.24, VC 9.29 V; IB 12.3 µA, IE 1.24 mA; `Thevenin ≈ Nodal: ตรงกัน (Δ 4.34e-19)` |
| A2 | Fixed · RB 1 MΩ (ไม่มีช่อง RE) | IC **1.13 mA**, VCE **9.51 V**; IB 11.3 µA, VC 9.51 V, VE 0.00 V |
| A3 | Emitter · RB 1 MΩ, RE 1 kΩ | IC **1.03 mA**, VCE **8.71 V**; IB 10.3 µA, VE 1.04 V, VC 9.74 V |
| A4 | Emitter · RB 1 MΩ, RE 2 kΩ (เปลี่ยนค่าเดียวจาก A3) | IC **0.94 mA** (ลดลง), VCE **8.03 V**; IB 9.4 µA, VE 1.90 V, VC 9.93 V |
| A5 | Fixed · RB = 0 | `RB ต้องมีค่ามากกว่าศูนย์` · ไม่มีตารางผลลัพธ์ · ไม่มีกราฟ load line |

เหตุผล A4: ตัวส่วน `RB + (1+β)RE` เพิ่มจาก 1.101 MΩ → 1.202 MΩ ทำให้ IB ลด (10.26 → 9.40 µA) และ IC ลดตาม — เป็น negative feedback จาก RE

## 7) นักศึกษาทวนเอง 1 กรณี (ไม่ใช้โค้ดของแอป)

ทวน **A4 (Emitter, RB 1 MΩ, RE 2 kΩ)** ด้วยมือทีละขั้น:

```
IB = (12 − 0.70) / (1,000,000 + 101 × 2,000) = 11.3 / 1,202,000 = 9.4009 µA
IC = 100 × IB = 0.94009 mA        → แอปแสดง 0.94 mA ✅
IE = 101 × IB = 0.94949 mA        → แอปแสดง 0.95 mA ✅
VE = IE × RE = 1.89898 V          → แอปแสดง 1.90 V ✅
VB = VE + VBE = 2.59898 V         → แอปแสดง 2.60 V ✅
VC = 12 − IC × 2,200 = 9.9318 V   → แอปแสดง 9.93 V ✅
VCE = VC − VE = 8.0328 V          → แอปแสดง 8.03 V ✅
```

## 8) การตรวจสมการกับโค้ดที่ AI สร้าง + บทบาท MCP

- **โค้ดที่ AI สร้าง:** `solve_fixed_bias`, `solve_emitter_bias`, `solve_for_mode`, `parse_input(raw, mode)`, `result_payload` และ route ใน `app.py`
- **วิธีตรวจอิสระ:** เขียนสคริปต์แทนค่าลงสูตรสไลด์โดยตรง **ไม่ import `bjt.py`/`app.py`** แล้วเทียบผลกับ (1) Flask test client, (2) Browser จริง, (3) การคำนวณด้วยมือข้อ 7 — ทุกทางให้ผลตรงกันถึงตัวเลขที่แสดง
- **การคงผลเดิมของ Divider:** เปรียบเทียบ HTML ที่เรนเดอร์ก่อน/หลังแก้ 6 สถานการณ์ (default, saturation, cutoff, mV/Ω, ช่องว่าง, หน่วยผิด) — ทุกตัวเลข/หน่วย/ข้อความ status/ค่า Δ เหมือนเดิม เปลี่ยนแต่ whitespace และแท็บนำทาง
- **บทบาท MCP:** MCP (Model Context Protocol) คือสะพานที่ให้โมเดลเรียกเครื่องมือภายนอก เช่น Playwright `browser_navigate` / `browser_snapshot` เพื่อเปิดหน้าเว็บ อ่าน accessibility snapshot กรอกฟอร์มและกดปุ่ม **ในเซสชันนี้ไม่มี Playwright MCP** (`search(namespace:"playwright")` คืนค่าเป็นศูนย์ และ `list_mcp_resources` ไม่พบ server) จึงใช้เครื่องมือ browser ในตัว OpenCode (`tabs.open`, `snapshot`, `navigate`, `evaluate`) แทน ซึ่งทำหน้าที่เท่ากัน
- **ให้คะแนนเท่ากันทุกวิธี:** ผลจากสคริปต์อิสระ, Flask test client, Browser/MCP และการทวนด้วยมือ มีน้ำหนัก **เท่ากัน** — เกณฑ์ผ่านคือต้องตรงกันทุกวิธี ไม่มีการให้สิทธิ์วิธีใดวิธีหนึ่งเป็นพิเศษ

## 9) ข้อจำกัดที่ตรวจแล้ว

- แบบจำลองเชิงเส้นไม่ clamp ค่า VCE — เคส RC=100 kΩ ได้ Fixed −228.43 V / Emitter −187.90 V พร้อมการ์ด `Saturation — linear model invalid` (ค่าติดลบเป็นสัญญาณว่าสมการหลุดขอบเขต ไม่ใช่แรงดันจริง)
- หน้า GET แรกเริ่มวาดผังด้วยค่าที่แปลงเป็น SI แล้ว (แก้ใน commit `8580d61`) จึงไม่เกิดป้าย `470 Ω` ขณะฟอร์มแสดง `470 kΩ`
