# BJT Common-Emitter DC Bias (ENG29 2121)

เว็บแอป Flask สำหรับคำนวณจุดทำงาน DC ของวงจร BJT Common-Emitter แบบ Voltage Divider Bias พร้อมการตรวจสอบข้อมูลเข้า คำเตือนภาวะการทำงาน และการเปรียบเทียบผลกับวิธีคำนวณอิสระ (Nodal Analysis)

## โครงสร้าง
- `bjt.py` — ตรรกะทางวิศวกรรม (คำนวณ/ตรวจสอบ/เปรียบเทียบ) แยกจากเว็บ
- `app.py` — Flask routes
- `templates/index.html`, `static/style.css` — ส่วนแสดงผล
- `tests/` — ชุดทดสอบ (`unittest`)

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
ค่าเริ่มต้นในฟอร์ม: `VCC=12 V, R1=47 kΩ, R2=10 kΩ, RC=2.2 kΩ, RE=470 Ω, β=150, VBE=0.7 V`

ผลที่คาดหวังโดยประมาณ:
- `IB ≈ 17.74 µA`, `IC ≈ 2.661 mA`, `IE ≈ 2.679 mA`
- `VB ≈ 1.959 V`, `VE ≈ 1.259 V`, `VC ≈ 6.146 V`, `VCE ≈ 4.887 V`
- สถานะ: **Active** และผล Thevenin vs Nodal **ตรงกัน**

## สูตรอ้างอิง (Thevenin)
- `VBB = VCC·R2/(R1+R2)`, `RB = R1||R2`
- `IB = (VBB−VBE)/(RB + (1+β)RE)`
- `IC = βIB`, `IE = (1+β)IB`
- `VE = IE·RE`, `VB = VBE+VE`, `VC = VCC−IC·RC`, `VCE = VC−VE`

> หมายเหตุ: แอปใช้แบบจำลองเชิงเส้นและ VBE คงที่ตามที่ป้อน หากเข้าสู่ภาวะ cutoff/saturation จะมีคำเตือนและแสดงค่าตามแบบจำลอง (ไม่ปรับ clamp ค่า VCE)
