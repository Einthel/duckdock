"""
Сенсорная макро-панель DuckDeck (Presentation Layer).
Оптимизирована под геометрию рабочего пространства 944x600 (7" Touchscreen).
Архитектурные инварианты:
  - Наследование от TouchModuleView (Qt.NoFocus для сохранения фокуса на основном мониторе).
  - Сенсорные тайлы поддерживают точные размеры 174x168 px (3x5) и 143x123 px (4x6).
  - Отсутствие залипающего :hover на тач-экранах; управление через свойства [state="..."]:
    idle, pressed, executing, success, error.
  - Тактильный отклик: вдавливание на 2 px и шейк содержимого через _content_offset без поломки QGridLayout.
  - Централизованная реактивность Live Dynamic Tiles и безопасная отписка от EventBus без утечек.
  - Sibling Decoupling: AudioManager принимается опционально через DI.
"""
import logging
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from core.event_bus import bus
from core.ui_base import TouchModuleView
from modules.deck.action_dispatcher import DeckActionDispatcher
from modules.deck.models import (
    DeckButtonConfig,
    DeckConfigLoader,
    DeckRootConfig,
    NavigationParams,
)
from modules.deck.widgets.deck_button import DeckButtonWidget
from modules.deck.widgets.deck_grid import DeckGrid
from modules.deck.widgets.header_bar import HeaderBar

logger = logging.getLogger("duckdock.deck.ui")

DECK_QSS = """
/* Базовый контейнер DeckView */
QWidget#DeckView {
    background-color: #0b0f19;
}

/* Верхняя панель HeaderBar */
QFrame#DeckHeaderBar {
    background-color: #111622;
    border-bottom: 1px solid #1e2638;
}

/* Кнопки-пилюли вкладок страниц */
QPushButton.deck-pill-btn {
    background-color: #161b26;
    color: #94a3b8;
    border: 1px solid #232b3e;
    border-radius: 16px;
    padding: 4px 16px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton.deck-pill-btn[active="true"] {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
    font-weight: bold;
}

/* Кнопка быстрой перезагрузки JSON */
QPushButton.deck-reload-btn {
    background-color: #161b26;
    color: #94a3b8;
    border: 1px solid #232b3e;
    border-radius: 10px;
    font-size: 16px;
}

QPushButton.deck-reload-btn:pressed {
    background-color: #1f293d;
    border-color: #38bdf8;
    color: #38bdf8;
}

/* Сенсорный тайл DeckButtonWidget (состояния [state="..."]) */
QFrame.deck-button {
    background-color: #161b26;
    border: 1px solid #232b3e;
}

QFrame.deck-button[state="idle"] {
    background-color: #161b26;
    border: 1px solid #232b3e;
}

QFrame.deck-button[state="pressed"] {
    background-color: #10141d;
    border: 1px solid #334155;
}

QFrame.deck-button[state="executing"] {
    background-color: #161b26;
    border: 2px solid #38bdf8;
}

QFrame.deck-button[state="success"] {
    background-color: #12241e;
    border: 2px solid #10b981;
}

QFrame.deck-button[state="error"] {
    background-color: #271417;
    border: 2px solid #ef4444;
}

/* Текстовые метки тайла */
QLabel.deck-btn-title {
    color: #e2e8f0;
    font-weight: bold;
}

QLabel.deck-btn-status {
    color: #94a3b8;
}
"""


