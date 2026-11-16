"""
Модуль сенсорного детектора горизонтального свайпа DuckDeck (DeckSwipeDetector).
Архитектурные инварианты:
  - Кинематический детектор 1-пальцевого горизонтального свайпа:
      * dt <= 600 ms (MAX_DT_MS)
      * |dx| >= 60 px (MIN_DX)
      * |dx| > 1.5 * |dy| (AXIS_RATIO)
  - Сброс состояния кнопки DeckButtonWidget при |dx| >= 20 px (BUTTON_RESET_DX).
  - Бесконфликтная изоляция от глобального 2-пальцевого фильтра TouchCursorFilter:
      * При len(points) > 1 детектор немедленно сбрасывается и возвращает False.
      * Любые 2-пальцевые жесты беспрепятственно передаются в core.touch_filter.TouchCursorFilter.
  - Подавление синтетического клика мыши (mouseReleaseEvent) при распознанном свайпе.
"""
import time
import logging
from typing import Any, Optional

from PySide6.QtCore import Qt, QPointF, Signal, QEvent, QObject
from PySide6.QtGui import QTouchEvent, QEventPoint, QMouseEvent

logger = logging.getLogger("duckdock.deck.swipe_detector")


def _extract_point_pos(pt: Any) -> QPointF:
    """Извлечь координаты точки тача с учетом различий версий Qt и синтетических тестов."""
    if hasattr(pt, "scenePosition") and not pt.scenePosition().isNull():
        return pt.scenePosition()
    if hasattr(pt, "position") and not pt.position().isNull():
        return pt.position()
    if hasattr(pt, "globalPosition") and not pt.globalPosition().isNull():
        return pt.globalPosition()
    if hasattr(pt, "pos") and callable(pt.pos):
        p = pt.pos()
        return QPointF(p.x(), p.y())
    return QPointF(0, 0)


