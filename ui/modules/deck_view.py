"""
Сенсорная макро-панель DuckDeck (Presentation Layer).
Оптимизирована под геометрию рабочего пространства 944x600 (7" Touchscreen).
Архитектурные инварианты:
  - 100% элементов имеют Qt.NoFocus для сохранения фокуса на основном мониторе.
  - Сенсорные тайлы поддерживают точные размеры 174x168 px (3x5) и 143x123 px (4x6).
  - Отсутствие залипающего :hover на тач-экранах; управление через свойства [state="..."]:
    idle, pressed, executing, success, error.
  - Тактильный отклик: вдавливание на 2 px и шейк содержимого через _content_offset без поломки QGridLayout.
  - Централизованная реактивность Live Dynamic Tiles и безопасная отписка от EventBus без утечек.
"""
import logging
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.audio_manager import AudioManager
from core.deck.action_dispatcher import DeckActionDispatcher
from core.deck.models import (
    DeckButtonConfig,
    DeckConfigLoader,
    DeckPageConfig,
    DeckRootConfig,
    NavigationParams,
)
from core.event_bus import bus

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


class DeckButtonWidget(QFrame):
    """
    Базовый сенсорный тайл макро-панели DuckDeck.
    Инварианты:
      - Qt.NoFocus и Qt.WA_AcceptTouchEvents.
      - Точные габариты: 174x168 px (3x5) или 143x123 px (4x6).
      - Визуальная тактильность без залипающего :hover (через свойство [state="..."]).
      - Сдвиг содержимого _content_offset (вдавливание и шейк) без поломки внешнего QGridLayout.
    """
    triggered = Signal(object)  # DeckButtonConfig

    def __init__(
        self,
        button_config: DeckButtonConfig,
        rows: int = 3,
        cols: int = 5,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.button_config = button_config
        self.rows = rows
        self.cols = cols

        # Инварианты фокуса и сенсорного ввода
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.setObjectName("DeckButtonWidget")
        self.setProperty("class", "deck-button")

        # Геометрия тайла под сетку
        if self.cols == 6 or self.rows == 4:
            self.tile_width = 143
            self.tile_height = 123
            self.corner_radius = 10
            self.icon_font_size = 28
            self.title_font_size = 11
            self.status_font_size = 9
        else:
            self.tile_width = 174
            self.tile_height = 168
            self.corner_radius = 14
            self.icon_font_size = 38
            self.title_font_size = 13
            self.status_font_size = 10

        self.setFixedSize(self.tile_width, self.tile_height)

        # Состояния и тактильный сдвиг содержимого
        self._state: str = "idle"
        self._is_pressed: bool = False
        self._content_offset_x: int = 0
        self._content_offset_y: int = 0

        # Таймеры анимаций
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._on_reset_timeout)

        self._shake_timer = QTimer(self)
        self._shake_timer.setInterval(35)
        self._shake_timer.timeout.connect(self._on_shake_tick)
        self._shake_sequence: List[int] = []
        self._shake_step: int = 0

        # Построение разметки
        self._setup_ui()
        self.set_state("idle")

    def _setup_ui(self) -> None:
        """Инициализация внутренней компоновки и элементов тайла."""
        self._content_layout = QVBoxLayout(self)
        self._content_layout.setSpacing(4)
        self._apply_content_offset()

        # Иконка тайла
        self.lbl_icon = QLabel(self.button_config.icon, self)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setFocusPolicy(Qt.NoFocus)
        self.lbl_icon.setStyleSheet(
            f"font-size: {self.icon_font_size}px; color: {self.button_config.color_accent};"
        )
        self._content_layout.addWidget(self.lbl_icon)

        # Заголовок тайла
        self.lbl_title = QLabel(self.button_config.title, self)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setFocusPolicy(Qt.NoFocus)
        self.lbl_title.setProperty("class", "deck-btn-title")
        self.lbl_title.setStyleSheet(f"font-size: {self.title_font_size}px;")
        self._content_layout.addWidget(self.lbl_title)

        # Метка статуса (Live Dynamic Tiles)
        self.lbl_status = QLabel("", self)
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFocusPolicy(Qt.NoFocus)
        self.lbl_status.setProperty("class", "deck-btn-status")
        self.lbl_status.setStyleSheet(f"font-size: {self.status_font_size}px;")
        self.lbl_status.setVisible(False)
        self._content_layout.addWidget(self.lbl_status)

        # Применение скругления через локальный стиль
        self._update_border_style()

    def _update_border_style(self) -> None:
        """Синхронизирует радиус скругления с геометрией сетки."""
        self.setStyleSheet(
            f"QFrame.deck-button {{ border-radius: {self.corner_radius}px; }}"
        )

    @property
    def state(self) -> str:
        """Текущее состояние тайла."""
        return self._state

    @property
    def content_offset(self) -> Tuple[int, int]:
        """Текущий вектор тактильного сдвига содержимого (dx, dy)."""
        return (self._content_offset_x, self._content_offset_y)

    def set_content_offset(self, dx: int, dy: int) -> None:
        """Устанавливает смещение содержимого без изменения внешней геометрии в QGridLayout."""
        self._content_offset_x = dx
        self._content_offset_y = dy
        self._apply_content_offset()

    def _apply_content_offset(self) -> None:
        """Применяет смещение содержимого через внутренние поля макета."""
        base_margin = 8
        left = max(0, base_margin + self._content_offset_x)
        top = max(0, base_margin + self._content_offset_y)
        right = max(0, base_margin - self._content_offset_x)
        bottom = max(0, base_margin - self._content_offset_y)
        self._content_layout.setContentsMargins(left, top, right, bottom)

    def set_state(self, state: str) -> None:
        """
        Переключение визуального состояния тайла.
        Поддерживаемые состояния:
          - 'idle': базовое фоновое состояние.
          - 'pressed': тактильное вдавливание (+2 px вниз) и затемнение.
          - 'executing': индикация исполнения (акцентная рамка).
          - 'success': кратковременная изумрудная рамка (600 мс).
          - 'error': рубиновая рамка (800 мс) и шейк содержимого _content_offset.
        """
        self._state = state
        self.setProperty("state", state)

        # Остановка таймеров
        self._reset_timer.stop()
        if state != "error" and self._shake_timer.isActive():
            self._shake_timer.stop()

        if state == "idle":
            self.set_content_offset(0, 0)

        elif state == "pressed":
            # Тактильное вдавливание содержимого на 2 px вниз
            self.set_content_offset(0, 2)
            # Защитный таймаут от залипания тач-касания (3 сек)
            self._reset_timer.start(3000)

        elif state == "executing":
            self.set_content_offset(0, 0)
            # Сторожевой таймер (Watchdog): авто-сброс подсветки через 4 сек при задержке/зависании
            self._reset_timer.start(4000)

        elif state == "success":
            self.set_content_offset(0, 0)
            self._reset_timer.start(600)

        elif state == "error":
            # Запуск шейк-анимации содержимого
            self._start_shake()
            self._reset_timer.start(800)

        # Обновление стилей Qt
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _start_shake(self) -> None:
        """Инициализация последовательности тактильного шейка."""
        self._shake_sequence = [-6, 6, -4, 4, -2, 2, 0]
        self._shake_step = 0
        self._shake_timer.start()

    def _on_shake_tick(self) -> None:
        """Шаг тактильного колебания содержимого тайла."""
        if self._shake_step < len(self._shake_sequence):
            dx = self._shake_sequence[self._shake_step]
            self.set_content_offset(dx, 0)
            self._shake_step += 1
        else:
            self._shake_timer.stop()
            self.set_content_offset(0, 0)

    def _on_reset_timeout(self) -> None:
        """Автоматический возврат в состояние idle."""
        self.set_state("idle")

    def update_status(
        self,
        status_text: Optional[str] = None,
        icon: Optional[str] = None,
        title: Optional[str] = None,
    ) -> None:
        """Централизованное обновление динамического содержимого живого тайла."""
        if icon is not None:
            self.lbl_icon.setText(icon)
        if title is not None:
            self.lbl_title.setText(title)
        if status_text is not None:
            clean_status = status_text.strip()
            if clean_status:
                self.lbl_status.setText(clean_status)
                self.lbl_status.setVisible(True)
            else:
                self.lbl_status.setText("")
                self.lbl_status.setVisible(False)

    # ---------------------------------------------------------
    # Сенсорные и мышиные события (Stealth / Anti-Sticky Hover)
    # ---------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._is_pressed = True
            self.set_state("pressed")
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._is_pressed and event.button() == Qt.LeftButton:
            self._is_pressed = False
            # Проверяем, отпущена ли точка внутри геометрии кнопки
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            if self.rect().contains(pos):
                self.set_state("executing")
                self.triggered.emit(self.button_config)
            else:
                self.set_state("idle")
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if self._is_pressed:
            self._is_pressed = False
            self.set_state("idle")
        super().leaveEvent(event)

    def cleanup(self) -> None:
        """Остановка всех активных таймеров виджета."""
        if self._reset_timer.isActive():
            self._reset_timer.stop()
        if self._shake_timer.isActive():
            self._shake_timer.stop()


