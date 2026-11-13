"""
Менеджер окон для бесшовного тайлинга сторонних приложений (happ, AIDA64) в зону 720x600.
"""
import sys
from typing import Optional, Tuple, List, Dict
import psutil

try:
    import win32gui
    import win32con
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class WindowManager:
    """Управление стилями и позиционированием сторонних окон Windows."""

    def __init__(self):
        self._cached_hwnds: Dict[str, int] = {}

    def find_window_by_process_name(self, process_name: str) -> Optional[int]:
        """
        Найти HWND главного видимого окна процесса по его имени (например, 'happ.exe').
        """
        if not HAS_WIN32:
            return None

        # Проверяем кэшированный дескриптор
        if process_name in self._cached_hwnds:
            hwnd = self._cached_hwnds[process_name]
            if win32gui.IsWindow(hwnd):
                return hwnd
            del self._cached_hwnds[process_name]

        # Ищем PID процесса через psutil (сравниваем с учетом регистра и без .exe)
        target_pids = set()
        clean_target = process_name.lower().removesuffix(".exe")
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                pname = (proc.info['name'] or '').lower().removesuffix(".exe")
                if pname == clean_target:
                    target_pids.add(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not target_pids:
            return None

        found_hwnd = None

        def enum_windows_callback(hwnd, _):
            nonlocal found_hwnd
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid in target_pids:
                    # Проверяем размер окна
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    title = win32gui.GetWindowText(hwnd)
                    # Если окно имеет размеры или заголовок
                    if (width > 80 and height > 80) or title:
                        found_hwnd = hwnd
                        return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception:
            pass

        if found_hwnd:
            self._cached_hwnds[process_name] = found_hwnd

        return found_hwnd

    def strip_window_decorations(self, hwnd: int) -> bool:
        """
        Удалить заголовок (WS_CAPTION) и рамку изменения размера (WS_THICKFRAME).
        """
        if not HAS_WIN32 or not win32gui.IsWindow(hwnd):
            return False

        try:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
            style &= ~win32con.WS_MINIMIZEBOX
            style &= ~win32con.WS_MAXIMIZEBOX
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            return True
        except Exception as e:
            print(f"[!] Ошибка удаления рамок HWND {hwnd}: {e}")
            return False

    def tile_window(self, hwnd: int, rect: Tuple[int, int, int, int]) -> bool:
        """
        Вписать окно в заданный прямоугольник (x, y, width, height) без активации.
        """
        if not HAS_WIN32 or not win32gui.IsWindow(hwnd):
            return False

        x, y, width, height = rect
        try:
            # SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW
            flags = (
                win32con.SWP_NOACTIVATE
                | win32con.SWP_FRAMECHANGED
                | win32con.SWP_SHOWWINDOW
            )
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, width, height, flags)
            return True
        except Exception as e:
            print(f"[!] Ошибка позиционирования HWND {hwnd}: {e}")
            return False

    def show_window_no_activate(self, hwnd: int) -> bool:
        """Отобразить окно без передачи ему фокуса."""
        if not HAS_WIN32 or not win32gui.IsWindow(hwnd):
            return False
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            return True
        except Exception:
            return False

    def hide_window(self, hwnd: int) -> bool:
        """Скрыть окно."""
        if not HAS_WIN32 or not win32gui.IsWindow(hwnd):
            return False
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            return True
        except Exception:
            return False
