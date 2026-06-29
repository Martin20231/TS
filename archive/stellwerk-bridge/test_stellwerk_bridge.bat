@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === Stellwerk-Brücke testen (TS muss laufen, in BR 483 sitzen) ===
echo.
python test_stellwerk_bridge.py
echo.
pause
