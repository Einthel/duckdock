"""
Виджет отдельного действия каталога DuckDeck (ActionItemWidget).
Представляет собой компактную кликабельную карточку действия с иконкой и локализованным названием.
"""
from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal, QMimeData
from PySide6.QtGui import QDrag, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from modules.deck.editor.dto import ActionItemDTO
from modules.deck.editor.styles import ACTION_ITEM_HEIGHT


class ActionItemWidget(QFrame):
    """
    Карточка действия в библиотеке DuckDeck.
    Высота 36 px, стиль ActionItemCard, подложка иконки 24x24 px.
    Поддерживает протокол локализации retranslate_ui и эмитирует сигнал item_clicked(ActionItemDTO).
    """

    item_clicked = Signal(object)

    def __init__(
        self,
        item_dto: ActionItemDTO,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.item_dto = item_dto

        self.setObjectName(f"actionItem_{item_dto.id}")
        self.setProperty("class", "ActionItemCard")
        self.setFixedHeight(ACTION_ITEM_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 8, 2)
        layout.setSpacing(8)

        # Подложка иконки (24x24 px)
        self.icon_box = QFrame(self)
        self.icon_box.setObjectName("actionItemIconBox")
        self.icon_box.setProperty("class", "ActionItemIconBox")
        self.icon_box.setFixedSize(24, 24)

        icon_layout = QHBoxLayout(self.icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)

        self.lbl_icon = QLabel(self.item_dto.icon, self.icon_box)
        self.lbl_icon.setObjectName("actionItemIcon")
        self.lbl_icon.setProperty("class", "ActionItemIcon")
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        icon_layout.addWidget(self.lbl_icon)

        layout.addWidget(self.icon_box, 0, Qt.AlignVCenter)

        # Название действия
        self.lbl_title = QLabel(self.item_dto.get_title(), self)
        self.lbl_title.setObjectName("actionItemTitle")
        self.lbl_title.setProperty("class", "ActionItemTitle")
        self.lbl_title.setTextFormat(Qt.PlainText)
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents)

        layout.addWidget(self.lbl_title, 1, Qt.AlignVCenter)

        # Подсказка
        self.setToolTip(self.item_dto.get_title())

        self._drag_start_pos: Optional[QPoint] = None

    def retranslate_ui(self) -> None:
        """Обновляет локализованное название действия и тултип."""
        title = self.item_dto.get_title()
        self.lbl_title.setText(title)
        self.setToolTip(title)

    def set_active(self, active: bool) -> None:
        """Устанавливает визуальный статус активности карточки."""
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Обработка клика левой кнопкой мыши: эмиссия сигнала item_clicked."""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self.item_clicked.emit(self.item_dto)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Инициализация Drag-and-Drop при перемещении с зажатой ЛКМ."""
        if (event.buttons() & Qt.LeftButton) and self._drag_start_pos is not None:
            dist = (event.pos() - self._drag_start_pos).manhattanLength()
            if dist >= QApplication.startDragDistance():
                self._drag_start_pos = None

                cat_id = getattr(self.item_dto, "category_id", "")
                if not cat_id and getattr(self.item_dto, "category_key", ""):
                    cat_id = self.item_dto.category_key.split(".")[-1]

                payload = {
                    "id": self.item_dto.id,
                    "title": self.item_dto.get_title(),
                    "icon": self.item_dto.icon,
                    "category": self.item_dto.category_key,
                    "category_id": cat_id,
                    "keywords": self.item_dto.keywords,
                }
                mime = QMimeData()
                mime.setData("application/x-duckdeck-action", json.dumps(payload).encode("utf-8"))
                drag = QDrag(self)
                drag.setMimeData(mime)
                pixmap = self.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(event.pos())
                drag.exec(Qt.CopyAction)
                return
        super().mouseMoveEvent(event)
