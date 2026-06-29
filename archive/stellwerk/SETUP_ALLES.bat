@echo off
setlocal EnableExtensions

echo.
echo ============================================
echo   STELLWERK - Komplett-Setup
echo ============================================
echo.

call "%~dp0install_hl_hs_all.bat" silent
call "%~dp0install_sw_s1.bat" silent

set "SCENARIO=E:\Steam\steamapps\common\RailWorks\Content\Routes\35e4c400-8268-4ca4-9af6-52263689d603\Scenarios\16133f2c-3362-474b-a3cb-266914695836"

echo.
echo Szenario-Dateien kopieren...
copy /Y "%~dp0scenario\ScenarioScript.lua" "%SCENARIO%\ScenarioScript.lua" >nul
copy /Y "%~dp0scenario\stellwerk_help.html" "%SCENARIO%\stellwerk_help.html" >nul
copy /Y "%~dp0scenario\stellwerk_menu.html" "%SCENARIO%\stellwerk_menu.html" >nul
copy /Y "%~dp0scenario\editor_hilfe.html" "%SCENARIO%\editor_hilfe.html" >nul
if not exist "%SCENARIO%\de" mkdir "%SCENARIO%\de"
copy /Y "%~dp0scenario\*.html" "%SCENARIO%\de\" >nul
echo [OK] Szenario aktualisiert
call "%~dp0patch_fresh_start.bat" silent 2>nul

echo.
echo ============================================
echo   JETZT IM SZENARIO-EDITOR (wichtig!):
echo ============================================
echo.
echo   Signal FEHLER? -> stellwerk\SIGNAL_SZENARIO.md
echo.
echo   1. Objekt-Browser -^> Signal vT S45 HL HS platzieren
echo   2. Object Name = SW_S1
echo   3. Script -^> Kompilieren -^> Speichern
echo.
echo   Optional Strecken-Editor: route_id in ScenarioScript.lua
echo.
echo ============================================
if /I not "%~1"=="silent" pause
