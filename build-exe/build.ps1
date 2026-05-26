# Build-script voor Takt.exe
# Uitvoeren vanuit de build-exe map: .\build.ps1

Set-Location $PSScriptRoot

Write-Host "=== Takt build ===" -ForegroundColor Cyan

# Maak venv aan als die nog niet bestaat
if (-not (Test-Path ".venv")) {
    Write-Host "Venv aanmaken..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activeer venv en installeer dependencies
Write-Host "Dependencies installeren..." -ForegroundColor Yellow
& ".\.venv\Scripts\pip.exe" install -r requirements.txt --quiet

# Bouw de exe
Write-Host "PyInstaller uitvoeren..." -ForegroundColor Yellow
& ".\.venv\Scripts\pyinstaller.exe" takt.spec --clean --noconfirm

if (Test-Path "dist\Takt.exe") {
    Write-Host ""
    Write-Host "Klaar! Executable staat in:" -ForegroundColor Green
    Write-Host "  $PSScriptRoot\dist\Takt.exe" -ForegroundColor Green
} else {
    Write-Host "Build mislukt - controleer de output hierboven." -ForegroundColor Red
    exit 1
}
