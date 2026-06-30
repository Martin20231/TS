@echo off
chcp 65001 >nul
title TS-Radar.exe bauen
cd /d "%~dp0\.."

echo.
echo  TS-Radar.exe wird erstellt (moderner Launcher) ...
echo.

taskkill /IM TS-Radar.exe /F >nul 2>&1
taskkill /IM python.exe /FI "WINDOWTITLE eq TS Radar*" /F >nul 2>&1
timeout /t 2 /nobreak >nul

python -m pip install pyinstaller customtkinter requests pillow -q
if errorlevel 1 (
    echo FEHLER: pip install fehlgeschlagen.
    pause
    exit /b 1
)

pyinstaller --noconfirm --onefile --windowed ^
  --name "TS-Radar" ^
  --hidden-import=customtkinter ^
  --hidden-import=PIL ^
  --hidden-import=PIL._tkinter_finder ^
  --hidden-import=requests ^
  --hidden-import=radar_config ^
  --hidden-import=radar_util ^
  --hidden-import=app_services ^
  --hidden-import=launcher_app ^
  --hidden-import=launcher_settings ^
  --hidden-import=http_session ^
  --hidden-import=ts_tracker ^
  --hidden-import=cab_overlay ^
  --hidden-import=radio_bridge ^
  --hidden-import=ctypes ^
  --collect-all customtkinter ^
  --collect-submodules=requests ^
  launcher.py

if errorlevel 1 (
    echo FEHLER: PyInstaller fehlgeschlagen.
    pause
    exit /b 1
)

copy /Y config.cloud.example.json dist\config.example.json >nul 2>&1
if exist config.json copy /Y config.json dist\config.json >nul 2>&1
copy /Y docs\SPIELANLEITUNG.txt dist\SPIELANLEITUNG.txt >nul 2>&1

echo.
echo  ========================================
echo  Fertig!
echo    dist\TS-Radar.exe
echo.
echo  Doppelklick = alles in einem Fenster
echo  ========================================
echo.
pause
