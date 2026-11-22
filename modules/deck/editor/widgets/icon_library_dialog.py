"""
Модальный диалог библиотеки иконок DuckDeck (IconLibraryDialog).
Габариты 580x640 px, палитра Dark Obsidian v2, живой поиск (RU/EN),
фильтрация по категориям (Pills), сетка с масштабированием (Zoom) и предпросмотром.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.icon_catalog import (
    IconCatalog,
    IconCategoryDTO,
    IconEntryDTO,
)
from modules.deck.editor.styles import (
    BORDER_FOCUS_NEON,
    SURFACE_0_CANVAS,
    SURFACE_1_PANEL,
    SURFACE_2_CARD,
    SURFACE_3_HOVER,
    apply_editor_theme,
)

logger = logging.getLogger("duckdock.deck.editor.icon_dialog")


class IconTileWidget(QFrame):
    """
    Интерактивная карточка иконки в сетке каталога.
    Поддерживает клик (выбор), двойной клик (немедленное подтверждение),
    ховер-анимацию и отображение подсказки.
    """

    clicked = Signal(object)
    double_clicked = Signal(object)

    def __init__(
        self,
        entry: IconEntryDTO,
        pixmap: QPixmap,
        tile_size: int = 64,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.entry = entry
        self._tile_size = tile_size
        self._is_selected = False

        self.setObjectName("iconTileWidget")
        self.setProperty("class", "IconTileWidget")
        self.setFixedSize(tile_size, tile_size)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_icon = QLabel(self)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setPixmap(pixmap)
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_icon)

        # Тултип с названием и категорией
        self.setToolTip(f"{entry.name}\n({entry.category})")

    def set_selected(self, selected: bool) -> None:
        """Переключает состояние выбора тайла с обновлением стиля QSS."""
        if self._is_selected != selected:
            self._is_selected = selected
            self.setProperty("selected", "true" if selected else "false")
            self.style().unpolish(self)
            self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.entry)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.entry)
        super().mouseDoubleClickEvent(event)


class IconLibraryDialog(QDialog):
    """
    Модальный диалог выбора иконки (580x640 px).
    Включает:
      - HeaderBar: заголовок, бейдж общего количества, кнопка ✕;
      - SearchBar: живой поиск с кнопкой быстрой очистки;
      - CategoryPillsStrip: горизонтальная лента категорий с бейджами;
      - QScrollArea + QGridLayout: сетка иконок;
      - FooterBar: регулятор зума, добавление пользовательских иконок, кнопки Отмена/Выбрать.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        current_icon: str = "",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("iconLibraryDialog")
        self.setProperty("class", "IconLibraryDialog")
        self.setFixedSize(580, 640)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setModal(True)

        self.catalog = IconCatalog()
        self._current_icon: str = current_icon
        self._selected_icon: Optional[str] = current_icon if current_icon else None

        self._active_category: str = "all"
        self._search_text: str = ""
        self._zoom_size: int = 48  # Доступно: 36, 48, 60 px

        self._pill_buttons: dict[str, QPushButton] = {}
        self._tile_widgets: list[IconTileWidget] = []

        self._setup_ui()
        self._center_on_parent()
        apply_editor_theme(self)
        self.retranslate_ui()
        self._refresh_grid()

    def _setup_ui(self) -> None:
        """Построение компоновки диалога."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ----------------------------------------------------------------------
        # 1. Header Bar (48 px)
        # ----------------------------------------------------------------------
        self.header_frame = QFrame(self)
        self.header_frame.setObjectName("iconLibraryHeader")
        self.header_frame.setProperty("class", "IconLibraryHeader")
        self.header_frame.setFixedHeight(48)

        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(10)

        lbl_icon = QLabel("📚", self.header_frame)
        lbl_icon.setStyleSheet("font-size: 16px; background: transparent;")

        self.lbl_title = QLabel(self.header_frame)
        self.lbl_title.setObjectName("iconLibraryTitle")
        self.lbl_title.setProperty("class", "IconLibraryTitle")

        self.lbl_badge = QLabel("0", self.header_frame)
        self.lbl_badge.setObjectName("iconLibraryBadge")
        self.lbl_badge.setProperty("class", "IconLibraryBadge")

        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(self.lbl_title)
        header_layout.addWidget(self.lbl_badge)
        header_layout.addStretch(1)

        self.btn_close = QPushButton("✕", self.header_frame)
        self.btn_close.setObjectName("iconLibraryCloseBtn")
        self.btn_close.setProperty("class", "IconLibraryCloseBtn")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        header_layout.addWidget(self.btn_close)

        main_layout.addWidget(self.header_frame)

        # ----------------------------------------------------------------------
        # 2. Search & Filter Bar (~86 px)
        # ----------------------------------------------------------------------
        filter_container = QWidget(self)
        filter_container.setStyleSheet("background-color: transparent;")
        filter_layout = QVBoxLayout(filter_container)
        filter_layout.setContentsMargins(16, 10, 16, 8)
        filter_layout.setSpacing(8)

        # Поисковая строка
        search_box = QHBoxLayout()
        search_box.setContentsMargins(0, 0, 0, 0)
        search_box.setSpacing(6)

        self.edit_search = QLineEdit(filter_container)
        self.edit_search.setObjectName("iconSearchInput")
        self.edit_search.setProperty("class", "InspectorLineEdit")
        self.edit_search.setFixedHeight(32)
        self.edit_search.textChanged.connect(self._on_search_changed)

        self.btn_clear_search = QPushButton("✕", filter_container)
        self.btn_clear_search.setObjectName("btnIconSearchClear")
        self.btn_clear_search.setProperty("class", "TileCornerButton")
        self.btn_clear_search.setFixedSize(32, 32)
        self.btn_clear_search.setCursor(Qt.PointingHandCursor)
        self.btn_clear_search.clicked.connect(self.edit_search.clear)

        search_box.addWidget(self.edit_search, 1)
        search_box.addWidget(self.btn_clear_search)
        filter_layout.addLayout(search_box)

        # Лента категорий (Pills Strip)
        self.pills_layout = QHBoxLayout()
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(6)
        filter_layout.addLayout(self.pills_layout)

        main_layout.addWidget(filter_container)

        # ----------------------------------------------------------------------
        # 3. Icon Grid View (QScrollArea)
        # ----------------------------------------------------------------------
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("iconLibraryScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("iconLibraryScrollContent")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.lbl_empty = QLabel(self.scroll_content)
        self.lbl_empty.setObjectName("lblIconSearchEmpty")
        self.lbl_empty.setProperty("class", "SearchEmptyPlaceholder")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.hide()
        self.grid_layout.addWidget(self.lbl_empty, 0, 0, 1, 6, Qt.AlignCenter)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        # ----------------------------------------------------------------------
        # 4. Footer Action Bar (56 px)
        # ----------------------------------------------------------------------
        self.footer_frame = QFrame(self)
        self.footer_frame.setObjectName("iconLibraryFooter")
        self.footer_frame.setProperty("class", "IconLibraryFooter")
        self.footer_frame.setFixedHeight(56)

        footer_layout = QHBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(16, 8, 16, 8)
        footer_layout.setSpacing(8)

        # Зум-кнопки [-] [=] [+]
        self.btn_zoom_out = QPushButton("-", self.footer_frame)
        self.btn_zoom_out.setProperty("class", "IconZoomBtn")
        self.btn_zoom_out.setFixedSize(26, 26)
        self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_out.clicked.connect(lambda: self._set_zoom(36))

        self.btn_zoom_mid = QPushButton("=", self.footer_frame)
        self.btn_zoom_mid.setProperty("class", "IconZoomBtn")
        self.btn_zoom_mid.setFixedSize(26, 26)
        self.btn_zoom_mid.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_mid.clicked.connect(lambda: self._set_zoom(48))

        self.btn_zoom_in = QPushButton("+", self.footer_frame)
        self.btn_zoom_in.setProperty("class", "IconZoomBtn")
        self.btn_zoom_in.setFixedSize(26, 26)
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.clicked.connect(lambda: self._set_zoom(60))

        footer_layout.addWidget(self.btn_zoom_out)
        footer_layout.addWidget(self.btn_zoom_mid)
        footer_layout.addWidget(self.btn_zoom_in)

        # Ссылка "+ Добавить свои иконки..."
        self.btn_add_custom = QPushButton(self.footer_frame)
        self.btn_add_custom.setObjectName("btnAddCustomIcons")
        self.btn_add_custom.setProperty("class", "IconLibraryAddCustomBtn")
        self.btn_add_custom.setCursor(Qt.PointingHandCursor)
        self.btn_add_custom.clicked.connect(self._on_add_custom_clicked)
        footer_layout.addWidget(self.btn_add_custom)

        footer_layout.addStretch(1)

        # Кнопки Отмена и Выбрать
        self.btn_cancel = QPushButton(self.footer_frame)
        self.btn_cancel.setObjectName("iconLibraryCancelBtn")
        self.btn_cancel.setProperty("class", "IconLibraryCancelBtn")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_select = QPushButton(self.footer_frame)
        self.btn_select.setObjectName("iconLibrarySelectBtn")
        self.btn_select.setProperty("class", "IconLibrarySelectBtn")
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.clicked.connect(self.accept)
        self.btn_select.setEnabled(bool(self._selected_icon))

        footer_layout.addWidget(self.btn_cancel)
        footer_layout.addWidget(self.btn_select)

        main_layout.addWidget(self.footer_frame)

    def _center_on_parent(self) -> None:
        """Центрирует диалог относительно родительского окна."""
        parent = self.parentWidget()
        if parent:
            geo = self.frameGeometry()
            geo.moveCenter(parent.frameGeometry().center())
            self.move(geo.topLeft())

    # ==========================================================================
    # Фильтрация и обновление сетки
    # ==========================================================================

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text
        self._refresh_grid()

    def _set_category(self, category_id: str) -> None:
        self._active_category = category_id
        for cat_id, btn in self._pill_buttons.items():
            is_active = (cat_id == category_id)
            btn.setProperty("selected", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._refresh_grid()

    def _set_zoom(self, zoom_size: int) -> None:
        if self._zoom_size != zoom_size:
            self._zoom_size = zoom_size
            self._refresh_grid()

    def _on_add_custom_clicked(self) -> None:
        """Вызов диалога выбора пользовательского файла."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("deck.editor.menu.icon.set_from_file"),
            "",
            t("deck.editor.dialog.icon_library.files_filter"),
        )
        if file_path:
            try:
                saved = self.catalog.save_custom_icon(file_path)
                self._selected_icon = saved
                self._set_category("custom")
            except Exception as exc:
                logger.error("Error importing custom icon: %s", exc)

    def _refresh_grid(self) -> None:
        """Перерисовывает сетку карточек иконок по текущему фильтру."""
        # Очистка предыдущих виджетов
        for tile in self._tile_widgets:
            self.grid_layout.removeWidget(tile)
            tile.deleteLater()
        self._tile_widgets.clear()

        # Получение отфильтрованных иконок
        icons = self.catalog.get_icons(
            category=self._active_category,
            search_query=self._search_text,
        )

        # Обновление счетчика бейджа
        self.lbl_badge.setText(str(len(icons)))

        if not icons:
            self.lbl_empty.show()
            self.btn_select.setEnabled(False)
            return

        self.lbl_empty.hide()

        # Расчет количества колонок в зависимости от зума
        # 36 px -> 48px tile (10 колонок)
        # 48 px -> 64px tile (7-8 колонок)
        # 60 px -> 80px tile (6 колонок)
        tile_size = self._zoom_size + 16
        columns_count = max(4, 520 // (tile_size + 10))

        row, col = 0, 0
        for entry in icons:
            pixmap = self.catalog.cache.get_pixmap(entry.path_or_glyph, self._zoom_size)
            tile = IconTileWidget(entry, pixmap, tile_size=tile_size, parent=self.scroll_content)

            if self._selected_icon == entry.path_or_glyph:
                tile.set_selected(True)

            tile.clicked.connect(self._on_tile_clicked)
            tile.double_clicked.connect(self._on_tile_double_clicked)

            self.grid_layout.addWidget(tile, row, col)
            self._tile_widgets.append(tile)

            col += 1
            if col >= columns_count:
                col = 0
                row += 1

        self.btn_select.setEnabled(bool(self._selected_icon))

    def _on_tile_clicked(self, entry: IconEntryDTO) -> None:
        self._selected_icon = entry.path_or_glyph
        for tile in self._tile_widgets:
            tile.set_selected(tile.entry.path_or_glyph == self._selected_icon)
        self.btn_select.setEnabled(True)

    def _on_tile_double_clicked(self, entry: IconEntryDTO) -> None:
        self._selected_icon = entry.path_or_glyph
        self.accept()

    def get_selected_icon(self) -> str:
        """Возвращает строку символа или путь выбранной иконки."""
        return self._selected_icon if self._selected_icon else ""

    # ==========================================================================
    # Локализация (Localization-First & In-place Retranslate)
    # ==========================================================================

    def retranslate_ui(self) -> None:
        """Обновляет все локализованные надписи диалога."""
        self.setWindowTitle(t("deck.editor.dialog.icon_library.title"))
        self.lbl_title.setText(t("deck.editor.dialog.icon_library.title"))
        self.edit_search.setPlaceholderText(t("deck.editor.dialog.icon_library.search_placeholder"))
        self.lbl_empty.setText(t("deck.editor.dialog.icon_library.no_results"))
        self.btn_add_custom.setText(t("deck.editor.dialog.icon_library.add_custom"))
        self.btn_cancel.setText(t("deck.editor.dialog.icon_library.btn_cancel"))
        self.btn_select.setText(t("deck.editor.dialog.icon_library.btn_select"))

        zoom_tip = t("deck.editor.dialog.icon_library.zoom_tooltip")
        self.btn_zoom_out.setToolTip(f"{zoom_tip}: 36px")
        self.btn_zoom_mid.setToolTip(f"{zoom_tip}: 48px")
        self.btn_zoom_in.setToolTip(f"{zoom_tip}: 60px")

        # Пересоздание Pills категорий с сохранением активного выбора
        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._pill_buttons.clear()

        categories = self.catalog.get_categories()
        for cat in categories:
            btn = QPushButton(f"{t(cat.title_key)} ({cat.icon_count})", self)
            btn.setObjectName(f"pillCat_{cat.id}")
            btn.setProperty("class", "IconCategoryPill")
            btn.setCursor(Qt.PointingHandCursor)
            if cat.id == self._active_category:
                btn.setProperty("selected", "true")
            btn.clicked.connect(lambda checked=False, cid=cat.id: self._set_category(cid))
            self.pills_layout.addWidget(btn)
            self._pill_buttons[cat.id] = btn

        self.pills_layout.addStretch(1)
