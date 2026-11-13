"""
Менеджер окон для бесшовного тайлинга сторонних приложений (happ, AIDA64) в рабочую область.
Включает фоновый ProcessWatcher для автоматического обнаружения, снятия рамок и тайлинга.
"""
import sys
from typing import Optional, Tuple, List, Dict
import psutil

from PySide6.QtCore import QObject, Signal, QTimer

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

    def get_cached_hwnd(self, process_name: str) -> Optional[int]:
        """Получить кэшированный дескриптор окна, если оно все еще существует."""
        hwnd = self._cached_hwnds.get(process_name)
        if hwnd:
            if self.is_window_valid(hwnd):
                return hwnd
            del self._cached_hwnds[process_name]
        return None

    def uncache_hwnd(self, process_name: str) -> None:
        """Удалить процесс из кэша окон."""
        self._cached_hwnds.pop(process_name, None)

    def is_window_valid(self, hwnd: int) -> bool:
        """Проверить, действительно ли окно существует в системе."""
        if not HAS_WIN32:
            return False
        try:
            return bool(win32gui.IsWindow(hwnd))
        except Exception:
            return False

    def is_minimized(self, hwnd: int) -> bool:
        """Проверить, свернуто ли окно (в трей или панель задач)."""
        if not HAS_WIN32 or not self.is_window_valid(hwnd):
            return False
        try:
            return bool(win32gui.IsIconic(hwnd))
        except Exception:
            return False

    def restore_window(self, hwnd: int) -> bool:
        """Восстановить свернутое окно."""
        if not HAS_WIN32 or not self.is_window_valid(hwnd):
            return False
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
        except Exception:
            return False

    def find_window_by_process_name(self, process_name: str) -> Optional[int]:
        """
        Найти HWND главного видимого окна процесса по его имени (например, 'happ.exe').
        """
        if not HAS_WIN32:
            return None

        # Проверяем кэшированный дескриптор
        cached = self.get_cached_hwnd(process_name)
        if cached:
            return cached

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
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    title = win32gui.GetWindowText(hwnd)
                    # Окно с ненулевым размером или заголовком
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
        if not HAS_WIN32 or not self.is_window_valid(hwnd):
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
        if not HAS_WIN32 or not self.is_window_valid(hwnd):
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
        """Отобразить окно без передачи ему фокуса (SW_SHOWNOACTIVATE)."""
        if not HAS_WIN32 or not self.is_window_valid(hwnd):
            return False
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            return True
        except Exception:
            return False

    def hide_window(self, hwnd: int) -> bool:
        """Скрыть окно (SW_HIDE)."""
        if not HAS_WIN32 or not self.is_window_valid(hwnd):
            return False
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            return True
        except Exception:
            return False


class ProcessWatcher(QObject):
    """
    Фоновый наблюдатель за процессами сторонних приложений.
    Периодически проверяет статус отслеживаемых приложений по таймеру (1.5–2 сек),
    кэширует дескрипторы, снимает декорации и сигнализирует об обнаружении/закрытии окон.
    """
    window_discovered = Signal(str, int)  # process_name, hwnd
    window_lost = Signal(str, int)        # process_name, hwnd

    def __init__(
        self,
        window_manager: WindowManager,
        tracked_apps: Optional[List[str]] = None,
        poll_interval_ms: int = 1500,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.window_manager = window_manager
        self.tracked_apps: List[str] = tracked_apps or []
        self.poll_interval_ms = poll_interval_ms

        self._timer = QTimer(self)
        self._timer.setInterval(self.poll_interval_ms)
        self._timer.timeout.connect(self.scan)

    def start(self):
        """Запустить периодический мониторинг."""
        self._timer.start()
        # Выполняем предварительное сканирование сразу
        self.scan()

    def stop(self):
        """Остановить периодический мониторинг."""
        self._timer.stop()

    def add_tracked_app(self, process_name: str):
        """Добавить процесс в список отслеживания."""
        if process_name not in self.tracked_apps:
            self.tracked_apps.append(process_name)

    def remove_tracked_app(self, process_name: str):
        """Удалить процесс из отслеживания."""
        if process_name in self.tracked_apps:
            self.tracked_apps.remove(process_name)

    def scan(self):
        """
        Периодическое сканирование:
        - Проверка существующих кэшированных HWND на закрытие.
        - Поиск новых запущенных окон для отслеживаемых процессов.
        - Снятие рамок при обнаружении.
        """
        if not HAS_WIN32:
            return

        # 1. Проверяем кэшированные окна: живы ли они еще?
        cached_copy = dict(self.window_manager._cached_hwnds)
        for proc_name, hwnd in cached_copy.items():
            if not self.window_manager.is_window_valid(hwnd):
                self.window_manager.uncache_hwnd(proc_name)
                self.window_lost.emit(proc_name, hwnd)

        # 2. Ищем новые окна для отслеживаемых приложений
        for proc_name in self.tracked_apps:
            cached_hwnd = self.window_manager.get_cached_hwnd(proc_name)
            if cached_hwnd and self.window_manager.is_window_valid(cached_hwnd):
                continue

            hwnd = self.window_manager.find_window_by_process_name(proc_name)
            if hwnd:
                self.window_manager.strip_window_decorations(hwnd)
                self.window_discovered.emit(proc_name, hwnd)
