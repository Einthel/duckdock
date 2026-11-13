@echo off
setlocal enabledelayedexpansion
title DuckDock / TouchWM - Build EXE
cd /d "%~dp0"

echo ===================================================
echo   DuckDock / TouchWM - PyInstaller Builder
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] Окружение .venv не найдено. Запустите сначала dev.bat или run.bat.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" build_exe.py

if %ERRORLEVEL% NEQ 0 (
    echo [!] Ошибка при сборке EXE.
    pause
    exit /b 1
)

echo [✓] Готово! Исполняемый файл находится в dist/duckdock.exe
pause
