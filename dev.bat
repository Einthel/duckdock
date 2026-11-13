@echo off
setlocal enabledelayedexpansion
title DuckDock / TouchWM [DEV MODE]
cd /d "%~dp0"

echo ===================================================
echo   DuckDock / TouchWM - Development Mode
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    call run.bat
    exit /b 0
)

echo [*] Запуск в режиме разработки с консольным выводом...
set DUCKDOCK_DEBUG=1
set QT_LOGGING_RULES=qt.qpa.*=false

".venv\Scripts\python.exe" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] DuckDock остановлен с кодом %ERRORLEVEL%.
    pause
)
