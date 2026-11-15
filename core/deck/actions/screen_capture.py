"""
Модуль безопасного и точного захвата экрана (Multi-DPI Screen Capture).
Обеспечивает скриншот первичного монитора (2560x1440) или активного окна
с сохранением в буфер обмена Windows (QClipboard в GUI thread) и/или на диск.
"""
import logging
import os
from typing import Optional, Tuple

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QApplication

logger = logging.getLogger("duckdock.deck.screenshot")

try:
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    win32gui = None


class ClipboardHelper(QObject):
    """
    Потокобезопасный диспетчер записи в системный буфер обмена QClipboard.
    Гарантирует вызов QClipboard строго в главном потоке GUI через механизм сигналов Qt.
    """
    _instance: Optional["ClipboardHelper"] = None
    copy_pixmap_signal = Signal(QPixmap)

    @classmethod
    def get_instance(cls) -> "ClipboardHelper":
        if cls._instance is None:
            cls._instance = ClipboardHelper()
        return cls._instance

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        ClipboardHelper._instance = self
        self.copy_pixmap_signal.connect(self._on_copy_pixmap)

    def _on_copy_pixmap(self, pixmap: QPixmap) -> None:
        try:
            clipboard = QGuiApplication.clipboard()
            if clipboard is not None:
                clipboard.setPixmap(pixmap)
                logger.info("Скриншот успешно помещен в буфер обмена Windows (GUI Thread)")
        except Exception as e:
            logger.error(f"Ошибка записи скриншота в QClipboard: {e}")


def copy_pixmap_to_clipboard(pixmap: QPixmap) -> None:
    """
    Помещает QPixmap в системный буфер обмена.
    Если вызывается из фонового потока (например, QThreadPool),
    делегирует выполнение в поток GUI через ClipboardHelper.
    """
    app = QApplication.instance()
    if not app:
        return

    helper = ClipboardHelper.get_instance()
    if QThread.currentThread() == app.thread():
        helper._on_copy_pixmap(pixmap)
    else:
        helper.copy_pixmap_signal.emit(pixmap)


def get_primary_screen():
    """
    Находит экземпляр QScreen первичного экрана (расположенный в точке 0,0).
    """
    screens = QGuiApplication.screens()
    if not screens:
        return None

    # Ищем экран с геометрией, начинающейся в (0, 0)
    for s in screens:
        geo = s.geometry()
        if geo.x() == 0 and geo.y() == 0:
            return s

    return QGuiApplication.primaryScreen() or screens[0]


def capture_screen(
    target: str = "primary_screen",
    clipboard: bool = True,
    save_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Выполняет захват экрана или активного окна.
    - target: 'primary_screen' (основной 2560x1440) или 'active_window'
    - clipboard: копировать ли в буфер обмена Windows
    - save_path: путь к файлу для сохранения (.png)
    """
    app = QApplication.instance()
    if not app:
        return False, "QApplication не инициализирован"

    try:
        screen = get_primary_screen()
        if not screen:
            return False, "Первичный монитор не обнаружен"

        pixmap: Optional[QPixmap] = None

        if target == "active_window" and HAS_WIN32:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd and win32gui.IsWindow(hwnd):
                pixmap = screen.grabWindow(hwnd)
            else:
                pixmap = screen.grabWindow(0)
        else:
            # Захват первичного монитора без захвата 7" сенсорного экрана
            pixmap = screen.grabWindow(0)

        if not pixmap or pixmap.isNull():
            return False, "Не удалось создать снимок экрана"

        # Запись в системный буфер обмена
        if clipboard:
            copy_pixmap_to_clipboard(pixmap)

        # Сохранение на диск, если указан путь
        if save_path:
            expanded_path = os.path.expandvars(save_path)
            os.makedirs(os.path.dirname(os.path.abspath(expanded_path)), exist_ok=True)
            saved = pixmap.save(expanded_path, "PNG")
            if not saved:
                return False, f"Не удалось сохранить снимок в файл '{expanded_path}'"

        return True, f"Скриншот успешно выполнен ({pixmap.width()}x{pixmap.height()})"

    except Exception as e:
        logger.error(f"Ошибка при захвате экрана: {e}")
        return False, f"Ошибка захвата экрана: {e}"
