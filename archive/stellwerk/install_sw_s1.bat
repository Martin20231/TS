@echo off
setlocal EnableExtensions

set "RAILWORKS=E:\Steam\steamapps\common\RailWorks"
if defined RAILWORKS_ROOT set "RAILWORKS=%RAILWORKS_ROOT%"

set "SRC=%~dp0signals\TS Stellwerk SW_S1.lua"
set "DST=%RAILWORKS%\Assets\virtualTracks\S45\RailNetwork\Signals\German-HL\Skripte\TS Stellwerk SW_S1.lua"

echo.
echo === TS Stellwerk SW_S1 Script installieren ===
echo.

if not exist "%SRC%" (
    echo [FEHLER] %SRC% fehlt
    pause
    exit /b 1
)

copy /Y "%SRC%" "%DST%" >nul
echo [OK] %DST%
echo.
echo Im STRECKEN-Editor an DEINEM Signal:
echo   Object Name  = SW_S1
echo   Script       = TS Stellwerk SW_S1.lua
echo   Dann STRECKE SPEICHERN (nicht nur Szenario!)
echo.
if /I not "%~1"=="silent" pause
