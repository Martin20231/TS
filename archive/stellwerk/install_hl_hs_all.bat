@echo off
chcp 65001 >nul
setlocal EnableExtensions

set "RAILWORKS=E:\Steam\steamapps\common\RailWorks"
if defined RAILWORKS_ROOT set "RAILWORKS=%RAILWORKS_ROOT%"

set "SRC=%~dp0signals\TS Manual Stellwerk HL HS.lua"
set "DST_DIR=%RAILWORKS%\Assets\virtualTracks\S45\RailNetwork\Signals\German-HL\Skripte"

if not exist "%SRC%" (
    echo [FEHLER] %SRC% fehlt
    pause
    exit /b 1
)

echo === HL-Signal-Scripts fuer Stellwerk (alle Varianten) ===
echo.

for %%V in ("vT HL HS" "vT HL HS 060" "vT HL HS 100" "vT HL HS 160") do (
    set "NAME=%%~V"
    call :install_one "%%~V"
)

echo.
echo [OK] Wrapper installiert. Spiel komplett neu starten!
echo.
if /I not "%~1"=="silent" pause
exit /b 0

:install_one
set "BASE=%~1"
if not exist "%DST_DIR%\%BASE%.out" (
    if not exist "%DST_DIR%\%BASE%.out.disabled_stellwerk" (
        echo [SKIP] %BASE%.out nicht gefunden
        goto :eof
    )
)
if not exist "%DST_DIR%\%BASE%.out.backup_stellwerk" (
    if exist "%DST_DIR%\%BASE%.out" (
        copy /Y "%DST_DIR%\%BASE%.out" "%DST_DIR%\%BASE%.out.backup_stellwerk" >nul
    )
)
copy /Y "%SRC%" "%DST_DIR%\%BASE%.lua" >nul
if exist "%DST_DIR%\%BASE%.out" (
    ren "%DST_DIR%\%BASE%.out" "%BASE%.out.disabled_stellwerk" >nul 2>&1
)
echo [OK] %BASE%
goto :eof
