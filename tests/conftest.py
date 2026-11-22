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


@pytest.fixture
def sample_two_page_deck_config_path(tmp_path):
    """
    Создает изолированный временный файл конфигурации DuckDeck с двумя страницами
    ('default' с тестовыми кнопками и 'grid4x6' для тестирования навигации и свайпов).
    Предотвращает загрязнение и зависимость тестов от боевого config/deck_config.json.
    """
    from modules.deck.models import (
        DeckActionConfig,
        DeckButtonConfig,
        DeckConfigLoader,
        DeckPageConfig,
        DeckRootConfig,
        SoundSettings,
    )

    buttons_p1 = [
        DeckButtonConfig(
            id="btn_toggle_audio_device",
            slot_index=0,
            name="Аудиовыход",
            title="Аудиовыход",
            category="system",
            icon="🎧",
            icon_path="resources/deck/icons/system/sound.png",
            icon_size=48,
            color_accent="#06b6d4",
            status_source="audio_device",
            action=DeckActionConfig(
                action_type="audio",
                params={"target": "device", "command": "toggle_device", "devices": ["Наушники", "Динамики"]},
            ),
        ),
        DeckButtonConfig(
            id="btn_mute_mic",
            slot_index=1,
            name="Микрофон",
            title="Микрофон",
            category="system",
            icon="🎙",
            icon_path="resources/deck/icons/system/mic.png",
            icon_size=48,
            color_accent="#ef4444",
            status_source="mic_mute",
            action=DeckActionConfig(
                action_type="audio",
                params={"target": "mic", "command": "toggle_mute"},
            ),
        ),
        DeckButtonConfig(
            id="btn_screenshot_primary",
            slot_index=2,
            name="Скриншот",
            title="Скриншот",
            category="system",
            icon="📸",
            icon_path="resources/deck/icons/system/screenshot.png",
            icon_size=48,
            color_accent="#38bdf8",
            action=DeckActionConfig(
                action_type="system",
                params={"command": "screenshot", "screenshot_target": "primary"},
            ),
        ),
        DeckButtonConfig(
            id="btn_toggle_dimmer",
            slot_index=7,
            name="Ночной режим",
            title="Ночной режим",
            category="system",
            icon="🌙",
            icon_path="resources/deck/icons/system/dimmer.png",
            icon_size=48,
            color_accent="#a855f7",
            status_source="dimmer",
            action=DeckActionConfig(
                action_type="system",
                params={"command": "dimmer"},
            ),
        ),
    ]

    buttons_p2 = [
        DeckButtonConfig(
            id="btn_stream_back",
            slot_index=0,
            name="Назад",
            title="Назад",
            category="navigation",
            icon="◀",
            icon_size=48,
            color_accent="#38bdf8",
            action=DeckActionConfig(
                action_type="navigation",
                params={"target_page_id": "default"},
            ),
        ),
    ]

    root = DeckRootConfig(
        active_profile="default",
        simulation_mode=False,
        sound_settings=SoundSettings(),
        pages=[
            DeckPageConfig(
                id="default",
                name="Основной",
                grid_rows=2,
                grid_cols=5,
                buttons=buttons_p1,
            ),
            DeckPageConfig(
                id="grid4x6",
                name="Стриминг",
                grid_rows=2,
                grid_cols=5,
                buttons=buttons_p2,
            ),
        ],
    )

    cfg_file = tmp_path / "deck_test_isolated.json"
    DeckConfigLoader.save_to_file(root, str(cfg_file))
    return str(cfg_file)


