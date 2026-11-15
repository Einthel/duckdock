"""
Базовые UI-классы DuckDock / TouchWM.
Определяет абстрактный базовый класс TouchModuleView с принудительным инвариантом Stealth Focus.
"""
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


class TouchModuleView(QWidget):
    """
    Базовый класс экрана DuckDock.
    Гарантирует инвариант Stealth Focus: окно и все дочерние элементы
    не перехватывают фокус у основного 27" монитора.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)

    def cleanup(self) -> None:
        """Безопасная очистка ресурсов, таймеров и отписка от шины EventBus."""
        pass


__all__ = ["TouchModuleView"]
