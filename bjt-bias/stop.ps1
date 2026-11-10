# หยุดเซิร์ฟเวอร์แอปทั้งหมดที่กำลังรันอยู่ (ใช้เมื่อพอร์ต 5000 ถูกจอง)
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
  Where-Object { $_.CommandLine -like "*flask*" -or $_.CommandLine -like "*app.py*" } |
  ForEach-Object {
    Write-Host "หยุด process $($_.ProcessId)"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }
Write-Host "เรียบร้อย - พอร์ต 5000 ว่างแล้ว" -ForegroundColor Green
