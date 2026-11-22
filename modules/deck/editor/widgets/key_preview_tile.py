"""
Плитка превью иконки макро-кнопки (KeyPreviewTile).
Габариты 84x84, скругление 10px, угловые кнопки загрузки и опций (20x20) с поддержкой i18n
и контекстным меню Dark Obsidian v2.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QMenu, QPushButton, QWidget

from core.i18n import t
from modules.deck.editor.styles import ICON_BTN_SIZE, PREVIEW_TILE_SIZE

logger = logging.getLogger("duckdock.deck.editor.key_preview_tile")


class KeyPreviewTile(QFrame):
    """
    Интерактивная плитка предварительного просмотра иконки кнопки (84x84 px).
    Включает центральное отображение символа/картинки и две микро-кнопки (20x20 px):
    '+' в левом верхнем углу (открытие библиотеки иконок) и
    'v' в правом верхнем углу (контекстное меню опций иконки).
    """

    add_icon_clicked = Signal()
    icon_menu_clicked = Signal()
    tile_clicked = Signal()
    icon_selected = Signal(str)
    open_library_requested = Signal()

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
        font.setPixelSize(40)
        self.lbl_icon.setFont(font)

        # Левая верхняя микро-кнопка '+' (библиотека иконок)
        self.btn_add = QPushButton("+", self)
        self.btn_add.setObjectName("btnTileAddIcon")
        self.btn_add.setProperty("class", "TileCornerButton")
        self.btn_add.setFixedSize(ICON_BTN_SIZE, ICON_BTN_SIZE)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._on_btn_add_clicked)

        # Правая верхняя микро-кнопка 'v' (опции иконки)
        self.btn_menu = QPushButton("v", self)
        self.btn_menu.setObjectName("btnTileMenuIcon")
        self.btn_menu.setProperty("class", "TileCornerButton")
        self.btn_menu.setFixedSize(ICON_BTN_SIZE, ICON_BTN_SIZE)
        self.btn_menu.setCursor(Qt.PointingHandCursor)
        self.btn_menu.clicked.connect(self._on_btn_menu_clicked)

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

    def _on_btn_add_clicked(self) -> None:
        self.add_icon_clicked.emit()
        self.open_library_requested.emit()

    def _on_btn_menu_clicked(self) -> None:
        self.icon_menu_clicked.emit()
        self._show_icon_context_menu()

    def _show_icon_context_menu(self) -> None:
        """
        Отображает стилизованное контекстное меню QMenu под кнопкой 'v'
        с опциями загрузки файла, открытия библиотеки, перехода в папку и сброса.
        """
        menu = QMenu(self.btn_menu)
        menu.setObjectName("iconOptionsMenu")

        # 1. Заголовок меню (неактивный)
        act_header = menu.addAction(f"🎨 {t('deck.editor.menu.icon.header')}")
        act_header.setEnabled(False)
        menu.addSeparator()

        # 2. Выбрать из файла...
        act_file = menu.addAction(f"📁 {t('deck.editor.menu.icon.set_from_file')}")
        act_file.triggered.connect(self._choose_icon_from_file)

        # 3. Открыть библиотеку иконок...
        act_lib = menu.addAction(f"📚 {t('deck.editor.menu.icon.open_library')}")
        act_lib.triggered.connect(self.open_library_requested.emit)

        menu.addSeparator()

        # 4. Открыть папку пользовательских иконок
        act_folder = menu.addAction(f"📂 {t('deck.editor.menu.icon.open_folder')}")
        act_folder.triggered.connect(self._open_custom_icons_folder)

        # 5. Сбросить иконку
        act_reset = menu.addAction(f"🗑️ {t('deck.editor.menu.icon.reset_icon')}")
        act_reset.triggered.connect(self._reset_icon)

        # Выравнивание меню под кнопкой btn_menu
        btn_pos = self.btn_menu.mapToGlobal(QPoint(0, self.btn_menu.height()))
        menu_hint = menu.sizeHint()
        target_x = btn_pos.x() + self.btn_menu.width() - menu_hint.width()
        target_y = btn_pos.y() + 2
        self._context_menu = menu
        menu.popup(QPoint(target_x, target_y))

    def _choose_icon_from_file(self) -> None:
        """Открывает диалог выбора файла и сохраняет его в пользовательскую папку."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("deck.editor.menu.icon.set_from_file"),
            "",
            t("deck.editor.dialog.icon_library.files_filter"),
        )
        if file_path:
            try:
                from modules.deck.editor.icon_catalog import IconCatalog
                saved_path = IconCatalog().save_custom_icon(file_path)
                self.set_icon(saved_path)
                self.icon_selected.emit(saved_path)
            except Exception as exc:
                logger.error("Failed to copy chosen icon file '%s': %s", file_path, exc)

    def _open_custom_icons_folder(self) -> None:
        """Открывает папку пользовательских иконок в проводнике ОС."""
        folder = Path("resources/deck/custom_icons").resolve()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            logger.warning("Could not open custom icons directory: %s", exc)

    def _reset_icon(self) -> None:
        """Сбрасывает текущую иконку."""
        self.set_icon("")
        self.icon_selected.emit("")

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
