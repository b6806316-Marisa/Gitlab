# BJT Common-Emitter DC Bias (ENG29 2121)

เว็บแอป Flask สำหรับคำนวณจุดทำงาน DC ของวงจร BJT Common-Emitter 3 โหมด — **Voltage Divider Bias**, **Fixed Bias** และ **Emitter Bias (แหล่งจ่ายเดียว)** — พร้อมการตรวจสอบข้อมูลเข้าตามโหมด คำเตือนภาวะการทำงาน และ (เฉพาะโหมด Divider) การเปรียบเทียบผลกับวิธีคำนวณอิสระ (Nodal Analysis)

## โครงสร้าง
- `bjt.py` — ตรรกะทางวิศวกรรม (คำนวณ/ตรวจสอบ/เปรียบเทียบ) แยกจากเว็บ
- `units.py` — แปลงหน่วยที่เลือกในฟอร์มเป็นหน่วยฐาน (V, Ω) ฝั่ง server
- `diagrams.py` — สร้างผังวงจรและกราฟ load line เป็น inline SVG (ไม่พึ่ง library ภายนอก)
- `app.py` — Flask routes
- `templates/index.html`, `static/style.css` — ส่วนแสดงผล
- `tests/` — ชุดทดสอบ (`unittest`)

## สิ่งที่หน้าเว็บแสดง
1. แท็บเลือกโหมด 3 แท็บ (Divider / Fixed / Emitter) + ฟอร์มป้อนค่าตามโหมด (5–7 ช่อง พร้อม dropdown หน่วยต่อช่อง)
2. **ผังวงจร (SVG)** — เปลี่ยนตามโหมด: Divider มี R1/R2/RE, Fixed มี RB (Emitter ต่อกราวด์ตรง), Emitter มี RB/RE พร้อมค่าที่ป้อนและค่าโหนด VB/VE/VC เมื่อมีผลลัพธ์
3. **DC Bias Results** — VB, VE, VC, VCE, IB, IC, IE พร้อมหน่วยชุดเดียวกันทุกโหมด + การ์ดสถานะ (Active / Cutoff / Saturation); บรรทัดสรุป Thevenin กับ Nodal แสดงเฉพาะโหมด Divider
4. กราฟ load line (SVG) พร้อมจุด Q (Fixed ใช้ RC อย่างเดียว); ถ้า Q อยู่นอกเส้นจะ clamp ที่ขอบกราฟและมีหมายเหตุกำกับ
5. ตารางเทียบ Thevenin กับ Nodal analysis เฉพาะโหมด Divider และสูตรอ้างอิงตามโหมด

## การติดตั้งและรัน (Windows / PowerShell)
```powershell
cd bjt-bias
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```
จากนั้นเปิดเบราว์เซอร์ที่ http://127.0.0.1:5000

### วิธีที่ง่ายที่สุด
- **เริ่มเซิร์ฟเวอร์:** คลิกขวาที่ `run.ps1` > Run with PowerShell (ปิดตัวเก่าที่ค้าง แล้วเปิดใหม่ให้อัตโนมัติ — กด Ctrl+C เพื่อหยุด)
- **หยุดเซิร์ฟเวอร์ / ล้างพอร์ต 5000:** คลิกขวาที่ `stop.ps1` > Run with PowerShell
- ถ้าเปิดเบราว์เซอร์แล้วขึ้น "site can't be reached" แปลว่าเซิร์ฟเวอร์ยังไม่ได้รัน — ให้รัน `run.ps1` ก่อน

## รันชุดทดสอบ
```powershell
cd bjt-bias
.\.venv\Scripts\python -m unittest discover -s tests -v
```

## ค่าตัวอย่างสำหรับเดโม (Active region)

ทุกช่องมี dropdown หน่วย: แรงดัน V/mV, ความต้านทาน Ω/kΩ/MΩ — แปลงเป็น V/Ω ฝั่ง server ที่จุดรับข้อมูลครั้งเดียว

### Voltage Divider Bias (ค่าเริ่มต้น)
`VCC=12.0 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1.0 kΩ, β=100, VBE=0.70 V`
- `IB ≈ 12.3 µA`, `IC ≈ 1.23 mA`, `IE ≈ 1.24 mA`
- `VB ≈ 1.94 V`, `VE ≈ 1.24 V`, `VC ≈ 9.29 V`, `VCE ≈ 8.05 V`
- สถานะ **Active** และผล Thevenin vs Nodal **ตรงกัน**

> หมายเหตุ: Divider ใช้วิธี Thevenin เต็ม (รวมการโหลดของฐานด้วย RB) จึงต่างจากการประมาณหยาบ
> `IB = (VBB−VBE)/(β·RE)` ที่ให้ IB ≈ 15 µA, IC ≈ 1.5 mA, VCE ≈ 7.2 V

### Fixed Bias (ค่าเริ่มต้นของโหมด)
`VCC=12.0 V, RB=470 kΩ, RC=2.2 kΩ, β=100, VBE=0.70 V`
- `IB ≈ 24.0 µA`, `IC ≈ 2.40 mA`, `IE ≈ 2.43 mA`
- `VB = VBE = 0.70 V`, `VE = 0 V`, `VC = VCE ≈ 6.71 V`

### Emitter Bias (ค่าเริ่มต้นของโหมด)
`VCC=12.0 V, RB=470 kΩ, RC=2.2 kΩ, RE=1.0 kΩ, β=100, VBE=0.70 V`
- `IB ≈ 19.8 µA`, `IC ≈ 1.98 mA`, `IE ≈ 2.00 mA`
- `VB ≈ 2.70 V`, `VE ≈ 2.00 V`, `VC ≈ 7.65 V`, `VCE ≈ 5.65 V`

## สูตรอ้างอิง

### Voltage Divider Bias
- `VTH = VCC·R2/(R1+R2)`, `RTH = R1||R2`
- `IB = (VTH−VBE)/(RTH + (1+β)RE)`
- `IC = βIB`, `IE = (1+β)IB`
- `VE = IE·RE`, `VB = VBE+VE`, `VC = VCC−IC·RC`, `VCE = VC−VE`

### Fixed Bias
- `IB = (VCC−VBE)/RB`
- `IC = βIB`, `IE = (1+β)IB`
- `VE = 0`, `VB = VBE`, `VC = VCC−IC·RC`, `VCE = VC`

### Emitter Bias (แหล่งจ่ายเดียว)
- `IB = (VCC−VBE)/[RB + (1+β)RE]`
- `IC = βIB`, `IE = (1+β)IB`
- `VE = IE·RE`, `VB = VBE+VE`, `VC = VCC−IC·RC`, `VCE = VC−VE`

> หมายเหตุ: แอปใช้แบบจำลองเชิงเส้นและ VBE คงที่ตามที่ป้อน หากเข้าสู่ภาวะ cutoff/saturation จะมีคำเตือนและแสดงค่าตามแบบจำลอง (ไม่ปรับ clamp ค่า VCE)
