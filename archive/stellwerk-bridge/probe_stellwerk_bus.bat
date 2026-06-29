@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === Setzbare Regler finden (TS laeuft, in BR 483 sitzen) ===
echo.
python probe_stellwerk_bus.py
echo.
pause
