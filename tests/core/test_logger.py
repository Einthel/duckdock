"""
Тесты инициализации и ротации логирования DuckDock (core/logger.py).
"""
import logging
import tempfile
from pathlib import Path

from core.logger import init_logging


def test_init_logging_creates_file_and_handlers():
    """Проверка создания лог-файла и настройки RotatingFileHandler."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = init_logging(log_dir=tmp_dir, log_filename="test_duckdock.log", force=True)
        assert logger is not None
        log_file = Path(tmp_dir) / "test_duckdock.log"
        assert log_file.exists()

        logger.info("Test message for logging system verification")
        content = log_file.read_text(encoding="utf-8")
        assert "Test message for logging system verification" in content

        # Закрываем и удаляем файловый обработчик для освобождения дескриптора на Windows
        for h in list(logging.getLogger().handlers):
            if isinstance(h, logging.FileHandler):
                h.close()
                logging.getLogger().removeHandler(h)
