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
    Потокобезопасное копирование QPixmap в буфер обмена.
    Если вызывается из не-GUI потока, передает изображение через Qt сигнал.
    """
    app = QApplication.instance()
    if not app:
        logger.error("QApplication не инициализирован")
        return

    # Проверка, находимся ли мы в главном GUI потоке
    if QThread.currentThread() == app.thread():
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setPixmap(pixmap)
            logger.info("Скриншот помещен в буфер обмена (прямой вызов в GUI потоке)")
    else:
        helper = ClipboardHelper.get_instance()
        helper.copy_pixmap_signal.emit(pixmap)


def get_primary_screen():
    """Возвращает первичный монитор (2560x1440) через QGuiApplication.primaryScreen()."""
    return QGuiApplication.primaryScreen()


def get_active_window_rect() -> Optional[Tuple[int, int, int, int]]:
    """Возвращает координаты (x, y, w, h) активного окна основного монитора."""
    if not HAS_WIN32 or not win32gui:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or not win32gui.IsWindow(hwnd):
            return None
        rect = win32gui.GetWindowRect(hwnd)
        x, y, r, b = rect
        w = max(1, r - x)
        h = max(1, b - y)
        return (x, y, w, h)
    except Exception as e:
        logger.debug(f"Не удалось получить геометрию активного окна: {e}")
        return None


def capture_screen(
    target: str = "primary_screen",
    clipboard: bool = True,
    save_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Выполняет захват экрана или окна.
    - target: 'primary_screen' или 'active_window'
    - clipboard: скопировать в буфер обмена
    - save_path: путь сохранения PNG/JPG файла
    """
    screen = get_primary_screen()
    if not screen:
        err_msg = "Не удалось обнаружить первичный монитор"
        logger.error(err_msg)
        return False, err_msg

    pixmap: Optional[QPixmap] = None

    if target == "active_window":
        rect = get_active_window_rect()
        if rect:
            x, y, w, h = rect
            pixmap = screen.grabWindow(0, x, y, w, h)
        else:
            # Fallback на полный первичный экран, если окно не определено
            pixmap = screen.grabWindow(0)
    else:
        # Полный первичный экран
        pixmap = screen.grabWindow(0)

    if not pixmap or pixmap.isNull():
        err_msg = "Не удалось получить пиксели экрана (пустой QPixmap)"
        logger.error(err_msg)
        return False, err_msg

    # Копирование в системный буфер обмена
    if clipboard:
        copy_pixmap_to_clipboard(pixmap)

    # Сохранение на диск
    if save_path and save_path.strip():
        expanded = os.path.expandvars(save_path.strip())
        try:
            os.makedirs(os.path.dirname(os.path.abspath(expanded)), exist_ok=True)
            success = pixmap.save(expanded)
            if success:
                logger.info(f"Скриншот сохранен в файл: {expanded}")
                return True, f"Скриншот сохранен: {os.path.basename(expanded)}"
            else:
                logger.error(f"Не удалось записать изображение в файл: {expanded}")
                return False, f"Ошибка сохранения в {expanded}"
        except Exception as e:
            logger.error(f"Исключение при сохранении скриншота: {e}")
            return False, f"Ошибка сохранения: {e}"

    return True, "Скриншот скопирован в буфер"


__all__ = [
    "ClipboardHelper",
    "copy_pixmap_to_clipboard",
    "get_primary_screen",
    "get_active_window_rect",
    "capture_screen",
]
