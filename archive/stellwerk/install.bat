@echo off
setlocal EnableExtensions

REM Installiert TS-Stellwerk-Skripte nach RailWorks
REM Standardpfad wie im Radar-Tracker

set "RAILWORKS=E:\Steam\steamapps\common\RailWorks"
if defined RAILWORKS_ROOT set "RAILWORKS=%RAILWORKS_ROOT%"

if not exist "%RAILWORKS%\RailWorks64.exe" (
    echo [FEHLER] RailWorks nicht gefunden: %RAILWORKS%
    echo Setze RAILWORKS_ROOT oder passe den Pfad in install.bat an.
    pause
    exit /b 1
)

set "SIG_SRC=%~dp0signals\TS Manual Stellwerk Shunt.lua"
set "SIG_DST1=%RAILWORKS%\Assets\Kuju\RailSimulator\RailNetwork\signals\German"
set "SIG_DST2=%RAILWORKS%\Assets\TrainTeamBerlin\AS_Common\RailNetwork\Signals\German"

echo.
echo === TS Stellwerk Installer ===
echo.

if not exist "%SIG_DST1%" mkdir "%SIG_DST1%"
if not exist "%SIG_DST2%" mkdir "%SIG_DST2%"

copy /Y "%SIG_SRC%" "%SIG_DST1%\TS Manual Stellwerk Shunt.lua"
if errorlevel 1 (
    echo [FEHLER] Kuju-Ordner: Signal-Skript konnte nicht kopiert werden.
    pause
    exit /b 1
)

copy /Y "%SIG_SRC%" "%SIG_DST2%\TS Manual Stellwerk Shunt.lua"
if errorlevel 1 (
    echo [FEHLER] S-Bahn-Ordner: Signal-Skript konnte nicht kopiert werden.
    pause
    exit /b 1
)

echo [OK] Signal-Skript installiert:
echo      %SIG_DST1%
echo      %SIG_DST2%
echo.
echo Naechste Schritte:
echo   1. INSTALL_DE.md lesen (Szenario im Editor anlegen)
echo   2. ScenarioScript.lua in deinen Szenario-Ordner kopieren
echo   3. SIGNALS-Namen in ScenarioScript.lua anpassen
echo.
pause
