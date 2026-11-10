# BJT Common-Emitter DC Bias (ENG29 2121)

เว็บแอป Flask สำหรับคำนวณจุดทำงาน DC ของวงจร BJT Common-Emitter แบบ Voltage Divider Bias พร้อมการตรวจสอบข้อมูลเข้า คำเตือนภาวะการทำงาน และการเปรียบเทียบผลกับวิธีคำนวณอิสระ (Nodal Analysis)

## โครงสร้าง
- `bjt.py` — ตรรกะทางวิศวกรรม (คำนวณ/ตรวจสอบ/เปรียบเทียบ) แยกจากเว็บ
- `units.py` — แปลงหน่วยที่เลือกในฟอร์มเป็นหน่วยฐาน (V, Ω) ฝั่ง server
- `diagrams.py` — สร้างผังวงจรและกราฟ load line เป็น inline SVG (ไม่พึ่ง library ภายนอก)
- `app.py` — Flask routes
- `templates/index.html`, `static/style.css` — ส่วนแสดงผล
- `tests/` — ชุดทดสอบ (`unittest`)

## สิ่งที่หน้าเว็บแสดง
1. หัวข้อแลป + ฟอร์มป้อนค่า 7 ตัว (พร้อม dropdown หน่วยต่อช่อง)
2. **ผังวงจร (SVG)** — วงจร CE แบบ voltage divider bias พร้อมค่าที่ป้อน และค่าโหนด VB/VE/VC เมื่อมีผลลัพธ์
3. **DC Bias Results** — VB, VE, VC, VCE, IB, IC, IE พร้อมหน่วย + การ์ดสถานะ (Active / Cutoff / Saturation) และบรรทัดสรุปการเทียบ Thevenin กับ Nodal
4. กราฟ load line (SVG) พร้อมจุด Q; ถ้า Q อยู่นอกเส้นจะ clamp ที่ขอบกราฟและมีหมายเหตุกำกับ
5. ตารางเทียบ Thevenin กับ Nodal analysis (สรุปว่า "ตรงกัน" หรือ "ไม่ตรงกัน") และสูตรอ้างอิง

## การติดตั้งและรัน (Windows / PowerShell)
```powershell
cd bjt-bias
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```
จากนั้นเปิดเบราว์เซอร์ที่ http://127.0.0.1:5000

## รันชุดทดสอบ
```powershell
cd bjt-bias
.\.venv\Scripts\python -m unittest discover -s tests -v
```

## ค่าตัวอย่างสำหรับเดโม (Active region)
ค่าเริ่มต้นในฟอร์ม: `VCC=12.0 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1.0 kΩ, β=100, VBE=0.70 V`
(ทุกช่องมี dropdown หน่วย: แรงดัน V/mV, ความต้านทาน Ω/kΩ/MΩ — แปลงเป็นหน่วยฐานฝั่ง server)

ผลที่คาดหวังโดยประมาณ (วิธี Thevenin มาตรฐาน):
- `IB ≈ 12.3 µA`, `IC ≈ 1.23 mA`, `IE ≈ 1.24 mA`
- `VB ≈ 1.94 V`, `VE ≈ 1.24 V`, `VC ≈ 9.29 V`, `VCE ≈ 8.05 V`
- สถานะ: **Active** และผล Thevenin vs Nodal **ตรงกัน**

> หมายเหตุ: ค่าที่คำนวณได้เป็นวิธี Thevenin แบบเต็ม (รวมการโหลดของฐานด้วย RB)
> จึงต่างจากการประมาณหยาบ `IB = (VBB−VBE)/(β·RE)` ที่ให้ IB ≈ 15 µA, IC ≈ 1.5 mA, VCE ≈ 7.2 V

## สูตรอ้างอิง (Thevenin)
- `VBB = VCC·R2/(R1+R2)`, `RB = R1||R2`
- `IB = (VBB−VBE)/(RB + (1+β)RE)`
- `IC = βIB`, `IE = (1+β)IB`
- `VE = IE·RE`, `VB = VBE+VE`, `VC = VCC−IC·RC`, `VCE = VC−VE`

> หมายเหตุ: แอปใช้แบบจำลองเชิงเส้นและ VBE คงที่ตามที่ป้อน หากเข้าสู่ภาวะ cutoff/saturation จะมีคำเตือนและแสดงค่าตามแบบจำลอง (ไม่ปรับ clamp ค่า VCE)
