"""
Плитка превью иконки макро-кнопки (KeyPreviewTile).
Габариты 84x84, скругление 10px, угловые кнопки загрузки и опций (18x18) с поддержкой i18n.
"""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QWidget

from core.i18n import t
from modules.deck.editor.styles import ICON_BTN_SIZE, PREVIEW_TILE_SIZE


class KeyPreviewTile(QFrame):
    """
    Интерактивная плитка предварительного просмотра иконки кнопки (84x84 px).
    Включает центральное отображение символа/картинки и две микро-кнопки (18x18 px):
    '+' в левом верхнем углу (загрузка файла изображения) и
    'v' в правом верхнем углу (меню настроек/выбора готовых иконок).
    """

    add_icon_clicked = Signal()
    icon_menu_clicked = Signal()
    tile_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("keyPreviewTile")
        self.setProperty("class", "KeyPreviewTile")
        self.setFixedSize(PREVIEW_TILE_SIZE, PREVIEW_TILE_SIZE)
        self.setCursor(Qt.PointingHandCursor)

        self._current_icon: str = "🖲️"

        # Центральная метка превью иконки (эмодзи, символ или QPixmap)
        self.lbl_icon = QLabel(self)
        self.lbl_icon.setObjectName("lblTileIcon")
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        font = self.lbl_icon.font()
        font.setPixelSize(32)
        self.lbl_icon.setFont(font)

        # Левая верхняя микро-кнопка '+' (загрузка изображения)
        self.btn_add = QPushButton("+", self)
        self.btn_add.setObjectName("btnTileAddIcon")
        self.btn_add.setProperty("class", "TileCornerButton")
        self.btn_add.setFixedSize(ICON_BTN_SIZE, ICON_BTN_SIZE)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self.add_icon_clicked.emit)

        # Правая верхняя микро-кнопка 'v' (опции иконки)
        self.btn_menu = QPushButton("v", self)
        self.btn_menu.setObjectName("btnTileMenuIcon")
        self.btn_menu.setProperty("class", "TileCornerButton")
        self.btn_menu.setFixedSize(ICON_BTN_SIZE, ICON_BTN_SIZE)
        self.btn_menu.setCursor(Qt.PointingHandCursor)
        self.btn_menu.clicked.connect(self.icon_menu_clicked.emit)

        # Первичное позиционирование и применение начального состояния
        self._update_geometry()
        self.set_icon(self._current_icon)
        self.retranslate_ui()

    def _update_geometry(self) -> None:
        w = self.width()
        h = self.height()
        self.lbl_icon.setGeometry(0, 0, w, h)
        padding = 5
        self.btn_add.setGeometry(padding, padding, ICON_BTN_SIZE, ICON_BTN_SIZE)
        self.btn_menu.setGeometry(w - ICON_BTN_SIZE - padding, padding, ICON_BTN_SIZE, ICON_BTN_SIZE)
        self.btn_add.raise_()
        self.btn_menu.raise_()

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self._update_geometry()

    def set_icon(self, icon_str_or_path: str) -> None:
        """
        Устанавливает иконку: растровый файл (PNG/SVG/JPG) или строку символа/эмодзи.
        """
        self._current_icon = icon_str_or_path
        if icon_str_or_path and os.path.isfile(icon_str_or_path):
            pixmap = QPixmap(icon_str_or_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    48,
                    48,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.lbl_icon.setPixmap(scaled)
                return
        # Обычный текст или эмодзи
        self.lbl_icon.setText(icon_str_or_path if icon_str_or_path else "")

    def get_icon(self) -> str:
        """
        Возвращает строковый идентификатор или путь текущей иконки.
        """
        return self._current_icon

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованные всплывающие подсказки для угловых кнопок.
        """
        self.btn_add.setToolTip(t("deck.editor.inspector.tooltips.load_image"))
        self.btn_menu.setToolTip(t("deck.editor.inspector.tooltips.icon_options"))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Обработка клика по самой плитке для генерации события выделения.
        """
        if event.button() == Qt.LeftButton:
            self.tile_clicked.emit()
        super().mousePressEvent(event)
