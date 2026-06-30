@echo off
setlocal EnableExtensions
title TS Radar – Szenario-Script installieren

echo.
echo  Multiplayer-Radar Szenario-Script
echo  =================================
echo.
echo  Dieses Script kopiert ScenarioScript.lua in dein Szenario.
echo  Danach im Szenario-Editor Start-Event setzen: MPRadarStart
echo.

set /p SCENARIO_DIR=Pfad zum Szenario-Ordner (mit ScenarioProperties.xml): 

if not exist "%SCENARIO_DIR%\ScenarioProperties.xml" (
    echo.
    echo  FEHLER: Kein Szenario gefunden unter:
    echo  %SCENARIO_DIR%
    pause
    exit /b 1
)

copy /Y "%~dp0ScenarioScript.lua" "%SCENARIO_DIR%\ScenarioScript.lua"
if errorlevel 1 (
    echo Kopieren fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo  [OK] ScenarioScript.lua kopiert.
echo.
echo  Naechste Schritte:
echo    1. Szenario im Editor oeffnen
echo    2. Fahrplan: Start-Event = MPRadarStart
echo    3. Szenario kompilieren
echo    4. Tracker mit session_id starten
echo.
pause
