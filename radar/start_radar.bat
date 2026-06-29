@echo off
chcp 65001 >nul
title TS Multiplayer-Radar
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Train Simulator – Multiplayer-Radar    ║
echo  ╚══════════════════════════════════════════╝
echo.

if not exist "config.json" (
    echo  Erstelle Standard-Konfiguration: config.json
    python -c "from radar_config import load_config; load_config()"
)

echo  [1/4] Pruefe Python-Abhaengigkeiten ...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo  FEHLER: pip install fehlgeschlagen. Ist Python installiert?
    pause
    exit /b 1
)

echo  [2/4] Starte Radar-Server ...
start "TS Radar – Server" cmd /k "cd /d "%~dp0" && python server.py"

echo  [3/4] Warte auf Server ...
timeout /t 3 /nobreak >nul

echo  [4/4] Starte GPS-Tracker und oeffne Karte ...
start "TS Radar – Tracker" cmd /k "cd /d "%~dp0" && python -u ts_tracker.py"
timeout /t 2 /nobreak >nul
start "" "http://localhost:8080"

echo.
echo  Fertig! Die Karte sollte sich im Browser oeffnen.
echo.
echo  Wichtig:
echo    1. Train Simulator starten und eine Fahrt beginnen
echo    2. Deinen Namen in config.json aendern (player_name)
echo    3. Freunde: server_url auf deine PC-IP setzen
echo.
echo  Beenden: stop_radar.bat oder die beiden schwarzen Fenster schliessen.
echo.
pause
