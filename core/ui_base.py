"""
Базовые UI-классы DuckDock / TouchWM.
Определяет абстрактный базовый класс TouchModuleView с принудительным инвариантом Stealth Focus
и реактивной поддержкой интернационализации (i18n).
"""
from typing import Optional
import warnings
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from core.event_bus import bus


class TouchModuleView(QWidget):
    """
    Базовый класс экрана DuckDock.
    Гарантирует инвариант Stealth Focus: окно и все дочерние элементы
    не перехватывают фокус у основного 27" монитора.
    Автоматически реагирует на смену языка через шину EventBus.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)

        # Автоматическая реактивная подписка на смену языка
        self._is_i18n_connected = True
        bus.language_changed.connect(self._handle_language_changed)
        self.destroyed.connect(self._on_view_destroyed)

    def _handle_language_changed(self, lang_code: str) -> None:
        try:
            self.retranslate_ui()
        except RuntimeError:
            self._disconnect_language_signal()

    def retranslate_ui(self) -> None:
        """
        Переопределяется каждым модулем для обновления текстов элементов.
        Служит единым источником правды для всех текстовых меток.
        """
        pass

    def _on_view_destroyed(self, *args) -> None:
        self._disconnect_language_signal()

    def _disconnect_language_signal(self) -> None:
        if not getattr(self, "_is_i18n_connected", False):
            return
        self._is_i18n_connected = False
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            try:
                bus.language_changed.disconnect(self._handle_language_changed)
            except (RuntimeError, TypeError, Exception):
                pass

    def cleanup(self) -> None:
        """Безопасная очистка ресурсов, таймеров и отписка от шины EventBus."""
        self._disconnect_language_signal()

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)


__all__ = ["TouchModuleView"]
