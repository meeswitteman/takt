$backendDir = "$PSScriptRoot\takt-backend"
$desktopDir = "$PSScriptRoot\takt-desktop"
$uvicorn    = "$backendDir\.venv\Scripts\uvicorn.exe"
$python     = "$desktopDir\.venv\Scripts\python.exe"
$healthUrl  = "http://127.0.0.1:8080/api/v1/health"

Write-Host "=== Takt ===" -ForegroundColor Cyan

# Lees db_path uit desktop settings en zet env-var voor backend
$settingsPath = "$env:APPDATA\takt\settings.json"
if (Test-Path $settingsPath) {
    try {
        $taktSettings = Get-Content $settingsPath -Raw | ConvertFrom-Json
        if ($taktSettings.db_path -and $taktSettings.db_path -ne "") {
            $env:TAKT_DB_PATH = $taktSettings.db_path
            Write-Host "Database: $($taktSettings.db_path)" -ForegroundColor Cyan
        }
    } catch {}
}

# Backend: controleer of al draait
$running = $false
try {
    Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 1 | Out-Null
    $running = $true
} catch {}

if ($running) {
    Write-Host "Backend draait al op :8080" -ForegroundColor Green
} else {
    Write-Host "Backend starten..." -ForegroundColor Yellow

    # Open backend in apart venster (zichtbaar, maar minimaliseerbaar)
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/k title Takt Backend && cd /d `"$backendDir`" && `"$uvicorn`" app.main:app --host 0.0.0.0 --port 8080" `
        -WindowStyle Minimized

    # Wachten tot backend beschikbaar is (max 15 seconden)
    $ok = $false
    Write-Host -NoNewline "Wachten"
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        Write-Host -NoNewline "."
        try {
            Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 1 | Out-Null
            $ok = $true
            break
        } catch {}
    }
    Write-Host ""

    if ($ok) {
        Write-Host "Backend actief." -ForegroundColor Green
    } else {
        Write-Host "Backend kon niet starten! Controleer het 'Takt Backend' venster." -ForegroundColor Red
        Start-Sleep -Seconds 5
        exit 1
    }
}

# Desktop app starten
Write-Host "Desktop app starten..." -ForegroundColor Yellow
Start-Process -FilePath $python -ArgumentList "-m app.main" -WorkingDirectory $desktopDir
Write-Host "Klaar - dit venster sluit automatisch." -ForegroundColor Green
Start-Sleep -Seconds 2
