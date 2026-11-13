"""
Модуль «Focus Guardian & Anti-Cursor Warp».
Предотвращает кражу фокуса у полноэкранных игр и приложений на основном мониторе
при касании сенсорного 7" экрана (800x600 / 1024x600).
"""
import sys
import time
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

from PySide6.QtCore import QObject, QThread, Signal, QTimer

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

if HAS_WIN32:
    WINEVENTPROC = ctypes.WINFUNCTYPE(
        None,
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.HWND,
        wintypes.LONG,
        wintypes.LONG,
        wintypes.DWORD,
        wintypes.DWORD,
    )
else:
    WINEVENTPROC = None


class _FocusHookThread(QThread):
    """
    Потокобезопасный поток с собственным циклом сообщений Win32
    для отслеживания смены активного окна через SetWinEventHook.
    """
    foreground_changed = Signal(int)  # emits hwnd

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._running = False
        self._hook = None
        self.thread_id: Optional[int] = None
        if HAS_WIN32:
            # Сохраняем ссылку на WINFUNCTYPE в поле класса, предотвращая удаление GC
            self._c_callback = WINEVENTPROC(self._winevent_proc)
        else:
            self._c_callback = None

    def _winevent_proc(self, hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
        if event == 0x0003 and hwnd:  # EVENT_SYSTEM_FOREGROUND
            self.foreground_changed.emit(int(hwnd))

    def run(self):
        if not HAS_WIN32 or self._c_callback is None:
            return

        self.thread_id = win32api.GetCurrentThreadId()
        self._running = True

        WINEVENT_OUTOFCONTEXT = 0x0000
        WINEVENT_SKIPOWNPROCESS = 0x0002
        EVENT_SYSTEM_FOREGROUND = 0x0003

        user32 = ctypes.windll.user32
        self._hook = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            0,
            self._c_callback,
            0,
            0,
            WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
        )

        msg = wintypes.MSG()
        while self._running:
            res = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if res <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self):
        self._running = False
        if self._hook and HAS_WIN32:
            try:
                ctypes.windll.user32.UnhookWinEvent(self._hook)
            except Exception:
                pass
            self._hook = None

        if self.thread_id and HAS_WIN32:
            try:
                # WM_QUIT = 0x0012
                ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
            except Exception:
                pass

        self.quit()
        if not self.wait(500):
            self.terminate()
            self.wait(200)


class FocusGuardian(QObject):
    """Защитник системного фокуса и положения курсора мыши."""

    def __init__(
        self,
        subscreen_rect: Tuple[int, int, int, int] = (1920, 0, 800, 600),
        restore_delay_ms: int = 80,
        cursor_restore_delay_ms: int = 25,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.subscreen_rect = subscreen_rect  # x, y, w, h
        self.restore_delay_ms = restore_delay_ms
        self.cursor_restore_delay_ms = cursor_restore_delay_ms
        self.input_lock_mode = False  # True = разрешить ввод с клавиатуры (отключить возврат)

        self.last_primary_hwnd: Optional[int] = None
        self.last_primary_cursor_pos: Tuple[int, int] = (960, 540)
        self._hook_thread: Optional[_FocusHookThread] = None

    def start_hook(self) -> bool:
        """Запустить фоновый WinEvent хук для отслеживания смены фокуса."""
        if not HAS_WIN32:
            return False
        if self._hook_thread and self._hook_thread.isRunning():
            return True

        try:
            self._hook_thread = _FocusHookThread(None)
            self._hook_thread.foreground_changed.connect(self._on_foreground_changed)
            self._hook_thread.start()
            return True
        except Exception as e:
            print(f"[!] Ошибка запуска FocusGuardian hook: {e}")
            return False

    def stop_hook(self) -> None:
        """Остановить фоновый хук."""
        if self._hook_thread:
            try:
                self._hook_thread.stop()
            except Exception as e:
                print(f"[!] Ошибка остановки FocusGuardian hook: {e}")
            self._hook_thread = None

    def _on_foreground_changed(self, hwnd: int):
        """Обработка смены активного окна в системе."""
        if not HAS_WIN32 or not win32gui.IsWindow(hwnd):
            return

        if not self.is_subscreen_window(hwnd):
            # Активное окно находится на основном экране — запоминаем его HWND
            self.last_primary_hwnd = hwnd
        else:
            # Окно на вспомогательном экране перехватило фокус
            if not self.input_lock_mode and self.last_primary_hwnd:
                QTimer.singleShot(self.restore_delay_ms, self.restore_focus_to_primary)

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

    def restore_cursor_to_primary(self, delay: bool = False):
        """Вернуть курсор на основной монитор в точку последнего известного положения."""
        if not HAS_WIN32:
            return
        try:
            if delay and self.cursor_restore_delay_ms > 0:
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

    def restore_focus_to_primary(self, delay: bool = False):
        """
        Принудительно вернуть фокус окну на основном мониторе с обходом ограничений Windows.
        """
        if not HAS_WIN32 or self.input_lock_mode or not self.last_primary_hwnd:
            return

        if not win32gui.IsWindow(self.last_primary_hwnd):
            return

        target_hwnd = self.last_primary_hwnd

        try:
            if delay and self.restore_delay_ms > 0:
                time.sleep(self.restore_delay_ms / 1000.0)

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
            try:
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                pass

            try:
                win32gui.SetForegroundWindow(target_hwnd)
                win32gui.BringWindowToTop(target_hwnd)
            except Exception:
                pass

            if attached:
                try:
                    win32process.AttachThreadInput(current_tid, target_tid, False)
                except Exception:
                    pass

        except Exception as e:
            print(f"[!] Ошибка возврата фокуса: {e}")
