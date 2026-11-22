"""
Менеджер жизненного цикла окна конфигуратора DuckDeck (DeckEditorManager).
Реализует потокобезопасный паттерн Singleton для управления окном DeckEditorWindow:
  - Открытие окна на основном мониторе (Primary 27" 2560x1440 dGPU).
  - Центрирование окна (1080x740 px) в доступной рабочей области primaryScreen.
  - Сохранение архитектурного инварианта Stealth Focus (WS_EX_NOACTIVATE на 7" iGPU).
  - Предотвращение циклических импортов и утечек ресурсов.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional, Union

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from modules.deck.editor.styles import WINDOW_DEFAULT_SIZE

logger = logging.getLogger("duckdock.deck.editor.manager")


def _is_widget_valid(widget: Optional[QWidget]) -> bool:
    """Проверяет валидность C++ объекта QWidget (исключает сбои после deleteLater/close)."""
    if widget is None:
        return False
    try:
        import shiboken6

        if not shiboken6.isValid(widget):
            return False
    except Exception:
        pass
    try:
        _ = widget.windowTitle()
        return True
    except (RuntimeError, AttributeError):
        return False


class DeckEditorManager:
    """
    Потокобезопасный синглтон-менеджер окна конфигуратора DuckDeck.
    Управляет жизненным циклом DeckEditorWindow на основном 27" dGPU мониторе.
    """

    _instance: Optional[DeckEditorManager] = None
    _editor_window: Optional[QWidget] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls, *args, **kwargs) -> DeckEditorManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def open_editor(
        cls,
        parent: Optional[QWidget] = None,
        page_id: Optional[Union[str, int]] = None,
    ) -> QWidget:
        """
        Открывает или выводит на передний план окно конфигуратора DeckEditorWindow.

        Инварианты:
          - Создается без родителя (parent=None, независимое top-level окно ОС).
          - Центрируется строго на доступной области основного экрана (primaryScreen).
          - DuckDock на 7" экране сохраняет свойство WS_EX_NOACTIVATE и Qt.NoFocus.
        """
        with cls._lock:
            # 1. Проверяем валидность существующего окна
            if cls._editor_window is not None and not _is_widget_valid(cls._editor_window):
                cls._editor_window = None

            # 2. Если окно не создано — инстанцируем DeckEditorWindow(parent=None)
            if cls._editor_window is None:
                from modules.deck.editor.window import DeckEditorWindow

                # Независимое top-level окно (parent=None исключает передачу фокуса тачскрину)
                window = DeckEditorWindow(parent=None)
                window.destroyed.connect(cls._on_window_destroyed)
                cls._editor_window = window
                logger.info("DeckEditorWindow instance created.")

            window = cls._editor_window

            # 3. Центрирование и позиционирование на основном экране
            cls._center_on_primary_screen(window)

            # 4. Восстановление из свернутого состояния и отображение
            if window.isMinimized():
                window.showNormal()

            window.show()
            window.raise_()
            window.activateWindow()

            # 5. Переключение на запрошенную страницу, если передана
            if page_id is not None and hasattr(window, "set_page") and callable(window.set_page):
                try:
                    window.set_page(page_id)
                except Exception as exc:
                    logger.warning("Failed to set page '%s' in DeckEditorWindow: %s", page_id, exc)

            return window

    @classmethod
    def _center_on_primary_screen(cls, window: QWidget) -> None:
        """Центрирует окно (1080x740) в пределах доступной геометрии primaryScreen."""
        screen = QGuiApplication.primaryScreen()
        target_w, target_h = WINDOW_DEFAULT_SIZE

        if screen is not None:
            avail_geo = screen.availableGeometry()
            window.resize(target_w, target_h)
            x = avail_geo.x() + (avail_geo.width() - target_w) // 2
            y = avail_geo.y() + (avail_geo.height() - target_h) // 2
            window.setGeometry(x, y, target_w, target_h)
        else:
            window.resize(target_w, target_h)

    @classmethod
    def get_instance(cls) -> Optional[QWidget]:
        """Возвращает активный экземпляр DeckEditorWindow или None, если окно закрыто."""
        with cls._lock:
            if cls._editor_window is not None and _is_widget_valid(cls._editor_window):
                return cls._editor_window
            return None

    @classmethod
    def get_window(cls) -> Optional[QWidget]:
        """Алиас для get_instance() для явного обращения к окну."""
        return cls.get_instance()

    @classmethod
    def get_manager(cls) -> DeckEditorManager:
        """Возвращает экземпляр синглтона DeckEditorManager."""
        return cls()

    @classmethod
    def close_editor(cls) -> None:
        """Закрывает окно конфигуратора и освобождает ссылку."""
        with cls._lock:
            if cls._editor_window is not None:
                if _is_widget_valid(cls._editor_window):
                    try:
                        cls._editor_window.close()
                    except Exception as exc:
                        logger.warning("Error while closing DeckEditorWindow: %s", exc)
                cls._editor_window = None
                logger.info("DeckEditorWindow closed via manager.")

    @classmethod
    def _on_window_destroyed(cls, obj: Optional[QObject] = None) -> None:
        """Слот обработки разрушения C++ объекта окна."""
        with cls._lock:
            cls._editor_window = None
            logger.debug("DeckEditorWindow destroyed signal received.")


__all__ = ["DeckEditorManager"]