class DeckSwipeDetector(QObject):
    """
    Кинематический детектор 1-пальцевого горизонтального свайпа DuckDeck.
    Пороги:
      - dt <= 600 ms (MAX_DT_MS)
      - |dx| >= 60 px (MIN_DX)
      - |dx| > 1.5 * |dy| (AXIS_RATIO)
      - |dx| >= 20 px (BUTTON_RESET_DX): сброс состояния кнопки
    Изоляция:
      - 2-пальцевые тач-события игнорируются (передаются TouchCursorFilter).
      - При распознавании свайпа выставляется _suppress_mouse_release = True.
    """
    swipe_detected = Signal(str)  # "left" | "right"
    swipe_left = Signal()
    swipe_right = Signal()

    MAX_DT_MS: float = 600.0
    MIN_DX: float = 60.0
    AXIS_RATIO: float = 1.5
    BUTTON_RESET_DX: float = 20.0

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._swipe_active: bool = False
        self._swipe_triggered: bool = False
        self._suppress_mouse_release: bool = False

        self._start_pos: QPointF = QPointF(0, 0)
        self._start_time: float = 0.0

        self._last_direction: Optional[str] = None
        self._last_dx: float = 0.0
        self._last_dy: float = 0.0
        self._last_dt_ms: float = 0.0

        # Эмуляция мыши (для отладки на рабочем столе и десктопных тестов)
        self._mouse_active: bool = False
        self._mouse_start_pos: QPointF = QPointF(0, 0)
        self._mouse_start_time: float = 0.0

    def reset(self) -> None:
        """Сброс состояния детектора."""
        self._swipe_active = False
        self._swipe_triggered = False
        self._mouse_active = False

    @property
    def is_swipe_active(self) -> bool:
        return self._swipe_active

    @property
    def swipe_triggered(self) -> bool:
        return self._swipe_triggered

    @property
    def suppress_mouse_release(self) -> bool:
        return self._suppress_mouse_release

    @property
    def last_direction(self) -> Optional[str]:
        return self._last_direction

    def _reset_watched_button(self, watched: QObject) -> None:
        """Сброс состояния прикрепленного виджета кнопки при сдвиге или жесте."""
        if hasattr(watched, "_swipe_consumed"):
            setattr(watched, "_swipe_consumed", True)
        if hasattr(watched, "_is_pressed"):
            setattr(watched, "_is_pressed", False)
        if hasattr(watched, "set_state"):
            try:
                watched.set_state("idle")
            except Exception:
                pass

    def _trigger_swipe(self, dx: float, watched: Optional[QObject] = None) -> None:
        direction = "left" if dx < 0 else "right"
        self._swipe_triggered = True
        self._suppress_mouse_release = True
        self._last_direction = direction
        if watched is not None:
            self._reset_watched_button(watched)
        logger.debug("Deck horizontal swipe detected: %s (dx=%.1f)", direction, dx)
        self.swipe_detected.emit(direction)
        if direction == "left":
            self.swipe_left.emit()
        else:
            self.swipe_right.emit()

    def process_event(self, watched: QObject, event: QEvent) -> bool:
        """
        Обработка тач- и мышиных событий.
        Возвращает True, если событие поглощено распознанным свайпом.
        """
        etype = event.type()

        # -------------------------------------------------------------
        # А. Обработка тач-событий (QTouchEvent)
        # -------------------------------------------------------------
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

            # Изоляция от глобального TouchCursorFilter: 2 пальца НЕ перехватываем
            if len(points) > 1:
                self.reset()
                self._reset_watched_button(watched)
                return False

            if etype == QEvent.Type.TouchBegin:
                if len(points) == 1:
                    self._swipe_active = True
                    self._swipe_triggered = False
                    self._start_pos = _extract_point_pos(points[0])
                    self._start_time = time.monotonic()
                return False

            elif etype == QEvent.Type.TouchUpdate:
                if not self._swipe_active:
                    return False

                if len(points) != 1:
                    self.reset()
                    self._reset_watched_button(watched)
                    return False

                curr_pos = _extract_point_pos(points[0])
                dt_ms = (time.monotonic() - self._start_time) * 1000.0
                dx = curr_pos.x() - self._start_pos.x()
                dy = curr_pos.y() - self._start_pos.y()
                self._last_dx = dx
                self._last_dy = dy
                self._last_dt_ms = dt_ms

                # Сброс кнопки при горизонтальном сдвиге |dx| >= 20 px
                if abs(dx) >= self.BUTTON_RESET_DX:
                    self._reset_watched_button(watched)

                # Проверка окна жеста
                if dt_ms > self.MAX_DT_MS:
                    self._swipe_active = False
                    return False

                if not self._swipe_triggered:
                    # Пороги: |dx| >= 60 px и |dx| > 1.5 * |dy|
                    if abs(dx) >= self.MIN_DX and abs(dx) > self.AXIS_RATIO * abs(dy):
                        self._trigger_swipe(dx, watched)
                        return True

                if self._swipe_triggered:
                    return True
                return False

            elif etype == QEvent.Type.TouchEnd:
                consumed = False
                if self._swipe_active:
                    if not self._swipe_triggered and len(points) == 1:
                        curr_pos = _extract_point_pos(points[0])
                        dt_ms = (time.monotonic() - self._start_time) * 1000.0
                        dx = curr_pos.x() - self._start_pos.x()
                        dy = curr_pos.y() - self._start_pos.y()
                        self._last_dx = dx
                        self._last_dy = dy
                        self._last_dt_ms = dt_ms

                        if (
                            dt_ms <= self.MAX_DT_MS
                            and abs(dx) >= self.MIN_DX
                            and abs(dx) > self.AXIS_RATIO * abs(dy)
                        ):
                            self._trigger_swipe(dx, watched)
                            consumed = True

                    if self._swipe_triggered:
                        consumed = True

                    self._swipe_active = False
                    self._swipe_triggered = False

                if consumed:
                    return True
                return False

            elif etype == QEvent.Type.TouchCancel:
                self.reset()
                self._reset_watched_button(watched)
                return False

        # -------------------------------------------------------------
        # Б. Обработка мышиных событий (эмуляция и подавление клика)
        # -------------------------------------------------------------
        if etype == QEvent.Type.MouseButtonRelease:
            if self._suppress_mouse_release:
                self._suppress_mouse_release = False
                self._reset_watched_button(watched)
                return True

            if self._mouse_active and not self._swipe_triggered:
                curr_pos = event.position() if hasattr(event, "position") else event.pos()
                dt_ms = (time.monotonic() - self._mouse_start_time) * 1000.0
                dx = curr_pos.x() - self._mouse_start_pos.x()
                dy = curr_pos.y() - self._mouse_start_pos.y()
                self._mouse_active = False
                if (
                    dt_ms <= self.MAX_DT_MS
                    and abs(dx) >= self.MIN_DX
                    and abs(dx) > self.AXIS_RATIO * abs(dy)
                ):
                    self._trigger_swipe(dx, watched)
                    return True
            self._mouse_active = False
            return False

        elif etype == QEvent.Type.MouseButtonPress:
            if hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton:
                self._mouse_active = True
                self._swipe_triggered = False
                self._mouse_start_time = time.monotonic()
                pos = event.position() if hasattr(event, "position") else event.pos()
                self._mouse_start_pos = QPointF(pos.x(), pos.y())
            return False

        elif etype == QEvent.Type.MouseMove:
            if self._mouse_active and not self._swipe_triggered:
                curr_pos = event.position() if hasattr(event, "position") else event.pos()
                dt_ms = (time.monotonic() - self._mouse_start_time) * 1000.0
                dx = curr_pos.x() - self._mouse_start_pos.x()
                dy = curr_pos.y() - self._mouse_start_pos.y()

                # Сброс кнопки при горизонтальном сдвиге |dx| >= 20 px
                if abs(dx) >= self.BUTTON_RESET_DX:
                    self._reset_watched_button(watched)

                if dt_ms > self.MAX_DT_MS:
                    self._mouse_active = False
                    return False
                if abs(dx) >= self.MIN_DX and abs(dx) > self.AXIS_RATIO * abs(dy):
                    self._trigger_swipe(dx, watched)
                    return True
            if self._swipe_triggered:
                return True
            return False

        return False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        return self.process_event(watched, event)


__all__ = ["DeckSwipeDetector", "_extract_point_pos"]
