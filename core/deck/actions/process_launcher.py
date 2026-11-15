"""
Модуль безопасного запуска процессов и утилит (Process Launcher).
Обеспечивает запуск приложений, bat/ps1 скриптов и системных утилит в фоновом
detached-режиме (CREATE_NO_WINDOW) с отвязкой дескрипторов ввода/вывода (DEVNULL).
"""
import logging
import os
import subprocess
from typing import List, Optional, Tuple

logger = logging.getLogger("duckdock.deck.launcher")

# Флаги создания процессов Windows
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

KNOWN_PROTOCOLS = (
    "http://",
    "https://",
    "discord://",
    "spotify://",
    "steam://",
    "mailto:",
)


def launch_process(
    path: str,
    args: Optional[List[str]] = None,
    working_dir: Optional[str] = None,
    detached: bool = True,
) -> Tuple[bool, str]:
    """
    Запускает программу, скрипт или URL-протокол.
    - path: путь к файлу или URL
    - args: аргументы командной строки
    - working_dir: рабочая директория (разворачивает %VARS%)
    - detached: флаг CREATE_NO_WINDOW | DETACHED_PROCESS
    """
    if not path or not path.strip():
        return False, "Указан пустой путь запуска"

    clean_path = path.strip()
    expanded_path = os.path.expandvars(clean_path)

    # Проверка на URL или протокольное обращение
    is_protocol = any(expanded_path.lower().startswith(p) for p in KNOWN_PROTOCOLS)
    if is_protocol:
        try:
            if hasattr(os, "startfile"):
                os.startfile(expanded_path)
            else:
                subprocess.Popen(
                    ["cmd.exe", "/c", "start", "", expanded_path],
                    creationflags=CREATE_NO_WINDOW,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            logger.info(f"Запущен протокол/URL: {expanded_path}")
            return True, f"Запущен URL: {expanded_path}"
        except Exception as e:
            logger.error(f"Ошибка открытия URL '{expanded_path}': {e}")
            return False, f"Ошибка запуска URL: {e}"

    # Подготовка аргументов и рабочей директории
    cmd_args = [expanded_path]
    if args:
        cmd_args.extend([os.path.expandvars(str(a)) for a in args])

    cwd = os.path.expandvars(working_dir) if working_dir else None
    if cwd and not os.path.isdir(cwd):
        cwd = None

    creationflags = 0
    if detached:
        creationflags = CREATE_NO_WINDOW | DETACHED_PROCESS

    try:
        subprocess.Popen(
            cmd_args,
            cwd=cwd,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        logger.info(f"Успешно запущен процесс: {' '.join(cmd_args)}")
        return True, f"Процесс '{os.path.basename(expanded_path)}' успешно запущен"
    except FileNotFoundError:
        logger.error(f"Файл не найден для запуска: {expanded_path}")
        return False, f"Исполняемый файл не найден: {expanded_path}"
    except Exception as e:
        logger.error(f"Ошибка при запуске процесса {cmd_args}: {e}")
        return False, f"Ошибка запуска: {e}"
