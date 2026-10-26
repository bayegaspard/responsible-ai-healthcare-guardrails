# Start the demo on Windows. Run from the repository root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\run.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path .venv)) { Write-Host "Run scripts\setup.ps1 first."; exit 1 }
& .\.venv\Scripts\python.exe app\app.py
