"""
Фикстуры для тестирования компонентов DuckDock.
"""
import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Инициализация COM до старта QApplication для предотвращения RPC_E_CHANGED_MODE
try:
    import comtypes
except Exception:
    pass

from contextlib import contextmanager
from typing import Optional
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

@pytest.fixture(scope="session")
def qapp():
    """Создает сессионный экземпляр QApplication для тестов виджетов."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class SignalBlocker:
    """Контейнер захваченного сигнала для waitSignal."""

    def __init__(self) -> None:
        self.signal_triggered: bool = False
        self.args: list = []


class QtBotFixture:
    """Хелпер имитации действий пользователя над виджетами Qt через QTest (совместимость с pytest-qtbot)."""

    def __init__(self, qapp):
        self._qapp = qapp
        self._widgets: list[QWidget] = []

    def addWidget(self, widget: QWidget) -> None:
        """Регистрирует виджет для автоматической обработки и отображения."""
        if widget not in self._widgets:
            self._widgets.append(widget)
        self._qapp.processEvents()

    @contextmanager
    def waitSignal(self, signal, timeout: int = 1000):
        """Контекстный менеджер ожидания сигнала Qt."""
        blocker = SignalBlocker()

        def slot(*args):
            blocker.signal_triggered = True
            blocker.args = list(args)

        signal.connect(slot)
        try:
            yield blocker
        finally:
            self._qapp.processEvents()
            try:
                signal.disconnect(slot)
            except Exception:
                pass

    def mouseClick(
        self,
        widget: QWidget,
        button: Qt.MouseButton = Qt.LeftButton,
        modifier: Qt.KeyboardModifier = Qt.NoModifier,
        pos: Optional[QPoint] = None,
        delay: int = -1,
    ) -> None:
        """Имитирует клик мыши по виджету."""
        if pos is not None:
            QTest.mouseClick(widget, button, modifier, pos, delay)
        else:
            QTest.mouseClick(widget, button, modifier)
        self._qapp.processEvents()

    def keyClick(
        self,
        widget: QWidget,
        key: Qt.Key,
        modifier: Qt.KeyboardModifier = Qt.NoModifier,
        delay: int = -1,
    ) -> None:
        """Имитирует нажатие клавиши на клавиатуре."""
        QTest.keyClick(widget, key, modifier, delay)
        self._qapp.processEvents()

    def wait(self, ms: int = 50) -> None:
        """Приостанавливает выполнение на ms миллисекунд с обработкой событий Qt."""
        QTest.qWait(ms)
        self._qapp.processEvents()


@pytest.fixture
def qtbot(qapp):
    """Фикстура qtbot для тестирования UI компонентов."""
    return QtBotFixture(qapp)

