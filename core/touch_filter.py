"""
Модуль «Touch Filter & Anti-Cursor Warp».
Перехватывает тач-события сенсорного экрана и восстанавливает позицию курсора мыши
на основном мониторе без задержек и артефактов дрифта.
"""
from typing import Optional
from PySide6.QtCore import QObject, QEvent, QTimer
from core.focus_guardian import FocusGuardian


class TouchCursorFilter(QObject):
    """
    Глобальный фильтр событий Qt для перехвата тач-ввода
    и возврата курсора на основной монитор.
    """

    def __init__(self, guardian: FocusGuardian, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.guardian = guardian
        self._touch_active = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        etype = event.type()

        # Фиксация начала касания пальцем
        if etype in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate):
            self._touch_active = True

        # Отрыв пальца от сенсора
        elif etype in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            self._touch_active = False
            self._schedule_cursor_restore()

        # Синтезированный клик мыши после тача
        elif etype == QEvent.Type.MouseButtonRelease:
            self._schedule_cursor_restore()

        return super().eventFilter(watched, event)

    def _schedule_cursor_restore(self):
        """Отложенный возврат курсора в точку на основном мониторе."""
        delay = self.guardian.cursor_restore_delay_ms
        QTimer.singleShot(delay, self.guardian.restore_cursor_to_primary)
