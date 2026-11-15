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
                subprocess.Popen(["cmd", "/c", "start", "", expanded_path], shell=False)
            logger.info(f"Успешно запущен URL/протокол: {expanded_path}")
            return True, f"Запущен URL: {expanded_path}"
        except Exception as e:
            logger.error(f"Ошибка открытия протокола '{expanded_path}': {e}")
            return False, f"Ошибка открытия протокола: {e}"

    # Обработка рабочей директории
    actual_cwd = None
    if working_dir and working_dir.strip():
        actual_cwd = os.path.expandvars(working_dir.strip())
        if not os.path.isdir(actual_cwd):
            actual_cwd = None

    cmd = [expanded_path]
    if args:
        cmd.extend(args)

    creationflags = 0
    if detached:
        creationflags = CREATE_NO_WINDOW | DETACHED_PROCESS

    try:
        subprocess.Popen(
            cmd,
            cwd=actual_cwd,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        logger.info(f"Успешно запущен процесс: {' '.join(cmd)}")
        return True, f"Запущен: {os.path.basename(expanded_path)}"
    except FileNotFoundError:
        err_msg = f"Файл не найден: {expanded_path}"
        logger.error(err_msg)
        return False, err_msg
    except Exception as e:
        err_msg = f"Ошибка запуска '{expanded_path}': {e}"
        logger.error(err_msg)
        return False, err_msg


__all__ = [
    "CREATE_NO_WINDOW",
    "DETACHED_PROCESS",
    "KNOWN_PROTOCOLS",
    "launch_process",
]
