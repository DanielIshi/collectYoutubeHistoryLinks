@echo off
echo ========================================
echo YouTube URL Retrograde Klassifizierung
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

echo Starte Klassifizierung...
echo.

"%PYTHON_PATH%" retrograde_classifier.py

echo.
echo Klassifizierung abgeschlossen.
pause