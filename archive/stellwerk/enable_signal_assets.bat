@echo off
setlocal EnableExtensions

echo.
echo === Stellwerk: Signal-Assets im Szenario freischalten ===
echo.
echo Szenario-Ordner (gleicher Pfad wie bei copy_scenario.bat):
echo.

set /p SCENARIO_DIR="Pfad: "

if not exist "%SCENARIO_DIR%\ScenarioProperties.xml" (
    echo [FEHLER] ScenarioProperties.xml nicht gefunden.
    pause
    exit /b 1
)

python "%~dp0enable_signal_assets.py" "%SCENARIO_DIR%"
echo.
pause
