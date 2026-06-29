@echo off
chcp 65001 >nul
title TS-Radar.exe bauen
cd /d "%~dp0"

echo.
echo  TS-Radar.exe wird erstellt ...
echo  =============================
echo.

python -m pip install pyinstaller requests -q
if errorlevel 1 (
    echo FEHLER: pip install fehlgeschlagen.
    pause
    exit /b 1
)

pyinstaller --noconfirm --onefile --windowed ^
  --name "TS-Radar" ^
  --hidden-import=requests ^
  --collect-submodules=requests ^
  launcher.py

if errorlevel 1 (
    echo FEHLER: PyInstaller fehlgeschlagen.
    pause
    exit /b 1
)

copy /Y config.example.json dist\config.example.json >nul 2>&1

echo.
echo  Fertig!
echo  -------
echo  Die Exe liegt hier:
echo    dist\TS-Radar.exe
echo.
echo  Beim ersten Start Einstellungen eingeben.
echo  config.json wird neben der Exe gespeichert.
echo.
echo  Diese Dateien an Freunde weitergeben:
echo    - TS-Radar.exe
echo    - optional config.example.json als Vorlage
echo.
pause
