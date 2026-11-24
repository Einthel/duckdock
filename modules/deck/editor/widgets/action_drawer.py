"""
Панель библиотеки действий DuckDeck (ActionLibraryDrawer) и аккордеон категорий (ActionAccordionWidget).
Объединяет ActionSearchBar, разделитель и скроллируемый аккордеон с поддержкой Localization-First.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.custom_library import CustomLibraryStorage
from modules.deck.editor.dto import ActionCategoryDTO
from modules.deck.editor.styles import SEARCH_BAR_HEIGHT
from modules.deck.editor.widgets.action_category import ActionCategorySection
from modules.deck.editor.widgets.custom_library_dialogs import CreateTabDialog
from modules.deck.editor.widgets.search_bar import ActionSearchBar


class ActionAccordionWidget(QScrollArea):
    """
    Скроллируемый контейнер-аккордеон категорий и карточек действий.
    Поддерживает динамическую фильтрацию по поисковому запросу,
    плейсхолдер отсутствия результатов и каскадную локализацию retranslate_ui.
    """

    action_selected = Signal(object)
    rename_tab_requested = Signal(str)
    delete_tab_requested = Signal(str)
    rename_item_requested = Signal(str)
    delete_item_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("actionAccordionWidget")
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.sections: List[ActionCategorySection] = []
        self._last_query: str = ""

        # Внутренний контейнер скролла
        self.content_widget = QWidget(self)
        self.content_widget.setObjectName("actionAccordionContent")

        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(2)
        self.content_layout.setAlignment(Qt.AlignTop)

        # Плейсхолдер при отсутствии результатов поиска
        self.lbl_empty = QLabel(self.content_widget)
        self.lbl_empty.setObjectName("lblSearchEmptyPlaceholder")
        self.lbl_empty.setProperty("class", "SearchEmptyPlaceholder")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setWordWrap(True)
        self.lbl_empty.hide()
        self.content_layout.addWidget(self.lbl_empty)

        self.setWidget(self.content_widget)

    def load_categories(self, categories: List[ActionCategoryDTO]) -> None:
        """
        Заполняет аккордеон переданным списком категорий DTO.
        Очищает предыдущие секции и пересоздает иерархию виджетов.
        """
        # Очистка предыдущих секций
        for section in self.sections:
            self.content_layout.removeWidget(section)
            section.setParent(None)
            section.deleteLater()
        self.sections.clear()

        # Удаление старых спейсеров в конце
        while self.content_layout.count() > 1:  # оставляем lbl_empty
            item = self.content_layout.takeAt(1)
            w = item.widget()
            if w is not None and w != self.lbl_empty:
                w.deleteLater()

        # Создание и добавление новых секций
        for cat_dto in categories:
            section = ActionCategorySection(category_dto=cat_dto, parent=self.content_widget)
            section.action_selected.connect(self.action_selected.emit)
            section.rename_tab_requested.connect(self.rename_tab_requested.emit)
            section.delete_tab_requested.connect(self.delete_tab_requested.emit)
            section.rename_item_requested.connect(self.rename_item_requested.emit)
            section.delete_item_requested.connect(self.delete_item_requested.emit)
            self.content_layout.addWidget(section)
            self.sections.append(section)

        # Эластичный спейсер для прижатия секций к верхнему краю
        self.content_layout.addStretch(1)

        # Применяем фильтр, если ранее был задан поисковый запрос
        if self._last_query:
            self.filter_actions(self._last_query)

    def filter_actions(self, query: str) -> int:
        """
        Фильтрует действия во всех секциях аккордеона.
        Если совпадений нет — показывает локализованный плейсхолдер.
        """
        self._last_query = query
        total_matches = 0

        for section in self.sections:
            total_matches += section.apply_filter(query)

        if total_matches == 0 and bool(query.strip()):
            self.lbl_empty.setText(t("deck.editor.drawer.no_results", query=query.strip()))
            self.lbl_empty.show()
        else:
            self.lbl_empty.hide()

        return total_matches

    def retranslate_ui(self) -> None:
        """
        Каскадно обновляет локализацию всех секций категорий и плейсхолдера поиска.
        """
        for section in self.sections:
            section.retranslate_ui()

        if self.lbl_empty.isVisible() and bool(self._last_query.strip()):
            self.lbl_empty.setText(
                t("deck.editor.drawer.no_results", query=self._last_query.strip())
            )


class ActionLibraryDrawer(QWidget):
    """
    Правая панель каталога действий редактора DuckDeck (30% сплиттера).
    Объединяет ActionSearchBar, кнопку '+ Вкладка', горизонтальный разделитель и ActionAccordionWidget.
    """

    action_picked = Signal(object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        categories: Optional[List[ActionCategoryDTO]] = None,
        custom_storage: Optional[CustomLibraryStorage] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("actionLibraryDrawer")
        self.setFocusPolicy(Qt.NoFocus)
        self.custom_storage: CustomLibraryStorage = custom_storage or CustomLibraryStorage()
        self._explicit_categories: Optional[List[ActionCategoryDTO]] = categories

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Шапка панели: Поисковая строка + кнопка "+ Вкладка"
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        self.search_bar = ActionSearchBar(self)
        header_row.addWidget(self.search_bar, 1)

        self.btn_add_tab = QPushButton(t("deck.editor.drawer.custom.add_tab"), self)
        self.btn_add_tab.setObjectName("btnAddTab")
        self.btn_add_tab.setProperty("class", "DrawerAddTabButton")
        self.btn_add_tab.setFixedHeight(SEARCH_BAR_HEIGHT)
        self.btn_add_tab.setCursor(Qt.PointingHandCursor)
        self.btn_add_tab.setFocusPolicy(Qt.NoFocus)
        self.btn_add_tab.setToolTip(t("deck.editor.drawer.custom.add_tab_tooltip"))
        self.btn_add_tab.clicked.connect(self._on_add_tab_clicked)
        header_row.addWidget(self.btn_add_tab, 0, Qt.AlignVCenter)

        layout.addLayout(header_row)

        # 2. Тонкий горизонтальный разделитель (1 px BORDER_SURFACE_1)
        self.separator = QFrame(self)
        self.separator.setObjectName("drawerInternalSeparator")
        self.separator.setProperty("class", "DrawerInternalSeparator")
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Plain)
        self.separator.setFixedHeight(1)
        self.separator.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.separator)

        # 3. Аккордеон библиотеки действий (растягиваемый QScrollArea)
        self.accordion = ActionAccordionWidget(self)
        self.accordion.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.accordion, 1)

        # Подключение внутренних сигналов
        self.search_bar.search_changed.connect(self.accordion.filter_actions)
        self.accordion.action_selected.connect(self.action_picked.emit)
        self.accordion.rename_tab_requested.connect(self._on_rename_tab_requested)
        self.accordion.delete_tab_requested.connect(self._on_delete_tab_requested)
        self.accordion.rename_item_requested.connect(self._on_rename_item_requested)
        self.accordion.delete_item_requested.connect(self._on_delete_item_requested)

        # Заполнение каталога
        if categories is not None:
            self.populate_actions(categories)
        else:
            self.reload_library()

    def populate_actions(self, categories: List[ActionCategoryDTO]) -> None:
        """Заполняет каталог действий структурой категорий."""
        self.accordion.load_categories(categories)

    def load_presets_registry(self) -> None:
        """Загружает категории и пресеты из ActionPresetsRegistry (и пользовательские вкладки)."""
        self.reload_library()

    def reload_library(self) -> None:
        """
        Перезагружает библиотеку: объединяет пользовательские вкладки (CustomLibraryStorage)
        и системные категории (ActionPresetsRegistry), сохраняя состояние раскрытия и поиск.
        """
        from modules.deck.presets import ActionPresetsRegistry

        expanded_map = {
            sec.category_dto.id: sec.is_expanded for sec in self.accordion.sections
        }
        current_query = self.search_bar.get_query()

        custom_cats = self.custom_storage.to_categories_dto()
        system_cats = ActionPresetsRegistry.get_categories_dto()
        all_cats = custom_cats + system_cats

        for cat in all_cats:
            if cat.id in expanded_map:
                cat.is_expanded = expanded_map[cat.id]

        self.populate_actions(all_cats)
        if current_query.strip():
            self.accordion.filter_actions(current_query)

    def _on_add_tab_clicked(self) -> None:
        """Открывает компактный диалог создания пользовательской вкладки."""
        dlg = CreateTabDialog(self.window())
        if dlg.exec() == QDialog.Accepted:
            self.custom_storage.create_tab(dlg.get_tab_title(), dlg.get_tab_icon())
            self.reload_library()

    def _on_rename_tab_requested(self, tab_id: str) -> None:
        """Запрашивает новое название для пользовательской вкладки и обновляет библиотеку."""
        current = next((tb.title for tb in self.custom_storage.list_tabs() if tb.id == tab_id), "")
        new_title, ok = QInputDialog.getText(
            self.window(),
            t("deck.editor.drawer.custom.rename_tab"),
            t("deck.editor.drawer.custom.rename_tab_prompt"),
            text=current,
        )
        if ok and new_title.strip():
            if self.custom_storage.rename_tab(tab_id, new_title.strip()):
                self.reload_library()

    def _on_delete_tab_requested(self, tab_id: str) -> None:
        """Подтверждает и удаляет пользовательскую вкладку со всеми её кнопками."""
        tab_title = next((tb.title for tb in self.custom_storage.list_tabs() if tb.id == tab_id), tab_id)
        reply = QMessageBox.question(
            self.window(),
            t("deck.editor.drawer.custom.delete_tab"),
            t("deck.editor.drawer.custom.delete_tab_confirm", title=tab_title),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self.custom_storage.delete_tab(tab_id):
                self.reload_library()

    def _on_rename_item_requested(self, item_id: str) -> None:
        """Запрашивает новое название для сохранённой пользовательской кнопки."""
        item = self.custom_storage.get_item(item_id)
        current = item.title if item else ""
        new_title, ok = QInputDialog.getText(
            self.window(),
            t("deck.editor.drawer.custom.rename_item"),
            t("deck.editor.drawer.custom.rename_item_prompt"),
            text=current,
        )
        if ok and new_title.strip():
            if self.custom_storage.rename_item(item_id, new_title.strip()):
                self.reload_library()

    def _on_delete_item_requested(self, item_id: str) -> None:
        """Удаляет сохранённую кнопку из пользовательской библиотеки."""
        if self.custom_storage.delete_item(item_id):
            self.reload_library()

    def retranslate_ui(self) -> None:
        """Каскадно обновляет локализацию поисковой строки, кнопки вкладки и аккордеона."""
        self.btn_add_tab.setText(t("deck.editor.drawer.custom.add_tab"))
        self.btn_add_tab.setToolTip(t("deck.editor.drawer.custom.add_tab_tooltip"))
        self.search_bar.retranslate_ui()
        self.accordion.retranslate_ui()
