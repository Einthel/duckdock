"""
Модуль «Mouse Barrier & Sticky Edges».
Ограничивает случайный вылет курсора мыши с основного монитора на вспомогательный
без удерживания модификатора (Alt) с использованием нативного WinAPI ClipCursor.
"""
import sys
import atexit
import ctypes
from ctypes import wintypes
from typing import Tuple, Optional

try:
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

class MouseBarrier:
    """Контроллер удержания мыши на основном экране через user32.ClipCursor."""

    def __init__(self, primary_rect: Tuple[int, int, int, int] = (0, 0, 1920, 1080)):
        self.primary_rect = primary_rect  # (x, y, w, h)
        self.enabled = False
        self._is_clipped = False
        atexit.register(self.release_barrier)

    def is_alt_pressed(self) -> bool:
        """Проверить, зажата ли клавиша Alt."""
        if not HAS_WIN32:
            return False
        # GetAsyncKeyState: старший бит 0x8000 установлен, если клавиша нажата
        try:
            return bool(win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000)
        except Exception:
            return False

    def is_cursor_in_primary(self) -> bool:
        """Проверить, находится ли системный курсор в пределах основного монитора."""
        if not HAS_WIN32:
            return False
        try:
            x, y = win32api.GetCursorPos()
            px, py, pw, ph = self.primary_rect
            return px <= x < px + pw and py <= y < py + ph
        except Exception:
            return False

    def enable(self):
        """Включить режим аппаратного барьера."""
        self.enabled = True
        if not self.is_alt_pressed() and self.is_cursor_in_primary():
            self.apply_barrier()

    def disable(self):
        """Отключить барьер и освободить мышь."""
        self.enabled = False
        self.release_barrier()

    def apply_barrier(self) -> bool:
        """Запереть курсор в пределах primary_rect через ClipCursor."""
        if not HAS_WIN32 or not self.enabled:
            return False
        try:
            px, py, pw, ph = self.primary_rect
            rect = RECT(px, py, px + pw, py + ph)
            res = ctypes.windll.user32.ClipCursor(ctypes.byref(rect))
            self._is_clipped = bool(res)
            return self._is_clipped
        except Exception as e:
            print(f"[!] Ошибка ClipCursor: {e}")
            return False

    def release_barrier(self) -> bool:
        """Снять ограничение ClipCursor (NULL)."""
        if not HAS_WIN32:
            return False
        try:
            res = ctypes.windll.user32.ClipCursor(None)
            self._is_clipped = False
            return bool(res)
        except Exception as e:
            print(f"[!] Ошибка освобождения ClipCursor: {e}")
            return False

    def update(self):
        """
        Регулярный опрос состояния клавиши Alt и позиции мыши.
        Вызывается по таймеру UI (каждые 20-30 мс).
        """
        if not HAS_WIN32 or not self.enabled:
            return

        if self.is_alt_pressed():
            if self._is_clipped:
                self.release_barrier()
        else:
            # Alt не нажат. Если курсор на основном экране и еще не заперт — запираем
            if not self._is_clipped and self.is_cursor_in_primary():
                self.apply_barrier()

    # Для обратной совместимости со старыми вызовами
    def clamp_cursor_to_primary(self):
        self.update()
