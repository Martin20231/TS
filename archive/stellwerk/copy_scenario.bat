@echo off
setlocal EnableExtensions

echo.
echo === Stellwerk Szenario-Dateien kopieren ===
echo.

if not "%~1"=="" (
    set "SCENARIO_DIR=%~1"
    goto :copy
)

echo Gib den vollen Pfad zu deinem Szenario-Ordner ein.
echo (Im Editor: Szenario oeffnen - Script - Ordner oeffnen)
echo.
echo Beispiel:
echo E:\Steam\steamapps\common\RailWorks\Content\Routes\35e4c400-...\Scenarios\16133f2c-...
echo.

set /p SCENARIO_DIR="Szenario-Ordner: "

:copy
if not exist "%SCENARIO_DIR%" (
    echo [FEHLER] Ordner existiert nicht.
    pause
    exit /b 1
)

copy /Y "%~dp0scenario\ScenarioScript.lua" "%SCENARIO_DIR%\ScenarioScript.lua"
copy /Y "%~dp0scenario\stellwerk_help.html" "%SCENARIO_DIR%\stellwerk_help.html"
copy /Y "%~dp0scenario\stellwerk_menu.html" "%SCENARIO_DIR%\stellwerk_menu.html"
copy /Y "%~dp0scenario\editor_hilfe.html" "%SCENARIO_DIR%\editor_hilfe.html"

echo.
echo [OK] Dateien kopiert nach:
echo   %SCENARIO_DIR%
echo.
echo Nach dem Kopieren im Editor: Script KOMPILIEREN (sonst alte "Einfahrt Nord"-Texte)!
echo.
pause
