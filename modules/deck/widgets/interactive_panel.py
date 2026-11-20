"""
Интерактивная сенсорная панель DuckDeck (DeckInteractivePanel).
Габариты: 920x216 px (Нижняя строка DuckDeck v0.4.0).
Архитектурные инварианты:
  - Наследование от TouchModuleView (Qt.NoFocus на всех элементах).
  - 3 горизонтальные секции: Левая (280x216), Центральная (360x216), Правая (280x216).
  - Центральная зона: сенсорный трек 1-пальцевого горизонтального свайпа:
      * dt <= 600 ms
      * |dx| >= 60 px
      * |dx| > 1.5 * |dy|
  - Бесконфликтная изоляция от глобального 2-пальцевого фильтра TouchCursorFilter.
  - Подавление синтетического клика мыши после успешного свайпа.
"""
import time
import logging
from typing import Any, Optional

from PySide6.QtCore import (
    Qt,
    QPointF,
    QTimer,
    Signal,
    QEvent,
    QObject,
    QDate,
    QTime,
    QLocale,
    QVariantAnimation,
    QEasingCurve,
)
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtGui import (
    QTouchEvent,
    QEventPoint,
    QFont,
    QColor,
    QPainter,
    QBrush,
    QPen,
    QMouseEvent,
    QLinearGradient,
)

from core.event_bus import bus
from core.i18n import t, I18nManager
from core.ui_base import TouchModuleView
from ui.widgets.marquee_label import MarqueeLabel
from modules.deck.widgets.swipe_detector import DeckSwipeDetector, _extract_point_pos

logger = logging.getLogger("duckdock.deck.interactive_panel")



