# เริ่มเซิร์ฟเวอร์แอป BJT DC Bias (คลิกขวาที่ไฟล์นี้แล้ว "Run with PowerShell")
# - ปิดตัวเก่าที่ค้างอยู่ก่อน เพื่อไม่ให้ชนพอร์ต 5000
# - สร้าง venv และติดตั้ง Flask ให้อัตโนมัติถ้ายังไม่มี
# - กด Ctrl+C ในหน้าต่างนี้เพื่อหยุดเซิร์ฟเวอร์
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
  Where-Object { $_.CommandLine -like "*flask*" -or $_.CommandLine -like "*app.py*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 800

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "ยังไม่มี .venv - กำลังสร้างและติดตั้ง Flask (ครั้งเดียว)" -ForegroundColor Yellow
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

Write-Host "กำลังเปิด http://127.0.0.1:5000/  (Ctrl+C = หยุด)" -ForegroundColor Green
.\.venv\Scripts\python.exe -m flask --app app run --debug
