@echo off
setlocal EnableExtensions

set "RAILWORKS=E:\Steam\steamapps\common\RailWorks"
if defined RAILWORKS_ROOT set "RAILWORKS=%RAILWORKS_ROOT%"

set "DIR=%RAILWORKS%\Assets\virtualTracks\S45\RailNetwork\Signals\German-HL\Skripte"
set "LUA=%DIR%\vT HL HS.lua"
set "OUT=%DIR%\vT HL HS.out"
set "DIS=%OUT%.disabled_stellwerk"
set "BAK=%OUT%.backup_stellwerk"

echo.
echo === Original vT HL HS wiederherstellen ===
echo.

if exist "%LUA%" (
    del "%LUA%" >nul 2>&1
    echo [OK] vT HL HS.lua entfernt (unser Ersatz)
)

if exist "%DIS%" (
    ren "%DIS%" "vT HL HS.out" >nul 2>&1
    echo [OK] vT HL HS.out wieder aktiv
) else if exist "%BAK%" (
    copy /Y "%BAK%" "%OUT%" >nul
    echo [OK] vT HL HS.out aus Backup
) else if exist "%OUT%" (
    echo [OK] vT HL HS.out war schon da
) else (
    echo [WARNUNG] Kein Original .out gefunden
)

echo.
echo Alle anderen Signale der Strecke verhalten sich wieder normal.
echo Nur SW_S1 nutzt TS Stellwerk SW_S1.lua (siehe install_sw_s1.bat).
echo.
if /I not "%~1"=="silent" pause