class DeckView(TouchModuleView):
    """
    Главный интерфейсный модуль сенсорной макро-панели DuckDeck.
    Габариты: 944x600 px (HeaderBar 48 px + DeckGrid 552 px).
    Реализует:
      - Связку с DeckActionDispatcher (асинхронное исполнение с антидребезгом).
      - Централизованную реактивность Live Dynamic Tiles (EventBus).
      - Поддержку многостраничности и горячей перезагрузки конфигурации.
      - Гарантированную отписку от шины событий без утечек памяти.
    """

    def __init__(
        self,
        config_path: str = "config/deck_config.json",
        dispatcher: Optional[DeckActionDispatcher] = None,
        audio_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.config_path = config_path
        self._audio_manager = audio_manager
        self.dispatcher = dispatcher or DeckActionDispatcher(
            audio_manager=self._audio_manager,
            parent=self,
        )

        # Инварианты геометрии и фокуса
        self.setObjectName("DeckView")
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(944, 600)
        self.setStyleSheet(DECK_QSS)

        self.root_config: Optional[DeckRootConfig] = None
        self.active_page_id: str = "default"
        self._eventbus_connected: bool = False

        self._setup_ui()
        self._connect_signals()
        self._subscribe_eventbus()
        self.load_config()

    @property
    def audio_manager(self) -> Any:
        """Ленивая инициализация или получение внедренного аудиоменеджера."""
        if self._audio_manager is None:
            try:
                from modules.audio.service import AudioManager
                self._audio_manager = AudioManager()
            except Exception as e:
                logger.debug(f"Не удалось инициализировать AudioManager: {e}")
        return self._audio_manager

    @audio_manager.setter
    def audio_manager(self, value: Any) -> None:
        self._audio_manager = value

    def _setup_ui(self) -> None:
        """Построение вертикального макета DeckView."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header_bar = HeaderBar(self)
        layout.addWidget(self.header_bar)

        self.grid = DeckGrid(self)
        layout.addWidget(self.grid)

    def _connect_signals(self) -> None:
        """Внутренние сигналы между компонентами UI и диспетчером действий."""
        self.grid.button_triggered.connect(self._on_button_triggered)
        self.header_bar.page_selected.connect(self.set_active_page)
        self.header_bar.reload_requested.connect(self.reload_config)

        self.dispatcher.action_started.connect(self._on_action_started)
        self.dispatcher.action_finished.connect(self._on_action_finished)

    def _subscribe_eventbus(self) -> None:
        """Подписка на сигналы шины событий для живых тайлов."""
        if not self._eventbus_connected:
            bus.playback_device_changed.connect(self._on_playback_device_changed)
            bus.mic_mute_changed.connect(self._on_mic_mute_changed)
            bus.dimmer_opacity_changed.connect(self._on_dimmer_opacity_changed)
            self._eventbus_connected = True

    def _unsubscribe_eventbus(self) -> None:
        """Безопасная отписка от шины событий без возникновения исключений."""
        if self._eventbus_connected:
            try:
                bus.playback_device_changed.disconnect(self._on_playback_device_changed)
            except Exception:
                pass
            try:
                bus.mic_mute_changed.disconnect(self._on_mic_mute_changed)
            except Exception:
                pass
            try:
                bus.dimmer_opacity_changed.disconnect(self._on_dimmer_opacity_changed)
            except Exception:
                pass
            self._eventbus_connected = False

    def load_config(self) -> None:
        """Загрузка конфигурации макро-панели с откатом на дефолт при ошибке."""
        self.root_config = DeckConfigLoader.load_from_file(self.config_path)
        if not self.root_config.pages:
            self.root_config = DeckConfigLoader.get_default_config()

        self.active_page_id = self.root_config.active_profile or self.root_config.pages[0].id
        self.header_bar.set_pages(self.root_config.pages, self.active_page_id)
        self.set_active_page(self.active_page_id)

    def reload_config(self) -> None:
        """Горячая перезагрузка конфигурации с уведомлением в шапке."""
        try:
            self.load_config()
            self.header_bar.set_status("Конфигурация перезагружена")
        except Exception as e:
            logger.error(f"Ошибка перезагрузки конфигурации DuckDeck: {e}")
            self.header_bar.set_status(f"Ошибка: {e}")

    def set_active_page(self, page_id: str) -> None:
        """Переключение отображаемой страницы сетки."""
        if not self.root_config:
            return

        target_page = next((p for p in self.root_config.pages if p.id == page_id), None)
        if not target_page:
            logger.warning(f"Страница '{page_id}' не найдена в конфигурации DuckDeck")
            return

        self.active_page_id = page_id
        self.header_bar.set_active_page(page_id)
        self.grid.load_page(target_page)

        # Начальная синхронизация Live Dynamic Tiles с реальным состоянием
        self._sync_live_tiles()

    def _on_button_triggered(self, btn_config: DeckButtonConfig) -> None:
        """Обработка нажатия на кнопку тайла."""
        # Навигационные действия обрабатываются внутри UI без отправки в worker thread
        if btn_config.action.action_type == "navigation":
            typed = btn_config.action.get_typed_params()
            if isinstance(typed, NavigationParams):
                self.set_active_page(typed.target_page_id)
                self.header_bar.set_status(f"Страница: {typed.target_page_id}")
                btn = self.grid.get_button(btn_config.id)
                if btn:
                    btn.set_state("success")
                return

        # Отправка действия в ActionDispatcher
        accepted = self.dispatcher.dispatch(btn_config.id, btn_config.action)
        if not accepted:
            # Сработал антидребезг (cooldown 250 мс)
            btn = self.grid.get_button(btn_config.id)
            if btn:
                btn.set_state("idle")

    def _on_action_started(self, button_id: str) -> None:
        """Индикация начала исполнения действия."""
        btn = self.grid.get_button(button_id)
        if btn:
            btn.set_state("executing")

    def _on_action_finished(self, button_id: str, success: bool, message: str) -> None:
        """Индикация завершения действия."""
        btn = self.grid.get_button(button_id)
        if btn:
            btn.set_state("success" if success else "error")

        if message:
            self.header_bar.set_status(message)

    # ---------------------------------------------------------
    # Централизованная реактивность Live Dynamic Tiles
    # ---------------------------------------------------------
    def _sync_live_tiles(self) -> None:
        """Первичная синхронизация живых тайлов текущей страницы."""
        try:
            mgr = self.audio_manager
            if mgr is not None:
                # 1. Аудиовыход
                dev_name = mgr.get_master_device_name()
                dev_id = mgr.get_default_playback_device_id() or ""
                self._on_playback_device_changed(dev_name, dev_id)

                # 2. Микрофон
                is_mic_muted = mgr.is_mic_muted()
                self._on_mic_mute_changed(is_mic_muted)
        except Exception as e:
            logger.debug(f"Ошибка первичной синхронизации живых тайлов: {e}")

    def _on_playback_device_changed(self, device_name: str, device_id: str) -> None:
        """Обновление тайлов с источником статуса 'audio_device'."""
        is_headphones = any(k in device_name.lower() for k in ["наушники", "headphone", "headset"])
        icon = "🎧" if is_headphones else "🔊"

        for btn in self.grid.get_buttons().values():
            if btn.button_config.status_source == "audio_device":
                btn.update_status(status_text=device_name, icon=icon)

    def _on_mic_mute_changed(self, is_muted: bool) -> None:
        """Обновление тайлов с источником статуса 'mic_mute'."""
        icon = "🔇" if is_muted else "🎙"
        status_text = "Выключен" if is_muted else "Включен"

        for btn in self.grid.get_buttons().values():
            if btn.button_config.status_source == "mic_mute":
                btn.update_status(status_text=status_text, icon=icon)

    def _on_dimmer_opacity_changed(self, opacity: float) -> None:
        """Обновление тайлов с источником статуса 'dimmer'."""
        status_text = f"{int(opacity * 100)}%" if opacity > 0.0 else "Выкл"
        for btn in self.grid.get_buttons().values():
            if btn.button_config.status_source == "dimmer":
                btn.update_status(status_text=status_text)

    # ---------------------------------------------------------
    # Жизненный цикл и гарантированное освобождение ресурсов
    # ---------------------------------------------------------
    def cleanup(self) -> None:
        """Гарантированное освобождение ресурсов при закрытии или смене вкладки."""
        self._unsubscribe_eventbus()
        self.header_bar.cleanup()
        self.grid.cleanup()
        super().cleanup()

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)


__all__ = [
    "DECK_QSS",
    "DeckButtonWidget",
    "DeckGrid",
    "HeaderBar",
    "DeckView",
]
