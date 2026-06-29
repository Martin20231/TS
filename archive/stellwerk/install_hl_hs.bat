@echo off

setlocal EnableExtensions



REM Ersetzt das Script "vT HL HS" fuer alle vT S45 HL-Hauptsignale auf der Strecke.

REM Backup von vT HL HS.out wird angelegt.



set "RAILWORKS=E:\Steam\steamapps\common\RailWorks"

if defined RAILWORKS_ROOT set "RAILWORKS=%RAILWORKS_ROOT%"



set "SRC=%~dp0signals\TS Manual Stellwerk HL HS.lua"

set "DST_DIR=%RAILWORKS%\Assets\virtualTracks\S45\RailNetwork\Signals\German-HL\Skripte"

set "DST_LUA=%DST_DIR%\vT HL HS.lua"

set "DST_OUT=%DST_DIR%\vT HL HS.out"

set "BAK=%DST_OUT%.backup_stellwerk"

set "ALT=%DST_DIR%\TS Manual Stellwerk HL HS.lua"



echo.

echo === TS Stellwerk: vT HL HS Script ===

echo.



if not exist "%SRC%" (

    echo [FEHLER] Quelle fehlt: %SRC%

    pause

    exit /b 1

)



if not exist "%DST_DIR%" (

    echo [FEHLER] Ordner nicht gefunden: %DST_DIR%

    echo Hast du die Route S45 / Berlin JWD installiert?

    pause

    exit /b 1

)



if not exist "%BAK%" (

    if exist "%DST_OUT%" (

        copy /Y "%DST_OUT%" "%BAK%" >nul

        echo [OK] Backup: vT HL HS.out.backup_stellwerk

    )

)



copy /Y "%SRC%" "%DST_LUA%" >nul

copy /Y "%SRC%" "%ALT%" >nul



if exist "%DST_OUT%" (

    ren "%DST_OUT%" "vT HL HS.out.disabled_stellwerk"

    echo [OK] Altes Bytecode-Script deaktiviert (.out.disabled_stellwerk)

)



echo [OK] Neues Script installiert:

echo      %DST_LUA%

echo.

echo Im Szenario-Editor an BESTEHENDEN Signalen:

echo   Object Name = SW_S1, SW_S2, SW_S3, SW_S4

echo Editor-Name z.B.: vT S45 HL HS 0T

echo.

echo Rueckgaengig:

echo   del "%DST_LUA%"

echo   ren "%DST_OUT%.disabled_stellwerk" "vT HL HS.out"
echo.
if /I not "%~1"=="silent" pause


