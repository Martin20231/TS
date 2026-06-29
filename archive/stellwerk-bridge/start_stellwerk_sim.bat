@echo off
chcp 65001 >nul
title TS Stellwerk Sim (lokal)
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      TS Stellwerk Sim – Lokaltest        ║
echo  ╚══════════════════════════════════════════╝
echo.

if not exist "config.json" (
    python -c "from radar_config import load_config; load_config()"
)

echo  [0/4] Alte Server/Tracker beenden ...
call "%~dp0stop_radar.bat"

echo  [1/4] Python-Abhaengigkeiten ...
python -m pip install -r requirements.txt -q

echo  [2/4] config.json auf localhost ...
python -c "import json;from pathlib import Path;p=Path('config.json');c=json.loads(p.read_text(encoding='utf-8'));c['server_url']='http://127.0.0.1:8080/api/position';p.write_text(json.dumps(c,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')"

echo  [3/4] Server + Tracker starten (ein Prozess, stabiler) ...
start "TS Stellwerk – Lokal" cmd /k "cd /d "%~dp0" && python -u run_stellwerk_local.py"
timeout /t 4 /nobreak >nul

echo  [4/4] Karte oeffnen ...
start "" "http://localhost:8080?mode=stellwerk"

echo.
echo  Karte: http://localhost:8080?mode=stellwerk
echo  Oben: Tab "Stellwerk Sim" waehlen, Signal anklicken.
echo.
echo  Train Simulator: Szenario starten, in Lok sitzen, Fahrt beginnen!
echo  Wichtig: Erst Spiel+Lok, dann funktioniert die Bruecke (gruene LED).
echo  Anleitung: stellwerk\ANLEITUNG.md
echo.
pause