class DeckGrid(QWidget):
    """
    Контейнер сетки сенсорных кнопок DuckDeck.
    Габариты строго 944x552 px (с отступами 12 px и промежутками 12 px).
    """
    button_triggered = Signal(object)  # DeckButtonConfig

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DeckGrid")
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(944, 552)

        self._buttons: Dict[str, DeckButtonWidget] = {}

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)
        self.grid_layout.setSpacing(12)

    def load_page(self, page_config: DeckPageConfig) -> None:
        """
        Загрузка страницы кнопок с очисткой предыдущих виджетов без утечек памяти.
        """
        # Очистка существующих элементов
        self.clear()

        rows = page_config.grid_rows or 3
        cols = page_config.grid_cols or 5

        # Размещение кнопок по формуле: row = idx // cols, col = idx % cols
        for idx, btn_cfg in enumerate(page_config.buttons):
            row = idx // cols
            col = idx % cols
            if row >= rows:
                logger.warning(
                    f"Кнопка '{btn_cfg.id}' выходит за пределы сетки ({rows}x{cols})"
                )
                break

            btn_widget = DeckButtonWidget(
                button_config=btn_cfg,
                rows=rows,
                cols=cols,
                parent=self,
            )
            btn_widget.triggered.connect(self.button_triggered.emit)
            self.grid_layout.addWidget(btn_widget, row, col, Qt.AlignCenter)
            self._buttons[btn_cfg.id] = btn_widget

        # Заполнение пустых ячеек сетки распорками для сохранения жесткой геометрии
        total_cells = rows * cols
        buttons_count = len(self._buttons)
        if buttons_count < total_cells:
            for idx in range(buttons_count, total_cells):
                r = idx // cols
                c = idx % cols
                spacer = QSpacerItem(
                    174 if cols == 5 else 143,
                    168 if rows == 3 else 123,
                    QSizePolicy.Fixed,
                    QSizePolicy.Fixed,
                )
                self.grid_layout.addItem(spacer, r, c)

    def get_button(self, button_id: str) -> Optional[DeckButtonWidget]:
        """Получить виджет кнопки по ее ID."""
        return self._buttons.get(button_id)

    def get_buttons(self) -> Dict[str, DeckButtonWidget]:
        """Возвращает словарь всех активных кнопок сетки."""
        return self._buttons.copy()

    def clear(self) -> None:
        """Безопасная очистка сетки с удалением виджетов через deleteLater."""
        for btn in self._buttons.values():
            btn.cleanup()
            btn.setParent(None)
            btn.deleteLater()
        self._buttons.clear()

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def cleanup(self) -> None:
        """Освобождение ресурсов сетки."""
        self.clear()


