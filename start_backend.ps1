$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root "venv\Scripts\python.exe"
$Backend = Join-Path $Root "backend"

if (-not (Test-Path $Python)) {
    Write-Error "Venv introuvable: $Python. Lance d'abord: py -3.11 -m venv venv; .\venv\Scripts\python.exe -m pip install -r backend\requirements.txt"
}

Set-Location $Backend
Write-Host "Backend Django: http://127.0.0.1:8000"
Write-Host "Services auto: ESP32/camera + tunnel Super Admin selon Web_app_migration\.env"
& $Python manage.py runserver 127.0.0.1:8000
