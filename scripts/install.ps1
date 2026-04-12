# Pocket Desk Agent - Windows Installation Script (source checkout)
#
# For most users, installing from PyPI is simpler:
#     pip install pocket-desk-agent
#
# This script is for developers working from a git checkout. It creates
# a local virtualenv, installs the package in editable mode, and leaves
# you with the `pdagent` CLI available inside the venv.

$projectRoot = Get-Location
$venvDir = Join-Path $projectRoot ".venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Pocket Desk Agent Installer (Dev)" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
Write-Host "Step 1: Checking Python version..."
$pythonVersion = python --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "X Python not found. Please install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}
Write-Host "OK Found $pythonVersion" -ForegroundColor Green

# 2. Setup Virtual Environment
if (-not (Test-Path $venvDir)) {
    Write-Host "Step 2: Creating virtual environment..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "X Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}
Write-Host "OK Virtual environment ready" -ForegroundColor Green

# 3. Install package in editable mode
Write-Host "Step 3: Installing pocket-desk-agent in editable mode..."
& "$pythonExe" -m pip install --upgrade pip
& "$pythonExe" -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    Write-Host "X Failed to install package." -ForegroundColor Red
    exit 1
}
Write-Host "OK Package installed" -ForegroundColor Green

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "INSTALLATION COMPLETE!" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Activate the venv:   .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  2. Create a .env file (copying .env.example) and add your tokens" -ForegroundColor White
Write-Host "  3. Run 'python scripts\manage_auth.py' to link your Google account" -ForegroundColor White
Write-Host "  4. Run 'pdagent' to start the bot" -ForegroundColor Green
Write-Host ""
Write-Host "For the end-user install, publish to PyPI and run:"
Write-Host "  pip install pocket-desk-agent" -ForegroundColor Cyan
Write-Host ""
