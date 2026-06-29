@echo off
setlocal EnableExtensions

set "SCENARIO=E:\Steam\steamapps\common\RailWorks\Content\Routes\35e4c400-8268-4ca4-9af6-52263689d603\Scenarios\16133f2c-3362-474b-a3cb-266914695836"

echo.
echo === Szenario-Start zuruecksetzen ===
echo.

if exist "%SCENARIO%\InitialSave.bin" (
    del /F "%SCENARIO%\InitialSave.bin" >nul 2>&1
    echo [OK] InitialSave.bin geloescht
) else (
    echo [OK] Kein InitialSave.bin
)

if exist "%SCENARIO%\InitialSave.bin.MD5" del /F "%SCENARIO%\InitialSave.bin.MD5" >nul 2>&1

echo Szenario im Spiel NEU starten (nicht Fortsetzen)!
echo.
if /I not "%~1"=="silent" pause
