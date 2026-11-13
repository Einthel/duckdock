@echo off
setlocal enabledelayedexpansion
title DuckDock / TouchWM
cd /d "%~dp0"

echo ===================================================
echo   DuckDock / TouchWM - Production Launcher
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [*] Виртуальное окружение не найдено. Создаем .venv...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Ошибка создания .venv. Убедитесь, что Python 3.11+ установлен.
        pause
        exit /b 1
    )
    echo [*] Обновление pip и установка зависимостей...
    call .\.venv\Scripts\python.exe -m pip install --upgrade pip
    call .\.venv\Scripts\pip.exe install -r requirements.txt
)

echo [*] Запуск DuckDock...
".venv\Scripts\python.exe" main.py

if %ERRORLEVEL% NEQ 0 (
    echo [!] Приложение завершилось с ошибкой.
    pause
)
