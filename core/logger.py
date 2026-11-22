"""
Централизованная подсистема логирования DuckDock.
Настраивает ротацию лог-файлов (logs/duckdock.log) и консольный вывод с перехватом sys.excepthook.
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def init_logging(
    log_dir: str | Path = "logs",
    log_filename: str = "duckdock.log",
    level: int = logging.INFO,
    force: bool = False,
) -> logging.Logger:
    """
    Инициализирует глобальное логирование в файл с ротацией и консоль.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    full_log_file = log_path / log_filename

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if force:
        for h in list(root_logger.handlers):
            if isinstance(h, logging.FileHandler):
                h.close()
                root_logger.removeHandler(h)
        has_file = False
    else:
        # Предотвращаем повторное добавление файловых обработчиков для того же файла
        has_file = any(
            isinstance(h, RotatingFileHandler)
            and getattr(h, "baseFilename", "") == str(full_log_file.resolve())
            for h in root_logger.handlers
        )

    if not has_file:
        file_handler = RotatingFileHandler(
            full_log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    has_stream = any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root_logger.handlers)
    if not has_stream:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 3. Перехват необработанных исключений верхнего уровня
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root_logger.critical(
            "Необработанное исключение процесса:",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_exception

    logger = logging.getLogger("duckdock")
    logger.info("Подсистема логирования инициализирована. Лог-файл: %s", full_log_file.resolve())
    return logger
