# Build-script voor takt.exe (de command-line tool)
# Uitvoeren vanuit de build-cli map: .\build.ps1

Set-Location $PSScriptRoot

Write-Host "=== takt CLI build ===" -ForegroundColor Cyan

# Zoek Python op (gebruik dezelfde als de bestaande venvs)
$pythonExe = "C:\Users\meesw\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (-not (Test-Path $pythonExe)) {
    # Fallback: probeer py launcher
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) { $pythonExe = $pyCmd.Source }
}
if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    Write-Host "Python niet gevonden. Pas `$pythonExe aan in build.ps1." -ForegroundColor Red
    exit 1
}
Write-Host "Python: $pythonExe" -ForegroundColor Cyan

# Maak venv aan als die nog niet bestaat
if (-not (Test-Path ".venv")) {
    Write-Host "Venv aanmaken..." -ForegroundColor Yellow
    & $pythonExe -m venv .venv
}

# Installeer dependencies
Write-Host "Dependencies installeren..." -ForegroundColor Yellow
& ".\.venv\Scripts\pip.exe" install -r requirements.txt --quiet

# Bouw de exe
Write-Host "PyInstaller uitvoeren..." -ForegroundColor Yellow
& ".\.venv\Scripts\pyinstaller.exe" takt-cli.spec --clean --noconfirm

if (Test-Path "dist\takt.exe") {
    Write-Host ""
    Write-Host "Klaar! Executable staat in:" -ForegroundColor Green
    Write-Host "  $PSScriptRoot\dist\takt.exe" -ForegroundColor Green
    Write-Host ""
    Write-Host "Zet deze map in je PATH, of kopieer takt.exe naar een map die al in PATH staat." -ForegroundColor Cyan
} else {
    Write-Host "Build mislukt - controleer de output hierboven." -ForegroundColor Red
    exit 1
}