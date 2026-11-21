"""
Панель библиотеки действий DuckDeck (ActionLibraryDrawer) и аккордеон категорий (ActionAccordionWidget).
Объединяет ActionSearchBar, разделитель и скроллируемый аккордеон с поддержкой Localization-First.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.dto import ActionCategoryDTO
from modules.deck.editor.widgets.action_category import ActionCategorySection
from modules.deck.editor.widgets.search_bar import ActionSearchBar


class ActionAccordionWidget(QScrollArea):
    """
    Скроллируемый контейнер-аккордеон категорий и карточек действий.
    Поддерживает динамическую фильтрацию по поисковому запросу,
    плейсхолдер отсутствия результатов и каскадную локализацию retranslate_ui.
    """

    action_selected = Signal(object)

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
    Объединяет ActionSearchBar, горизонтальный разделитель и ActionAccordionWidget.
    """

    action_picked = Signal(object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        categories: Optional[List[ActionCategoryDTO]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("actionLibraryDrawer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Поисковая строка ActionSearchBar (52 px)
        self.search_bar = ActionSearchBar(self)
        layout.addWidget(self.search_bar)

        # 2. Тонкий горизонтальный разделитель (1 px BORDER_SURFACE_1)
        self.separator = QFrame(self)
        self.separator.setObjectName("drawerInternalSeparator")
        self.separator.setProperty("class", "DrawerInternalSeparator")
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Plain)
        self.separator.setFixedHeight(1)
        layout.addWidget(self.separator)

        # 3. Аккордеон библиотеки действий (растягиваемый QScrollArea)
        self.accordion = ActionAccordionWidget(self)
        layout.addWidget(self.accordion, 1)

        # Подключение внутренних сигналов
        self.search_bar.search_changed.connect(self.accordion.filter_actions)
        self.accordion.action_selected.connect(self.action_picked.emit)

        # Заполнение каталога, если передан начальный список
        if categories is not None:
            self.populate_actions(categories)

    def populate_actions(self, categories: List[ActionCategoryDTO]) -> None:
        """Заполняет каталог действий структурой категорий."""
        self.accordion.load_categories(categories)

    def retranslate_ui(self) -> None:
        """Каскадно обновляет локализацию поисковой строки и аккордеона."""
        self.search_bar.retranslate_ui()
        self.accordion.retranslate_ui()
