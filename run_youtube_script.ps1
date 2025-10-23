# ============================================================================
# YouTube History Scraper to Supabase - PowerShell Starter
# ============================================================================
# Workflow:
# 1. Aktiviert Virtual Environment (.venv)
# 2. Startet Chrome im Debug-Modus
# 3. Scraped YouTube-Historie via Selenium
# 4. Lädt neue URLs zu Supabase hoch
# 5. Holt Untertitel für jedes Video (pytubefix)
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  YouTube History Scraper to Supabase" -ForegroundColor Cyan
Write-Host "============================================================================`n" -ForegroundColor Cyan

# Projekt-Verzeichnis
$projectRoot = $PSScriptRoot
Set-Location $projectRoot

# Virtual Environment aktivieren
Write-Host "[1/3] Aktiviere Virtual Environment..." -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    & ".\.venv\Scripts\Activate.ps1"
    Write-Host "      OK Virtual Environment aktiviert`n" -ForegroundColor Green
} else {
    Write-Host "      WARNUNG: .venv nicht gefunden - nutze System-Python" -ForegroundColor Yellow
}

# Environment-Variable prüfen
Write-Host "[2/3] Prufe Environment-Variablen..." -ForegroundColor Yellow
$supabaseKey = [System.Environment]::GetEnvironmentVariable('SUPABASE_SERVICE_KEY', 'User')
if (-not $supabaseKey) {
    $supabaseKey = [System.Environment]::GetEnvironmentVariable('SUPABASE_SERVICE_KEY', 'Machine')
}
if (-not $supabaseKey) {
    Write-Host "      FEHLER: SUPABASE_SERVICE_KEY nicht gesetzt!" -ForegroundColor Red
    Write-Host "      Bitte setzen mit: setx SUPABASE_SERVICE_KEY `"your-key`"`n" -ForegroundColor Red
    Read-Host "Drucke Enter zum Beenden"
    exit 1
}
Write-Host "      OK SUPABASE_SERVICE_KEY gesetzt ($($supabaseKey.Length) Zeichen)`n" -ForegroundColor Green

# Hauptskript ausführen
Write-Host "[3/3] Starte YouTube History Scraper..." -ForegroundColor Yellow
Write-Host "============================================================================`n" -ForegroundColor Cyan

python run_youtube_history_scraper.py --lang de --source powershell-run

# Fehlerbehandlung
$exitCode = $LASTEXITCODE
Write-Host "`n============================================================================" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "  ERFOLGREICH ABGESCHLOSSEN" -ForegroundColor Green
    Write-Host "============================================================================`n" -ForegroundColor Cyan
} else {
    Write-Host "  FEHLER: Exit-Code $exitCode" -ForegroundColor Red
    Write-Host "============================================================================`n" -ForegroundColor Cyan
    Read-Host "Drucke Enter zum Beenden"
    exit $exitCode
}

# Optional: Pause (für manuellen Start)
# Read-Host "Drucke Enter zum Beenden"
