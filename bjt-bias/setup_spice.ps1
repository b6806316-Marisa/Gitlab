# Portable ngspice installer for Lab 04 (no admin rights required)
# Run from the bjt-bias folder: .\setup_spice.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating .venv ..." -ForegroundColor Yellow
    python -m venv .venv
}
& $venvPython -m pip install -q -r requirements.txt

$existing = Get-ChildItem "tools\ngspice" -Recurse -Filter "ngspice_con.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $existing) { $existing = Get-ChildItem "tools\ngspice" -Recurse -Filter "ngspice.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 }
if (-not $existing) {
    New-Item -ItemType Directory -Force -Path "tools" | Out-Null
    $archive = "tools\ngspice-47.7z"
    if (-not (Test-Path $archive)) {
        Write-Host "Downloading ngspice 47 (~14 MB), first time only ..." -ForegroundColor Yellow
        $url = "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47_64.7z"
        curl.exe -L --fail --retry 2 -o $archive $url
        if ($LASTEXITCODE -ne 0) { throw "curl failed to download ngspice ($LASTEXITCODE)" }
    }
    $magic = [System.IO.File]::ReadAllBytes((Resolve-Path $archive))[0..3]
    if ($magic[0] -ne 0x37 -or $magic[1] -ne 0x7A -or $magic[2] -ne 0xBC -or $magic[3] -ne 0xAF) {
        throw "Downloaded file is not a 7z archive. Place ngspice-47_64.7z at tools\ngspice-47.7z manually."
    }
    Write-Host "Extracting to tools\ngspice ..." -ForegroundColor Yellow
    & $venvPython -c "import py7zr,sys; py7zr.SevenZipFile(sys.argv[1]).extractall(sys.argv[2])" $archive "tools\ngspice"
    $existing = Get-ChildItem "tools\ngspice" -Recurse -Filter "ngspice_con.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $existing) { $existing = Get-ChildItem "tools\ngspice" -Recurse -Filter "ngspice.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 }
}
if (-not $existing) { throw "ngspice_con.exe not found after installation" }

Write-Host "ngspice executable: $($existing.FullName)" -ForegroundColor Green
& $existing.FullName -v
Write-Host "Optional override: set NGSPICE_BIN to the path above" -ForegroundColor Green
