@echo off
setlocal enabledelayedexpansion
title DuckDock / TouchWM - Build Standalone Distribution
cd /d "%~dp0"

echo ===================================================
echo   DuckDock / TouchWM - Standalone Builder (v0.2.0)
echo   Target: --onedir (dist/DuckDock/) + ZIP Archive
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" build_exe.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Ошибка при сборке автономного дистрибутива.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ===================================================
echo [✓] Сборка успешно завершена!
echo     Папка сборки: dist\DuckDock\
echo     ZIP-дистрибутив: dist\DuckDock-v0.2.0.zip
echo ===================================================
echo.
pause
