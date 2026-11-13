"""
Фикстуры для тестирования компонентов DuckDock.
"""
import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    """Создает сессионный экземпляр QApplication для тестов виджетов."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
