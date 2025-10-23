@echo off
echo ========================================
echo YouTube URL Datenbank Bereinigung
echo ========================================
echo.

REM Setze Python Pfad
set PYTHON_PATH=C:\Users\Daniel\AppData\Local\Programs\Python\Python313\python.exe

REM Setze Supabase Service Key (falls nicht bereits gesetzt)
if "%SUPABASE_SERVICE_KEY%"=="" (
    echo WARNUNG: SUPABASE_SERVICE_KEY nicht gesetzt!
    echo Bitte setze die Umgebungsvariable vor dem Start.
    pause
    exit /b 1
)

echo Starte Datenbank-Bereinigung...
echo.

"%PYTHON_PATH%" database_cleaner.py

echo.
echo Bereinigung abgeschlossen.
pause