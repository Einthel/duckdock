"""
Модуль «Mouse Barrier & Sticky Edges».
Ограничивает случайный вылет курсора мыши с основного монитора на вспомогательный
без удерживания модификатора (Alt).
"""
import sys
from typing import Tuple

try:
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class MouseBarrier:
    """Контроллер удержания мыши на основном экране."""

    def __init__(self, primary_rect: Tuple[int, int, int, int] = (0, 0, 1920, 1080)):
        self.primary_rect = primary_rect
        self.enabled = False

    def is_alt_pressed(self) -> bool:
        """Проверить, зажата ли клавиша Alt."""
        if not HAS_WIN32:
            return False
        # GetAsyncKeyState: старший бит 0x8000 установлен, если клавиша нажата
        return bool(win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000)

    def clamp_cursor_to_primary(self):
        """Если Alt не нажат, не давать курсору уходить за правую границу основного экрана."""
        if not HAS_WIN32 or not self.enabled:
            return

        if self.is_alt_pressed():
            return

        try:
            x, y = win32api.GetCursorPos()
            px, py, pw, ph = self.primary_rect
            if x >= px + pw - 2:
                win32api.SetCursorPos((px + pw - 4, y))
        except Exception:
            pass
