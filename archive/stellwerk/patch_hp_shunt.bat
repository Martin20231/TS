@echo off
setlocal EnableExtensions

REM Ersetzt HP_Shunt.lua durch das Stellwerk-Script (mit Backup).
REM Danach reicht im Editor oft nur noch Object Name (SW_S1) – kein Script-Feld noetig.

set "RAILWORKS=E:\Steam\steamapps\common\RailWorks"
if defined RAILWORKS_ROOT set "RAILWORKS=%RAILWORKS_ROOT%"

set "SRC=%~dp0signals\TS Manual Stellwerk Shunt.lua"
set "DST=%RAILWORKS%\Assets\TrainTeamBerlin\AS_Common\RailNetwork\Signals\German\HP_Shunt.lua"
set "BAK=%DST%.backup_stellwerk"

if not exist "%SRC%" (
    echo [FEHLER] Quelle fehlt: %SRC%
    pause
    exit /b 1
)

if not exist "%DST%" (
    echo [FEHLER] HP_Shunt.lua nicht gefunden: %DST%
    pause
    exit /b 1
)

if not exist "%BAK%" (
    copy /Y "%DST%" "%BAK%" >nul
    echo [OK] Backup: HP_Shunt.lua.backup_stellwerk
)

copy /Y "%SRC%" "%DST%" >nul
echo [OK] HP_Shunt.lua ist jetzt das Stellwerk-Script.
echo.
echo Im Editor: bestehendes Rangiersignal anklicken, nur Object Name setzen (SW_S1).
echo Rueckgaengig: copy "%BAK%" "%DST%"
echo.
pause
