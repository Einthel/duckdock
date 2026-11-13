"""
Модуль «Focus Guardian & Anti-Cursor Warp».
Предотвращает кражу фокуса у полноэкранных игр и приложений на основном мониторе
при касании сенсорного 7" экрана 800x600.
"""
import sys
import time
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class FocusGuardian:
    """Защитник системного фокуса и положения курсора мыши."""

    def __init__(
        self,
        subscreen_rect: Tuple[int, int, int, int] = (1920, 0, 800, 600),
        restore_delay_ms: int = 80,
        cursor_restore_delay_ms: int = 25,
    ):
        self.subscreen_rect = subscreen_rect  # x, y, w, h
        self.restore_delay_ms = restore_delay_ms
        self.cursor_restore_delay_ms = cursor_restore_delay_ms
        self.input_lock_mode = False  # True = разрешить ввод с клавиатуры (отключить возврат)

        self.last_primary_hwnd: Optional[int] = None
        self.last_primary_cursor_pos: Tuple[int, int] = (960, 540)
        self._hook_id = None

    def enable_stealth_window_style(self, hwnd: int) -> bool:
        """
        Установить расширенный стиль WS_EX_NOACTIVATE для предотвращения передачи фокуса ОС.
        """
        if not HAS_WIN32 or not win32gui.IsWindow(hwnd):
            return False

        try:
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_NOACTIVATE | win32con.WS_EX_APPWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            return True
        except Exception as e:
            print(f"[!] Ошибка установки WS_EX_NOACTIVATE: {e}")
            return False

    def update_primary_cursor(self, x: int, y: int):
        """Сохранить позицию курсора, если он находится в пределах основного монитора."""
        sx, sy, sw, sh = self.subscreen_rect
        # Если координаты курсора НЕ попадают во 2-й экран
        if not (sx <= x < sx + sw and sy <= y < sy + sh):
            self.last_primary_cursor_pos = (x, y)

    def restore_cursor_to_primary(self):
        """Вернуть курсор на основной монитор в точку последнего известного положения."""
        if not HAS_WIN32:
            return
        try:
            time.sleep(self.cursor_restore_delay_ms / 1000.0)
            win32api.SetCursorPos(self.last_primary_cursor_pos)
        except Exception as e:
            print(f"[!] Ошибка возврата курсора: {e}")

    def is_subscreen_window(self, hwnd: int) -> bool:
        """Проверить, расположено ли окно в координатах вспомогательного экрана."""
        if not HAS_WIN32 or not win32gui.IsWindow(hwnd):
            return False
        try:
            rect = win32gui.GetWindowRect(hwnd)
            sx, sy, sw, sh = self.subscreen_rect
            # Центр окна попадает во вспомогательный экран
            cx = (rect[0] + rect[2]) // 2
            cy = (rect[1] + rect[3]) // 2
            return sx <= cx < sx + sw and sy <= cy < sy + sh
        except Exception:
            return False

    def restore_focus_to_primary(self):
        """
        Принудительно вернуть фокус окну на основном мониторе с обходом ограничений Windows.
        """
        if not HAS_WIN32 or self.input_lock_mode or not self.last_primary_hwnd:
            return

        if not win32gui.IsWindow(self.last_primary_hwnd):
            return

        target_hwnd = self.last_primary_hwnd

        try:
            time.sleep(self.restore_delay_ms / 1000.0)

            # Получаем ID потоков
            fore_hwnd = win32gui.GetForegroundWindow()
            if fore_hwnd == target_hwnd:
                return

            fore_tid, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
            target_tid, _ = win32process.GetWindowThreadProcessId(target_hwnd)
            current_tid = win32api.GetCurrentThreadId()

            # Мягкий обход через AttachThreadInput
            attached = False
            try:
                win32process.AttachThreadInput(current_tid, target_tid, True)
                attached = True
            except Exception:
                pass

            # Альтернативный толчок очереди через клавишу Alt (VK_MENU)
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)

            win32gui.SetForegroundWindow(target_hwnd)
            win32gui.BringWindowToTop(target_hwnd)

            if attached:
                try:
                    win32process.AttachThreadInput(current_tid, target_tid, False)
                except Exception:
                    pass

        except Exception as e:
            print(f"[!] Ошибка возврата фокуса: {e}")