class HeaderBar(QFrame):
    """
    Верхняя панель управления DuckDeck (высота 48 px).
    Включает:
      - Полосу кнопок-пилюль страниц/профилей (слева).
      - Текстовый индикатор статуса фоновых процессов (по центру).
      - Кнопку быстрой перезагрузки JSON конфигурации (справа).
    """
    page_selected = Signal(str)    # page_id
    reload_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DeckHeaderBar")
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(48)
        self.setFixedWidth(944)

        self._pill_buttons: Dict[str, QPushButton] = {}
        self._active_page_id: str = ""

        # Таймер угасания строки статуса
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Контейнер кнопок-пилюль
        self.pills_container = QWidget(self)
        self.pills_container.setFocusPolicy(Qt.NoFocus)
        self.pills_layout = QHBoxLayout(self.pills_container)
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(6)
        layout.addWidget(self.pills_container, 0, Qt.AlignLeft)

        # Центральный индикатор статуса
        self.lbl_status = QLabel("", self)
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFocusPolicy(Qt.NoFocus)
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_status, 1, Qt.AlignCenter)

        # Кнопка перезагрузки JSON конфигурации
        self.btn_reload = QPushButton("🔄", self)
        self.btn_reload.setFocusPolicy(Qt.NoFocus)
        self.btn_reload.setFixedSize(36, 36)
        self.btn_reload.setProperty("class", "deck-reload-btn")
        self.btn_reload.setToolTip("Перезагрузить deck_config.json")
        self.btn_reload.clicked.connect(self.reload_requested.emit)
        layout.addWidget(self.btn_reload, 0, Qt.AlignRight)

    def set_pages(self, pages: List[DeckPageConfig], active_page_id: str) -> None:
        """Формирует кнопки страниц-профилей."""
        # Очистка предыдущих кнопок
        for btn in self._pill_buttons.values():
            btn.setParent(None)
            btn.deleteLater()
        self._pill_buttons.clear()

        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._active_page_id = active_page_id

        for page in pages:
            btn = QPushButton(page.name, self.pills_container)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setProperty("class", "deck-pill-btn")
            btn.setProperty("active", "true" if page.id == active_page_id else "false")
            btn.clicked.connect(lambda checked=False, pid=page.id: self.page_selected.emit(pid))
            self.pills_layout.addWidget(btn)
            self._pill_buttons[page.id] = btn

    def set_active_page(self, page_id: str) -> None:
        """Переключает активную вкладку страницы."""
        self._active_page_id = page_id
        for pid, btn in self._pill_buttons.items():
            is_act = (pid == page_id)
            btn.setProperty("active", "true" if is_act else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def set_status(self, text: str, timeout_ms: int = 4000) -> None:
        """Отображает угасающее статусное сообщение."""
        self.lbl_status.setText(text)
        self._status_timer.stop()
        if text and timeout_ms > 0:
            self._status_timer.start(timeout_ms)

    def _clear_status(self) -> None:
        self.lbl_status.setText("")

    def cleanup(self) -> None:
        """Очистка таймеров шапки."""
        if self._status_timer.isActive():
            self._status_timer.stop()


class DeckView(QWidget):
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
        audio_manager: Optional[AudioManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.config_path = config_path
        self.audio_manager = audio_manager or AudioManager()
        self.dispatcher = dispatcher or DeckActionDispatcher(
            audio_manager=self.audio_manager,
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
            # 1. Аудиовыход
            dev_name = self.audio_manager.get_master_device_name()
            dev_id = self.audio_manager.get_default_playback_device_id() or ""
            self._on_playback_device_changed(dev_name, dev_id)

            # 2. Микрофон
            is_mic_muted = self.audio_manager.is_mic_muted()
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

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)