# =============================================================================
# 2. Виджет точечной пагинации (DotPagingWidget)
# =============================================================================
class DotPagingWidget(QWidget):
    """
    Сенсорный индикатор страниц (● ○ ○).
    Точки 14 px, отступы 8 px, активная #38bdf8, неактивная #334155.
    Инвариант: Qt.NoFocus.
    Поддерживает:
      - Плавную кинетическую анимацию перемещения активной точки (QVariantAnimation, 220 мс).
      - Капсульный контур (Swipe Track Pill) с направляющими шевронами ‹ и ›.
      - Неоновый световой импульс шевронов при свайпе (flash_chevron).
    """
    page_selected = Signal(int)

    def __init__(
        self,
        page_count: int = 3,
        current_page: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)
        self._page_count = max(1, page_count)
        self._current_page = current_page
        self._page_ids: list[str] = []
        self._dot_size = 14
        self._dot_spacing = 8
        self._anim_pos = float(current_page)
        self.setFixedHeight(28)
        self.setMinimumWidth(self._calculate_width())

        # Анимация перемещения активной точки
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_step)

        # Световой отклик шевронов при свайпе (0.0 .. 1.0)
        self._left_glow: float = 0.0
        self._right_glow: float = 0.0

        self._chevron_anim_left = QVariantAnimation(self)
        self._chevron_anim_left.setDuration(300)
        self._chevron_anim_left.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._chevron_anim_left.valueChanged.connect(self._on_left_glow_step)

        self._chevron_anim_right = QVariantAnimation(self)
        self._chevron_anim_right.setDuration(300)
        self._chevron_anim_right.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._chevron_anim_right.valueChanged.connect(self._on_right_glow_step)

    def _on_anim_step(self, value: Any) -> None:
        self._anim_pos = float(value)
        self.update()

    def _on_left_glow_step(self, val: Any) -> None:
        self._left_glow = float(val)
        self.update()

    def _on_right_glow_step(self, val: Any) -> None:
        self._right_glow = float(val)
        self.update()

    def flash_chevron(self, direction: str) -> None:
        """Вспышка направляющего шеврона при свайпе."""
        if direction in ("left", "next"):
            # Свайп влево ведет на следующую страницу (правый шеврон ›)
            if self._chevron_anim_right.state() == QVariantAnimation.State.Running:
                self._chevron_anim_right.stop()
            self._chevron_anim_right.setStartValue(1.0)
            self._chevron_anim_right.setEndValue(0.0)
            self._chevron_anim_right.start()
        elif direction in ("right", "prev"):
            # Свайп вправо ведет на предыдущую страницу (левый шеврон ‹)
            if self._chevron_anim_left.state() == QVariantAnimation.State.Running:
                self._chevron_anim_left.stop()
            self._chevron_anim_left.setStartValue(1.0)
            self._chevron_anim_left.setEndValue(0.0)
            self._chevron_anim_left.start()

    def _calculate_width(self) -> int:
        total_dots = self._page_count * self._dot_size + (self._page_count - 1) * self._dot_spacing
        return total_dots + 64

    def set_page_count(self, count: int) -> None:
        self._page_count = max(1, count)
        if self._current_page >= self._page_count:
            self._current_page = self._page_count - 1
            self._anim_pos = float(self._current_page)
        self.setMinimumWidth(self._calculate_width())
        self.update()

    def set_page_ids(self, page_ids: list[str]) -> None:
        """Регистрация идентификаторов страниц профиля."""
        self._page_ids = list(page_ids)
        self.set_page_count(len(page_ids))

    def set_current_page(self, index: int, animated: bool = True) -> None:
        if 0 <= index < self._page_count:
            old_page = self._current_page
            self._current_page = index
            if animated and old_page != index:
                if self._anim.state() == QVariantAnimation.State.Running:
                    self._anim.stop()
                self._anim.setStartValue(self._anim_pos)
                self._anim.setEndValue(float(index))
                self._anim.start()
            else:
                if self._anim.state() == QVariantAnimation.State.Running:
                    self._anim.stop()
                self._anim_pos = float(index)
                self.update()

    def current_page(self) -> int:
        return self._current_page

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        total_dots_width = self._page_count * self._dot_size + (self._page_count - 1) * self._dot_spacing
        start_x = (self.width() - total_dots_width) // 2
        center_y = self.height() // 2

        # 1. Фоновая капсула (Pill Container)
        pill_pad_x = 22
        pill_left = start_x - pill_pad_x
        pill_width = total_dots_width + pill_pad_x * 2
        pill_height = 24
        pill_top = center_y - pill_height // 2

        max_glow = max(self._left_glow, self._right_glow)
        if max_glow > 0.05:
            r = int(35 + (56 - 35) * max_glow)
            g = int(43 + (189 - 43) * max_glow)
            b = int(62 + (248 - 62) * max_glow)
            border_pen = QPen(QColor(r, g, b), 1)
        else:
            border_pen = QPen(QColor("#232b3e"), 1)

        painter.setBrush(QBrush(QColor("#161b26")))
        painter.setPen(border_pen)
        painter.drawRoundedRect(pill_left, pill_top, pill_width, pill_height, 12, 12)

        # 2. Шевроны по краям капсулы (‹ и ›)
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)

        # Левый шеврон ‹
        if self._left_glow > 0.05:
            lr = int(71 + (56 - 71) * self._left_glow)
            lg = int(85 + (189 - 85) * self._left_glow)
            lb = int(105 + (248 - 105) * self._left_glow)
            painter.setPen(QColor(lr, lg, lb))
        else:
            painter.setPen(QColor("#475569"))
        painter.drawText(pill_left + 7, center_y + 4, "‹")

        # Правый шеврон ›
        if self._right_glow > 0.05:
            rr = int(71 + (56 - 71) * self._right_glow)
            rg = int(85 + (189 - 85) * self._right_glow)
            rb = int(105 + (248 - 105) * self._right_glow)
            painter.setPen(QColor(rr, rg, rb))
        else:
            painter.setPen(QColor("#475569"))
        painter.drawText(pill_left + pill_width - 14, center_y + 4, "›")

        # 3. Фоновые неактивные точки (10 px, центрирование в слоте 14 px)
        inactive_color = QColor("#334155")
        for i in range(self._page_count):
            x = start_x + i * (self._dot_size + self._dot_spacing)
            y = center_y - self._dot_size // 2
            painter.setBrush(QBrush(inactive_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x + 2, y + 2, self._dot_size - 4, self._dot_size - 4)

        # 4. Скользящая активная точка (14 px)
        active_color = QColor("#38bdf8")
        active_x = start_x + self._anim_pos * (self._dot_size + self._dot_spacing)
        active_y = center_y - self._dot_size // 2
        painter.setBrush(QBrush(active_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(round(active_x)), int(round(active_y)), self._dot_size, self._dot_size)

        painter.end()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        total_dots_width = self._page_count * self._dot_size + (self._page_count - 1) * self._dot_spacing
        start_x = (self.width() - total_dots_width) // 2
        click_x = event.position().x() if hasattr(event, "position") else event.x()

        # Клик по левому шеврону ‹ (prev)
        if click_x < start_x - 4 and self._current_page > 0:
            self.set_current_page(self._current_page - 1, animated=True)
            self.flash_chevron("right")
            self.page_selected.emit(self._current_page)
            page_id = self._page_ids[self._current_page] if (self._page_ids and self._current_page < len(self._page_ids)) else f"page_{self._current_page}"
            bus.deck_page_changed.emit(page_id)
            return

        # Клик по правому шеврону › (next)
        if click_x > start_x + total_dots_width + 4 and self._current_page < self._page_count - 1:
            self.set_current_page(self._current_page + 1, animated=True)
            self.flash_chevron("left")
            self.page_selected.emit(self._current_page)
            page_id = self._page_ids[self._current_page] if (self._page_ids and self._current_page < len(self._page_ids)) else f"page_{self._current_page}"
            bus.deck_page_changed.emit(page_id)
            return

        # Клик по конкретной точке
        for i in range(self._page_count):
            dot_left = start_x + i * (self._dot_size + self._dot_spacing) - 4
            dot_right = dot_left + self._dot_size + 8
            if dot_left <= click_x <= dot_right:
                self.set_current_page(i, animated=True)
                self.page_selected.emit(i)
                page_id = self._page_ids[i] if (self._page_ids and i < len(self._page_ids)) else f"page_{i}"
                bus.deck_page_changed.emit(page_id)
                break

    def cleanup(self) -> None:
        """Остановка анимаций при уничтожении виджета."""
        if hasattr(self, "_anim") and self._anim.state() == QVariantAnimation.State.Running:
            self._anim.stop()
        if hasattr(self, "_chevron_anim_left") and self._chevron_anim_left.state() == QVariantAnimation.State.Running:
            self._chevron_anim_left.stop()
        if hasattr(self, "_chevron_anim_right") and self._chevron_anim_right.state() == QVariantAnimation.State.Running:
            self._chevron_anim_right.stop()


# =============================================================================
# 3. Центральная секция: Время, пагинация и трек свайпа (DeckCenterSection)
# =============================================================================
class DeckCenterSection(QFrame):
    """
    Центральная секция DeckInteractivePanel (360x216 px).
    Включает:
      - Часы HH:mm (34 px Bold #38bdf8) и дату (11 px #64748b).
      - Виджет пагинации DotPagingWidget (● ○ ○).
      - Сенсорную зону 1-пальцевого горизонтального свайпа.
    Инвариант: Qt.NoFocus.
    """
    swipe_detected = Signal(str)  # "left" | "right"
    swipe_left = Signal()
    swipe_right = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DeckCenterSection")
        self.setFixedSize(360, 216)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)

        # Световая волна при свайпе
        self._swipe_glow_opacity: float = 0.0
        self._swipe_glow_dir: str = "left"

        self._swipe_anim = QVariantAnimation(self)
        self._swipe_anim.setDuration(350)
        self._swipe_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._swipe_anim.valueChanged.connect(self._on_swipe_glow_step)

        # Детектор свайпа
        self.swipe_detector = DeckSwipeDetector(self)
        self.swipe_detector.swipe_detected.connect(self.swipe_detected)
        self.swipe_detector.swipe_left.connect(self.swipe_left)
        self.swipe_detector.swipe_right.connect(self.swipe_right)

        # Синхронная визуальная реакция на жесты свайпа
        self.swipe_detector.swipe_left.connect(lambda: self.trigger_swipe_feedback("left"))
        self.swipe_detector.swipe_right.connect(lambda: self.trigger_swipe_feedback("right"))

        # Перехват событий на секции и дочерних элементах
        self.installEventFilter(self.swipe_detector)

        self._init_ui()
        self._init_clock()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Часы HH:mm
        self.lbl_clock = QLabel("00:00", self)
        self.lbl_clock.setObjectName("DeckClockLabel")
        self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_clock.setFocusPolicy(Qt.NoFocus)
        self.lbl_clock.setStyleSheet(
            "color: #38bdf8; font-size: 34px; font-weight: bold; font-family: 'Segoe UI', sans-serif;"
        )
        self.lbl_clock.installEventFilter(self.swipe_detector)
        layout.addWidget(self.lbl_clock)

        # 2. Дата
        self.lbl_date = QLabel("", self)
        self.lbl_date.setObjectName("DeckDateLabel")
        self.lbl_date.setAlignment(Qt.AlignCenter)
        self.lbl_date.setFocusPolicy(Qt.NoFocus)
        self.lbl_date.setStyleSheet("color: #64748b; font-size: 11px;")
        self.lbl_date.installEventFilter(self.swipe_detector)
        layout.addWidget(self.lbl_date)

        # Распорка перед пагинацией
        layout.addSpacing(6)

        # 3. Виджет пагинации
        self.dots = DotPagingWidget(page_count=3, current_page=0, parent=self)
        self.dots.setObjectName("DeckDotPaging")
        layout.addWidget(self.dots, 0, Qt.AlignHCenter)

    def _init_clock(self) -> None:
        self._update_time()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_time)
        self._timer.start()

    def _update_time(self) -> None:
        now = QTime.currentTime()
        self.lbl_clock.setText(now.toString("HH:mm"))
        today = QDate.currentDate()
        months = t("common.calendar.months")
        days = t("common.calendar.days")
        if isinstance(months, list) and isinstance(days, list):
            m_idx = today.month() - 1
            d_idx = today.dayOfWeek() - 1
            month_str = months[m_idx] if 0 <= m_idx < len(months) else ""
            day_str = days[d_idx] if 0 <= d_idx < len(days) else ""
            self.lbl_date.setText(f"{today.day()} {month_str}, {day_str}")
        else:
            lang = I18nManager().get_language()
            qloc = QLocale(QLocale.Language.Russian if lang == "ru" else QLocale.Language.English)
            self.lbl_date.setText(qloc.toString(today, "d MMM, ddd"))

    def retranslate_ui(self) -> None:
        """Обновление даты при смене языка."""
        self._update_time()

    def _on_swipe_glow_step(self, val: Any) -> None:
        self._swipe_glow_opacity = float(val)
        self.update()

    def trigger_swipe_feedback(self, direction: str) -> None:
        """Запуск визуальной волны свайпа и вспышки шеврона пагинации."""
        self._swipe_glow_dir = direction
        self.dots.flash_chevron(direction)
        if self._swipe_anim.state() == QVariantAnimation.State.Running:
            self._swipe_anim.stop()
        self._swipe_anim.setStartValue(1.0)
        self._swipe_anim.setEndValue(0.0)
        self._swipe_anim.start()

    def paintEvent(self, event: Any) -> None:
        super().paintEvent(event)
        if self._swipe_glow_opacity > 0.01:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            w = self.width()
            h = self.height()
            if self._swipe_glow_dir == "left":
                grad = QLinearGradient(w, 0, 0, 0)
            else:
                grad = QLinearGradient(0, 0, w, 0)
            alpha = int(35 * self._swipe_glow_opacity)
            grad.setColorAt(0.0, QColor(56, 189, 248, alpha))
            grad.setColorAt(0.5, QColor(56, 189, 248, int(alpha * 0.3)))
            grad.setColorAt(1.0, QColor(56, 189, 248, 0))
            painter.fillRect(0, 0, w, h, QBrush(grad))
            painter.end()

    def set_page_count(self, count: int) -> None:
        self.dots.set_page_count(count)

    def set_page_ids(self, page_ids: list[str]) -> None:
        self.dots.set_page_ids(page_ids)

    def set_current_page(self, index: int, animated: bool = True) -> None:
        self.dots.set_current_page(index, animated=animated)

    def get_current_page(self) -> int:
        return self.dots.current_page()

    def cleanup(self) -> None:
        """Остановка таймеров секции и анимаций."""
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        if hasattr(self, "_swipe_anim") and self._swipe_anim.state() == QVariantAnimation.State.Running:
            self._swipe_anim.stop()
        if hasattr(self, "dots") and hasattr(self.dots, "cleanup"):
            self.dots.cleanup()


