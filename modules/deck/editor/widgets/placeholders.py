"""
Контейнеры-плейсхолдеры для каркаса окна редактора DuckDeck.
Используются на этапе прототипирования для визуализации компоновки зон.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from modules.deck.editor.styles import (
    CANVAS_SLOT_MIN_HEIGHT,
    HEADER_SLOT_HEIGHT,
    INSPECTOR_SLOT_HEIGHT,
    PAGINATION_SLOT_HEIGHT,
    SEARCH_SLOT_HEIGHT,
)


class PlaceholderBox(QFrame):
    """
    Базовый виджет-заглушка с пунктирной рамкой и центрированной подписью.
    """

    def __init__(
        self,
        label: str = "",
        min_height: int = 40,
        fixed_height: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("placeholderBox", "true")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignCenter)

        self._label = QLabel(label, self)
        self._label.setProperty("placeholderLabel", "true")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

        if fixed_height is not None:
            self.setFixedHeight(fixed_height)
        elif min_height > 0:
            self.setMinimumHeight(min_height)

    def set_label_text(self, text: str) -> None:
        """Обновляет текст центрированной метки плейсхолдера."""
        self._label.setText(text)

    def get_label_text(self) -> str:
        """Возвращает текущий текст метки."""
        return self._label.text()


class HeaderBarSlot(PlaceholderBox):
    """Слот-заглушка для верхней панели управления (селекторы устройств и профилей)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            label="[Header Bar Slot - 52px]",
            fixed_height=HEADER_SLOT_HEIGHT,
            parent=parent,
        )


class CanvasAreaSlot(PlaceholderBox):
    """Слот-заглушка для холста кнопок (2 ряда по 5 кнопок) и тачбара."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            label="[Canvas Area Slot - min 300px]",
            min_height=CANVAS_SLOT_MIN_HEIGHT,
            parent=parent,
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


class PaginationBarSlot(PlaceholderBox):
    """Слот-заглушка для панели пагинации страниц кнопок."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            label="[Pagination Bar Slot - 36px]",
            fixed_height=PAGINATION_SLOT_HEIGHT,
            parent=parent,
        )


class InspectorSlot(PlaceholderBox):
    """Слот-заглушка для постоянной нижней панели инспектора свойств."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            label="[Property Inspector Slot - 220px]",
            fixed_height=INSPECTOR_SLOT_HEIGHT,
            parent=parent,
        )


class SearchSlot(PlaceholderBox):
    """Слот-заглушка для поисковой строки библиотеки действий."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            label="[Search Slot - 52px]",
            fixed_height=SEARCH_SLOT_HEIGHT,
            parent=parent,
        )


class ActionListSlot(PlaceholderBox):
    """Слот-заглушка для аккордеона категорий и списка действий."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            label="[Action List Slot - Expanding]",
            min_height=100,
            parent=parent,
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
