# ============================================================================
# YouTube History Scraper to Supabase - PowerShell Starter
# Robust launch for Desktop shortcut and Task Scheduler
# ============================================================================
# Workflow:
# 1. Resolve Python (prefer venv: .venv\Scripts\python.exe)
# 2. Validate SUPABASE_SERVICE_KEY env var
# 3. Ensure python-dotenv is installed
# 4. Run run_youtube_history_scraper.py
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  YouTube History Scraper to Supabase" -ForegroundColor Cyan
Write-Host "============================================================================`n" -ForegroundColor Cyan

# Project root = directory of this script
$projectRoot = $PSScriptRoot
Set-Location $projectRoot

# [1] Resolve Python / virtualenv
Write-Host "[1/4] Check Python / venv..." -ForegroundColor Yellow
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$usingVenv = $false
$pythonExe = $null

if (Test-Path $venvPython) {
    $pythonExe = $venvPython
    $usingVenv = $true
    Write-Host "      OK: Using venv Python: $pythonExe" -ForegroundColor Green
} else {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $pythonExe = "py"
        Write-Host "      NOTE: .venv not found. Using 'py' from system" -ForegroundColor Yellow
    } elseif ($pythonCmd) {
        $pythonExe = "python"
        Write-Host "      NOTE: .venv not found. Using 'python' from system" -ForegroundColor Yellow
    } else {
        Write-Host "      ERROR: No Python installation found." -ForegroundColor Red
        Write-Host "      Install Python 3 or create a venv: py -3 -m venv .venv" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

try {
    if ($pythonExe -eq "py") {
        & $pythonExe -3 -c "import sys; print('      Python', sys.version)" | Out-Host
    } else {
        & $pythonExe -c "import sys; print('      Python', sys.version)" | Out-Host
    }
} catch {
    Write-Host "      ERROR: Failed to start Python ($pythonExe)." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# [2] Check environment variables (optional, Python reads .env)
Write-Host "[2/4] Check environment variables..." -ForegroundColor Yellow
$supabaseKey = [System.Environment]::GetEnvironmentVariable('SUPABASE_SERVICE_KEY', 'User')
if (-not $supabaseKey) { $supabaseKey = [System.Environment]::GetEnvironmentVariable('SUPABASE_SERVICE_KEY', 'Machine') }
if (-not $supabaseKey) {
    Write-Host "      NOTE: SUPABASE_SERVICE_KEY not found in OS env. Using .env file (loaded by python-dotenv)." -ForegroundColor Yellow
} else {
    Write-Host "      OK: SUPABASE_SERVICE_KEY present in OS env ($($supabaseKey.Length) chars)`n" -ForegroundColor Green
}

# [3] Ensure python-dotenv is available
Write-Host "[3/4] Verify Python packages..." -ForegroundColor Yellow
$dotenvMissing = $false
try {
    if ($pythonExe -eq "py") {
        & $pythonExe -3 -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('dotenv') else 1)"
        if ($LASTEXITCODE -ne 0) { $dotenvMissing = $true }
    } else {
        & $pythonExe -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('dotenv') else 1)"
        if ($LASTEXITCODE -ne 0) { $dotenvMissing = $true }
    }
} catch { $dotenvMissing = $true }

if ($dotenvMissing) {
    Write-Host "      'python-dotenv' missing -> installing..." -ForegroundColor Yellow
    try {
        if ($usingVenv) {
            & $pythonExe -m pip install --upgrade pip | Out-Host
            & $pythonExe -m pip install python-dotenv | Out-Host
        } else {
            if ($pythonExe -eq "py") {
                & $pythonExe -3 -m pip install --user python-dotenv | Out-Host
            } else {
                & $pythonExe -m pip install --user python-dotenv | Out-Host
            }
        }
        Write-Host "      OK: 'python-dotenv' installed`n" -ForegroundColor Green
    } catch {
        Write-Host "      ERROR: Failed to install 'python-dotenv'." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "      OK: 'python-dotenv' available`n" -ForegroundColor Green
}

# [4] Run main script
Write-Host "[4/4] Start YouTube History Scraper..." -ForegroundColor Yellow
Write-Host "============================================================================`n" -ForegroundColor Cyan

if ($pythonExe -eq "py") {
    & $pythonExe -3 run_youtube_history_scraper.py --lang de --source powershell-run
} else {
    & $pythonExe run_youtube_history_scraper.py --lang de --source powershell-run
}

$exitCode = $LASTEXITCODE
Write-Host "`n============================================================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "  ERFOLGREICH ABGESCHLOSSEN" -ForegroundColor Green
    Write-Host "============================================================================`n" -ForegroundColor Cyan
} else {
    Write-Host "  FEHLER: Exit-Code $exitCode" -ForegroundColor Red
    Write-Host "============================================================================`n" -ForegroundColor Cyan
    Read-Host "Press Enter to exit"
    exit $exitCode
}

# Optional: keep window open for manual runs
# Read-Host "Press Enter to exit"
