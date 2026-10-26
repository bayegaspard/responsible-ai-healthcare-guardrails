# One-time setup on Windows. Run from the repository root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> Creating virtual environment in .venv"
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip -q
Write-Host "==> Installing Python packages"
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -q

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "!! Ollama is not installed. Get it from https://ollama.com/download, then rerun this script."
    exit 1
}
Write-Host "==> Pulling models (about 10 GB the first time)"
ollama pull llama3
ollama pull llama3.1

Write-Host "==> Running policy tests"
& .\.venv\Scripts\python.exe -m unittest discover tests -q

Write-Host "Setup complete. Start the demo with: powershell -ExecutionPolicy Bypass -File scripts\run.ps1"
