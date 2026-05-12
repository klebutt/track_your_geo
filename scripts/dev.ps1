$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root "tygeo-venv\Scripts\uvicorn.exe"
if (-not (Test-Path $py)) {
  Write-Host "Missing tygeo-venv. See README.md for setup." -ForegroundColor Yellow
  exit 1
}

Write-Host "Starting API on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList @("tygeo.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $root

Start-Sleep -Seconds 2

Write-Host "Starting web on http://localhost:5173 ..." -ForegroundColor Cyan
Set-Location (Join-Path $root "apps\web")
if (-not (Test-Path "node_modules")) {
  npm install
}
npm run dev
