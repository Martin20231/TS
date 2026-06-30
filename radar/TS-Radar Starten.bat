@echo off
chcp 65001 >nul
title TS Multiplayer-Radar
cd /d "%~dp0"

if exist "dist\TS-Radar.exe" (
    start "" "dist\TS-Radar.exe"
    exit /b 0
)

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Python nicht gefunden.
    echo  Bitte dist\TS-Radar.exe nutzen oder Python installieren.
    echo.
    pause
    exit /b 1
)

python launcher.py