# =============================================================================
# 4. Левая секция: Мультимедийный пульт (DeckLeftSection)
# =============================================================================
class DeckLeftSection(QFrame):
    """
    Левая секция DeckInteractivePanel (280x216 px).
    Медиа-пульт: обложка 48x48, бегущая строка MarqueeLabel, подпись, кнопки ⏮ ⏯ ⏭.
    Инвариант: Qt.NoFocus.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DeckLeftSection")
        self.setFixedSize(280, 216)
        self.setFocusPolicy(Qt.NoFocus)

        self._is_playing = False
        self._eventbus_connected = False

        self._init_ui()
        self._subscribe_eventbus()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Верхняя информационная зона
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)

        # Обложка / иконка 48x48
        self.lbl_cover = QLabel("🎵", self)
        self.lbl_cover.setFixedSize(48, 48)
        self.lbl_cover.setAlignment(Qt.AlignCenter)
        self.lbl_cover.setFocusPolicy(Qt.NoFocus)
        self.lbl_cover.setStyleSheet(
            "background-color: #161b26; border: 1px solid #232b3e; border-radius: 8px; font-size: 20px;"
        )
        info_layout.addWidget(self.lbl_cover)

        # Текстовый блок (трек + артист)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignVCenter)

        self.lbl_title = MarqueeLabel(t("deck.interactive.media_default"), self)
        self.lbl_title.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: bold;")
        text_layout.addWidget(self.lbl_title)

        self.lbl_artist = QLabel(t("deck.interactive.media_waiting"), self)
        self.lbl_artist.setFocusPolicy(Qt.NoFocus)
        self.lbl_artist.setStyleSheet("color: #94a3b8; font-size: 11px;")
        text_layout.addWidget(self.lbl_artist)

        info_layout.addLayout(text_layout)
        layout.addLayout(info_layout)

        # Органы управления (⏮ ⏯ ⏭)
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)
        ctrl_layout.setAlignment(Qt.AlignCenter)

        btn_style = """
            QPushButton {
                background-color: #161b26;
                color: #e2e8f0;
                border: 1px solid #232b3e;
                border-radius: 10px;
                font-size: 16px;
            }
            QPushButton:pressed {
                background-color: #10141d;
                border-color: #38bdf8;
            }
        """

        self.btn_prev = QPushButton("⏮", self)
        self.btn_prev.setFixedSize(44, 44)
        self.btn_prev.setFocusPolicy(Qt.NoFocus)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(lambda: bus.media_action_requested.emit("prev"))
        ctrl_layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton("⏯", self)
        self.btn_play.setFixedSize(44, 44)
        self.btn_play.setFocusPolicy(Qt.NoFocus)
        self.btn_play.setStyleSheet(btn_style)
        self.btn_play.clicked.connect(lambda: bus.media_action_requested.emit("toggle_play"))
        ctrl_layout.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭", self)
        self.btn_next.setFixedSize(44, 44)
        self.btn_next.setFocusPolicy(Qt.NoFocus)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(lambda: bus.media_action_requested.emit("next"))
        ctrl_layout.addWidget(self.btn_next)

        layout.addLayout(ctrl_layout)

    def _subscribe_eventbus(self) -> None:
        if not self._eventbus_connected:
            bus.media_state_changed.connect(self._on_media_state_changed)
            self._eventbus_connected = True

    def _unsubscribe_eventbus(self) -> None:
        if self._eventbus_connected:
            try:
                bus.media_state_changed.disconnect(self._on_media_state_changed)
            except Exception:
                pass
            self._eventbus_connected = False

    def _on_media_state_changed(self, state: dict) -> None:
        title = state.get("title", "")
        artist = state.get("artist", "")
        self._is_playing = bool(state.get("is_playing", False))

        if title:
            self.lbl_title.set_track_text(title)
        if artist:
            self.lbl_artist.setText(artist)

        self.btn_play.setText("⏸" if self._is_playing else "▶")

    def retranslate_ui(self) -> None:
        """Обновление текстовых меток при отсутствии активного трека."""
        if not self._is_playing:
            self.lbl_artist.setText(t("deck.interactive.media_waiting"))
            if not self.lbl_title.text() or self.lbl_title.text() in ("YouTube Music", "YouTube", ""):
                self.lbl_title.setText(t("deck.interactive.media_default"))

    def cleanup(self) -> None:
        """Очистка ресурсов и отписка от EventBus."""
        self._unsubscribe_eventbus()
        if hasattr(self.lbl_title, "_timer") and self.lbl_title._timer.isActive():
            self.lbl_title._timer.stop()


# =============================================================================
# 5. Правая секция: Телеметрия, тикер и настройки (DeckRightSection)
# =============================================================================
class DeckRightSection(QFrame):
    """
    Правая секция DeckInteractivePanel (280x216 px).
    Включает:
      - Бейджи датчиков CPU/GPU.
      - NotificationTicker сообщений.
      - Сенсорную кнопку шестеренки ⚙.
    Инвариант: Qt.NoFocus.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DeckRightSection")
        self.setFixedSize(280, 216)
        self.setFocusPolicy(Qt.NoFocus)

        self._eventbus_connected = False
        self._init_ui()
        self._subscribe_eventbus()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Верхняя строка: Датчики и Шестеренка
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        # Бейджи датчиков
        sensors_layout = QVBoxLayout()
        sensors_layout.setSpacing(4)

        self.lbl_cpu = QLabel("CPU: --°C", self)
        self.lbl_cpu.setFocusPolicy(Qt.NoFocus)
        self.lbl_cpu.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
        sensors_layout.addWidget(self.lbl_cpu)

        self.lbl_gpu = QLabel("GPU: --°C", self)
        self.lbl_gpu.setFocusPolicy(Qt.NoFocus)
        self.lbl_gpu.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
        sensors_layout.addWidget(self.lbl_gpu)

        top_layout.addLayout(sensors_layout)
        top_layout.addStretch()

        # Кнопка настроек ⚙
        self.btn_settings = QPushButton("⚙", self)
        self.btn_settings.setFixedSize(44, 44)
        self.btn_settings.setFocusPolicy(Qt.NoFocus)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: #161b26;
                color: #94a3b8;
                border: 1px solid #232b3e;
                border-radius: 10px;
                font-size: 18px;
            }
            QPushButton:pressed {
                background-color: #10141d;
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        self.btn_settings.clicked.connect(self._on_settings_clicked)
        top_layout.addWidget(self.btn_settings)

        layout.addLayout(top_layout)

        # Нижняя зона: NotificationTicker
        layout.addStretch()

        self.lbl_ticker = QLabel(t("deck.interactive.ready"), self)
        self.lbl_ticker.setObjectName("DeckNotificationTicker")
        self.lbl_ticker.setFocusPolicy(Qt.NoFocus)
        self.lbl_ticker.setAlignment(Qt.AlignCenter)
        self.lbl_ticker.setStyleSheet(
            "background-color: #161b26; color: #94a3b8; border: 1px solid #232b3e; "
            "border-radius: 8px; padding: 6px; font-size: 11px;"
        )
        layout.addWidget(self.lbl_ticker)

        # Таймер сброса уведомлений (3 секунды)
        self._ticker_timer = QTimer(self)
        self._ticker_timer.setSingleShot(True)
        self._ticker_timer.setInterval(3000)
        self._ticker_timer.timeout.connect(self._reset_ticker)

    def _on_settings_clicked(self) -> None:
        self.show_notification(t("deck.interactive.settings_in_dev"))

    def _subscribe_eventbus(self) -> None:
        if not self._eventbus_connected:
            bus.sensors_updated.connect(self._on_sensors_updated)
            bus.deck_notification.connect(self.show_notification)
            self._eventbus_connected = True

    def _unsubscribe_eventbus(self) -> None:
        if self._eventbus_connected:
            try:
                bus.sensors_updated.disconnect(self._on_sensors_updated)
            except Exception:
                pass
            try:
                bus.deck_notification.disconnect(self.show_notification)
            except Exception:
                pass
            self._eventbus_connected = False

    def _on_sensors_updated(self, data: dict) -> None:
        cpu_temp = data.get("cpu_temp")
        gpu_temp = data.get("gpu_temp")

        if cpu_temp is not None:
            color = "#ef4444" if cpu_temp > 75 else ("#f59e0b" if cpu_temp > 65 else "#10b981")
            self.lbl_cpu.setText(f"CPU: {cpu_temp:.0f}°C")
            self.lbl_cpu.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")

        if gpu_temp is not None:
            color = "#ef4444" if gpu_temp > 75 else ("#f59e0b" if gpu_temp > 65 else "#10b981")
            self.lbl_gpu.setText(f"GPU: {gpu_temp:.0f}°C")
            self.lbl_gpu.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")

    def show_notification(self, message: str) -> None:
        self.lbl_ticker.setText(message)
        self.lbl_ticker.setStyleSheet(
            "background-color: #1a2234; color: #38bdf8; border: 1px solid #38bdf8; "
            "border-radius: 8px; padding: 6px; font-size: 11px; font-weight: 600;"
        )
        self._ticker_timer.start()

    def _reset_ticker(self) -> None:
        self.lbl_ticker.setText(t("deck.interactive.ready"))
        self.lbl_ticker.setStyleSheet(
            "background-color: #161b26; color: #94a3b8; border: 1px solid #232b3e; "
            "border-radius: 8px; padding: 6px; font-size: 11px;"
        )

    def retranslate_ui(self) -> None:
        """Обновление тикера при смене языка, если нет активного уведомления."""
        if not self._ticker_timer.isActive():
            self.lbl_ticker.setText(t("deck.interactive.ready"))

    def cleanup(self) -> None:
        """Очистка таймеров и отписка от EventBus."""
        self._unsubscribe_eventbus()
        if hasattr(self, "_ticker_timer") and self._ticker_timer.isActive():
            self._ticker_timer.stop()


# =============================================================================
# 6. Главная составная панель: DeckInteractivePanel
# =============================================================================
class DeckInteractivePanel(TouchModuleView):
    """
    Интерактивная сенсорная панель DuckDeck (920x216 px).
    Архитектурный инвариант:
      - TouchModuleView (Qt.NoFocus).
      - Объединяет 3 секции: Левая (280 px), Центральная (360 px), Правая (280 px).
      - Проксирует сигналы свайпа из центральной зоны.
    """
    swipe_detected = Signal(str)  # "left" | "right"
    swipe_left = Signal()
    swipe_right = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DeckInteractivePanel")
        self.setFixedSize(920, 216)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._init_layout()
        self._connect_signals()

    def _init_layout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Левая секция: Медиа (280 px)
        self.left_section = DeckLeftSection(self)
        layout.addWidget(self.left_section)

        # 2. Центральная секция: Время, пагинация и свайп (360 px)
        self.center_section = DeckCenterSection(self)
        layout.addWidget(self.center_section)

        # 3. Правая секция: Телеметрия и настройки (280 px)
        self.right_section = DeckRightSection(self)
        layout.addWidget(self.right_section)

    def _connect_signals(self) -> None:
        self.center_section.swipe_detected.connect(self.swipe_detected)
        self.center_section.swipe_left.connect(self.swipe_left)
        self.center_section.swipe_right.connect(self.swipe_right)

    def trigger_swipe_feedback(self, direction: str) -> None:
        """Визуальный отклик свайпа в центральной секции."""
        self.center_section.trigger_swipe_feedback(direction)

    def set_page_count(self, count: int) -> None:
        self.center_section.set_page_count(count)

    def set_page_ids(self, page_ids: list[str]) -> None:
        self.center_section.set_page_ids(page_ids)

    def set_current_page(self, index: int, animated: bool = True) -> None:
        self.center_section.set_current_page(index, animated=animated)

    def get_current_page(self) -> int:
        return self.center_section.get_current_page()

    def retranslate_ui(self) -> None:
        """Каскадная ретрансляция всех трех секций."""
        if hasattr(self, "left_section"):
            self.left_section.retranslate_ui()
        if hasattr(self, "center_section"):
            self.center_section.retranslate_ui()
        if hasattr(self, "right_section"):
            self.right_section.retranslate_ui()

    def cleanup(self) -> None:
        """Каскадная очистка всех секций интерактивной панели."""
        self.left_section.cleanup()
        self.center_section.cleanup()
        self.right_section.cleanup()


__all__ = [
    "DeckSwipeDetector",
    "DotPagingWidget",
    "DeckCenterSection",
    "DeckLeftSection",
    "DeckRightSection",
    "DeckInteractivePanel",
]
