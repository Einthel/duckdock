"""
Интерактивная ячейка кнопки холста DuckDeck Editor (EditorGridCell).
Отображает слот кнопки [0]..[9], превью иконки и заголовка,
поддерживает состояния ховера, синего фокуса (selected) и сигнал клика.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from modules.deck.editor.styles import (
    GRID_CELL_SIZE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

logger = logging.getLogger(__name__)


class EditorGridCell(QFrame):
    """
    Интерактивная ячейка холста DuckDeck (96x96 px).
    - Метка индекса [0]..[9] в верхнем левом углу (10px, #71717a).
    - Центральная иконка (шрифт 26px, центрированная).
    - Нижний заголовок (11px, центрированный, с эллипсисом).
    - Эксклюзивное выделение рамкой 2px #0078d4 через свойство selected.
    """

    cell_clicked = Signal(int)

    def __init__(self, slot_index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.slot_index = slot_index
        self._title = ""
        self._icon = ""
        self._category = ""
        self._hotkey = ""

        self.setObjectName("editorGridCell")
        self.setProperty("editorGridCell", "true")
        self.setProperty("selected", "false")
        self.setFixedSize(GRID_CELL_SIZE, GRID_CELL_SIZE)
        self.setCursor(Qt.PointingHandCursor)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        # Верхняя строка: индекс слота [0]..[9]
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.lbl_index = QLabel(f"[{self.slot_index}]", self)
        self.lbl_index.setObjectName("lblCellIndex")
        self.lbl_index.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_index.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 600; background: transparent; border: none;"
        )
        top_layout.addWidget(self.lbl_index, alignment=Qt.AlignLeft | Qt.AlignTop)
        top_layout.addStretch(1)

        layout.addLayout(top_layout)

        # Центральная зона: иконка (26px)
        self.lbl_icon = QLabel("", self)
        self.lbl_icon.setObjectName("lblCellIcon")
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 26px; background: transparent; border: none;"
        )
        layout.addWidget(self.lbl_icon, 1, alignment=Qt.AlignCenter)

        # Нижняя зона: заголовок (11px)
        self.lbl_title = QLabel("", self)
        self.lbl_title.setObjectName("lblCellTitle")
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 500; background: transparent; border: none;"
        )
        layout.addWidget(self.lbl_title, alignment=Qt.AlignCenter)

    def set_selected(self, selected: bool) -> None:
        """
        Переключает состояние выделения ячейки.
        Обновляет динамическое свойство 'selected' и перезагружает стиль.
        """
        val_str = "true" if selected else "false"
        if self.property("selected") == val_str:
            return

        self.setProperty("selected", val_str)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def is_selected(self) -> bool:
        """
        Возвращает True, если ячейка выделена.
        """
        return self.property("selected") in ("true", True)

    def set_button_data(
        self,
        title: str,
        icon: str,
        category: str = "",
        hotkey: str = "",
    ) -> None:
        """
        Задает отображаемые данные кнопки в ячейке.
        """
        self._title = title
        self._icon = icon
        self._category = category
        self._hotkey = hotkey

        self.lbl_icon.setText(icon)

        # Эллипсис для длинных названий
        metrics = QFontMetrics(self.lbl_title.font())
        elided = metrics.elidedText(title, Qt.ElideRight, GRID_CELL_SIZE - 16)
        self.lbl_title.setText(elided)
        self.setToolTip(f"{title} ({hotkey})" if hotkey else title)

    def clear_button_data(self) -> None:
        """
        Сбрасывает данные кнопки, возвращая ячейку в пустое состояние.
        """
        self._title = ""
        self._icon = ""
        self._category = ""
        self._hotkey = ""

        self.lbl_icon.setText("")
        self.lbl_title.setText("")
        self.setToolTip("")

    def get_button_data(self) -> dict[str, str]:
        """
        Возвращает словарь текущих данных ячейки.
        """
        return {
            "title": self._title,
            "icon": self._icon,
            "category": self._category,
            "hotkey": self._hotkey,
        }

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Обработка клика мыши: эмиттирует cell_clicked(slot_index) при нажатии ЛКМ.
        """
        if event.button() == Qt.LeftButton:
            self.cell_clicked.emit(self.slot_index)
            event.accept()
        else:
            super().mousePressEvent(event)
