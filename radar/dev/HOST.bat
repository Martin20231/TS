@echo off
chcp 65001 >nul
title TS Radar – Host (Server + Tracker)
cd /d "%~dp0\.."

echo.
echo  Host-Modus: Server + Tracker + Karte
echo  (Fuer Freunde im LAN – oder Launcher mit „Eigener Server“ nutzen)
echo.

if not exist "config.json" (
    python -c "from radar_config import load_config; load_config()"
)

python -m pip install -r requirements-local.txt -q
if errorlevel 1 (
    echo FEHLER: pip install fehlgeschlagen.
    pause
    exit /b 1
)

start "TS Radar – Server" cmd /k "cd /d "%~dp0\.." && python server.py"
timeout /t 3 /nobreak >nul
start "TS Radar – Launcher" cmd /k "cd /d "%~dp0\.." && python launcher.py"
timeout /t 2 /nobreak >nul
start "" "http://localhost:8080"

echo.
echo  Server und Launcher laufen in eigenen Fenstern.
echo  Beenden: dev\STOP.bat
echo.
pause
