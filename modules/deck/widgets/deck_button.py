"""
Сенсорный тайл кнопки макро-панели DuckDeck.
"""
import time
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer, Signal, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QTouchEvent, QEventPoint
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from modules.deck.models import DeckButtonConfig
from modules.deck.widgets.swipe_detector import _extract_point_pos


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
        rows: int = 2,
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
        self._swipe_consumed: bool = False
        self._press_start_pos: Optional[QPointF] = None
        self._press_start_time: float = 0.0
        self._swipe_threshold_dx: float = 20.0
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
    def is_pressed(self) -> bool:
        """Флаг активного нажатия кнопки."""
        return self._is_pressed

    @property
    def swipe_consumed(self) -> bool:
        """Флаг поглощения жестом (подавление клика при отпускании)."""
        return self._swipe_consumed

    def cancel_press(self) -> None:
        """Принудительный сброс состояния нажатия при распознанном жесте или свайпе."""
        self._is_pressed = False
        self._swipe_consumed = True
        self.set_state("idle")

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
        Переключение визуального состояния тайла:
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
            self._swipe_consumed = False
            pos = event.position() if hasattr(event, "position") else event.pos()
            self._press_start_pos = QPointF(pos.x(), pos.y())
            self._press_start_time = time.monotonic()
            self.set_state("pressed")
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_pressed and self._press_start_pos is not None:
            pos = event.position() if hasattr(event, "position") else event.pos()
            dx = pos.x() - self._press_start_pos.x()
            if abs(dx) >= self._swipe_threshold_dx:
                self.cancel_press()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            # Если жест был распознан как свайп или превысил порог смещения, клик подавляется
            if self._swipe_consumed:
                self._swipe_consumed = False
                self._is_pressed = False
                self.set_state("idle")
                event.accept()
                return

            if self._is_pressed:
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

    def event(self, event: QEvent) -> bool:
        """
        Перехват тач-событий (QTouchEvent) для кинематического сброса и
        бесконфликтной изоляции от двухпальцевого фильтра TouchCursorFilter.
        """
        etype = event.type()
        if etype in (
            QEvent.Type.TouchBegin,
            QEvent.Type.TouchUpdate,
            QEvent.Type.TouchEnd,
            QEvent.Type.TouchCancel,
        ):
            points = []
            if hasattr(event, "points"):
                points = event.points()
            elif hasattr(event, "touchPoints"):
                points = event.touchPoints()

            # 2 пальца и более -> жест переключения вкладок TouchCursorFilter
            # Кнопка сбрасывается в idle и не блокирует событие
            if len(points) > 1:
                if self._is_pressed:
                    self.cancel_press()
                else:
                    self._swipe_consumed = True
                return False

            if etype == QEvent.Type.TouchBegin and len(points) == 1:
                pt_pos = _extract_point_pos(points[0])
                self._press_start_pos = pt_pos
                self._press_start_time = time.monotonic()
                self._swipe_consumed = False

            elif etype == QEvent.Type.TouchUpdate and len(points) == 1:
                if self._is_pressed and self._press_start_pos is not None:
                    curr = _extract_point_pos(points[0])
                    dx = curr.x() - self._press_start_pos.x()
                    if abs(dx) >= self._swipe_threshold_dx:
                        self.cancel_press()

            elif etype in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
                if self._swipe_consumed:
                    self._is_pressed = False
                    self.set_state("idle")

        return super().event(event)

    def cleanup(self) -> None:
        """Остановка всех активных таймеров виджета."""
        if self._reset_timer.isActive():
            self._reset_timer.stop()
        if self._shake_timer.isActive():
            self._shake_timer.stop()


__all__ = ["DeckButtonWidget"]
