@echo off
chcp 65001 >nul
title TS Radar beenden
cd /d "%~dp0"

echo Beende Radar (Server + Tracker) ...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

taskkill /FI "WINDOWTITLE eq TS Radar – Server*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq TS Radar – Tracker*" /F >nul 2>&1

echo Warte kurz, bis Port 8080 frei ist ...
timeout /t 3 /nobreak >nul

echo Fertig. Jetzt start_radar.bat ausfuehren.
timeout /t 2 /nobreak >nul
