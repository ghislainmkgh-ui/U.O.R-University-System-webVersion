$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Root "venv\Scripts\python.exe"
$Requirements = Join-Path $Root "backend\requirements.txt"

if (-not (Test-Path $VenvPython)) {
    py -3.11 -m venv (Join-Path $Root "venv")
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $Requirements
