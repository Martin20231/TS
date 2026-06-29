@echo off
chcp 65001 >nul
title TS Radar – GPS-Tracker (Cloud-Server)
cd /d "%~dp0"

echo.
echo  GPS-Tracker für Cloud-Server (Render)
echo  =====================================
echo.

if not exist "config.json" (
    echo  Kopiere config.example.json nach config.json und trage deine Daten ein.
    copy /Y config.example.json config.json
    notepad config.json
    pause
)

python -m pip install -r requirements.txt -q
echo  Starte Tracker ...  (Train Simulator muss laufen)
echo  server_url in config.json muss auf Render zeigen.
echo.
python -u ts_tracker.py
pause
