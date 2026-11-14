"""
Модуль «Touch Filter & Swipe Gesture Engine».
Перехватывает тач-события сенсорного экрана, восстанавливает позицию курсора мыши
на основном мониторе (Anti-Cursor Warp) и распознает двухпальцевый вертикальный свайп
(len(points) == 2, |avg_dy| >= 70px, dt <= 500ms, dy0 * dy1 > 0):
- свайп вверх -> следующий экран (+1)
- свайп вниз -> предыдущий (-1).
Касания одним пальцем передаются элементам интерфейса без перехвата.
"""
import time
from typing import Optional, List
from PySide6.QtCore import QObject, QEvent, QTimer, QPointF
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QTouchEvent, QEventPoint

from core.event_bus import bus
from core.focus_guardian import FocusGuardian


def _extract_point_pos(pt: QEventPoint) -> QPointF:
    """Извлечь координаты точки тача с учетом версий Qt и синтетических тестов."""
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


class TouchCursorFilter(QObject):
    """
    Глобальный фильтр событий Qt для перехвата тач-ввода,
    восстановления позиции курсора и распознавания жестов управления.
    """

    def __init__(
        self,
        guardian: Optional[FocusGuardian] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.guardian = guardian
        self._touch_active = False
        self._current_tab = 0

        # Двухпальцевый вертикальный свайп (переключение экранов вверх-вниз)
        self._two_finger_active = False
        self._two_finger_start_time = 0.0
        self._two_finger_start_positions: List[QPointF] = []
        self._two_finger_swipe_triggered = False

        # Подавление клика после успешного жеста
        self._suppress_mouse_release = False

    def _switch_tab(self, offset: int):
        """Переключение активной вкладки с шагом offset (+1 или -1)."""
        total = 5
        parent_obj = self.parent()
        if parent_obj and hasattr(parent_obj, "workspace"):
            try:
                cnt = parent_obj.workspace.count()
                if cnt > 0:
                    total = cnt
                self._current_tab = parent_obj.workspace.currentIndex()
            except Exception:
                total = 5

        new_tab = (self._current_tab + offset) % total
        self._current_tab = new_tab
        bus.tab_changed.emit(new_tab)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        etype = event.type()

        # 1. Обработка тач-событий (QTouchEvent)
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

            if etype in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate):
                self._touch_active = True

            # Начало касания
            if etype == QEvent.Type.TouchBegin:
                if len(points) == 2:
                    self._two_finger_active = True
                    self._two_finger_start_time = time.monotonic()
                    self._two_finger_start_positions = [
                        _extract_point_pos(points[0]),
                        _extract_point_pos(points[1]),
                    ]
                    self._two_finger_swipe_triggered = False

            # Движение пальцев
            elif etype == QEvent.Type.TouchUpdate:
                # 2 пальца: вертикальный свайп для переключения экранов (вверх +1, вниз -1)
                if len(points) == 2:
                    if not self._two_finger_active:
                        self._two_finger_active = True
                        self._two_finger_start_time = time.monotonic()
                        self._two_finger_start_positions = [
                            _extract_point_pos(points[0]),
                            _extract_point_pos(points[1]),
                        ]
                        self._two_finger_swipe_triggered = False
                    elif len(self._two_finger_start_positions) == 2:
                        now = time.monotonic()
                        dt_ms = (now - self._two_finger_start_time) * 1000.0
                        p0 = _extract_point_pos(points[0])
                        p1 = _extract_point_pos(points[1])
                        dx0 = p0.x() - self._two_finger_start_positions[0].x()
                        dx1 = p1.x() - self._two_finger_start_positions[1].x()
                        dy0 = p0.y() - self._two_finger_start_positions[0].y()
                        dy1 = p1.y() - self._two_finger_start_positions[1].y()
                        avg_dx = (dx0 + dx1) / 2.0
                        avg_dy = (dy0 + dy1) / 2.0

                        if not self._two_finger_swipe_triggered:
                            # Проверка тайминга, сонаправленности по вертикали и блокировка щипка/зума
                            if (
                                dt_ms <= 500.0
                                and (dy0 * dy1 > 0)
                                and (abs(avg_dy) > 1.3 * abs(avg_dx))
                            ):
                                if avg_dy <= -70.0:  # Свайп вверх (снизу вверх) -> следующий экран (+1)
                                    self._two_finger_swipe_triggered = True
                                    self._suppress_mouse_release = True
                                    self._switch_tab(1)
                                    return True
                                elif avg_dy >= 70.0:  # Свайп вниз (сверху вниз) -> предыдущий экран (-1)
                                    self._two_finger_swipe_triggered = True
                                    self._suppress_mouse_release = True
                                    self._switch_tab(-1)
                                    return True

                        if self._two_finger_swipe_triggered:
                            return True

            # Завершение тача
            elif etype in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
                consumed = False
                now = time.monotonic()

                # Проверка 2 пальцев при отрыве, если жест не сработал на Update
                if (
                    len(points) == 2
                    and self._two_finger_active
                    and len(self._two_finger_start_positions) == 2
                ):
                    dt_ms = (now - self._two_finger_start_time) * 1000.0
                    p0 = _extract_point_pos(points[0])
                    p1 = _extract_point_pos(points[1])
                    dx0 = p0.x() - self._two_finger_start_positions[0].x()
                    dx1 = p1.x() - self._two_finger_start_positions[1].x()
                    dy0 = p0.y() - self._two_finger_start_positions[0].y()
                    dy1 = p1.y() - self._two_finger_start_positions[1].y()
                    avg_dx = (dx0 + dx1) / 2.0
                    avg_dy = (dy0 + dy1) / 2.0

                    if not self._two_finger_swipe_triggered:
                        if (
                            dt_ms <= 500.0
                            and (dy0 * dy1 > 0)
                            and (abs(avg_dy) > 1.3 * abs(avg_dx))
                        ):
                            if avg_dy <= -70.0:  # Свайп вверх -> следующий (+1)
                                self._two_finger_swipe_triggered = True
                                self._suppress_mouse_release = True
                                self._switch_tab(1)
                                consumed = True
                            elif avg_dy >= 70.0:  # Свайп вниз -> предыдущий (-1)
                                self._two_finger_swipe_triggered = True
                                self._suppress_mouse_release = True
                                self._switch_tab(-1)
                                consumed = True

                if self._two_finger_swipe_triggered:
                    consumed = True

                self._touch_active = False
                self._two_finger_active = False
                self._two_finger_swipe_triggered = False

                self._schedule_cursor_restore()

                if consumed:
                    return True

        # 2. Синтезированный клик мыши после тача / подавление ложного клика
        elif etype == QEvent.Type.MouseButtonRelease:
            self._schedule_cursor_restore()
            if self._suppress_mouse_release:
                self._suppress_mouse_release = False
                return True

        return super().eventFilter(watched, event)

    def _schedule_cursor_restore(self):
        """Отложенный возврат курсора в точку на основном мониторе."""
        if self.guardian and hasattr(self.guardian, "restore_cursor_to_primary"):
            delay = getattr(self.guardian, "cursor_restore_delay_ms", 25)
            QTimer.singleShot(delay, self.guardian.restore_cursor_to_primary)
