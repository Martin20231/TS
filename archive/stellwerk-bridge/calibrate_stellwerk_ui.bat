@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === Stellwerk-Menü kalibrieren (Spiel + Menü oben rechts sichtbar) ===
echo.
python calibrate_stellwerk_ui.py
echo.
pause
