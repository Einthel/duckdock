"""
Секция категории каталога действий DuckDeck (ActionCategorySection).
Включает кликабельный заголовок с шевроном (› / ⌄), сворачиваемое тело
со списком ActionItemWidget и двуязычный фильтр поиска (RU/EN).
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from modules.deck.editor.dto import ActionCategoryDTO
from modules.deck.editor.styles import CATEGORY_HEADER_HEIGHT
from modules.deck.editor.widgets.action_item import ActionItemWidget


class ActionCategoryHeader(QFrame):
    """
    Шапка категории аккордеона.
    Высота 38 px, шеврон › / ⌄ и локализованный заголовок.
    """

    clicked = Signal()

    def __init__(
        self,
        category_dto: ActionCategoryDTO,
        is_expanded: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.category_dto = category_dto

        self.setObjectName(f"categoryHeader_{category_dto.id}")
        self.setProperty("class", "ActionCategoryHeader")
        self.setProperty("expanded", "true" if is_expanded else "false")
        self.setFixedHeight(CATEGORY_HEADER_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        # Шеврон (› если свернуто, ⌄ если развернуто)
        self.lbl_chevron = QLabel("⌄" if is_expanded else "›", self)
        self.lbl_chevron.setObjectName("categoryChevron")
        self.lbl_chevron.setProperty("class", "CategoryChevron")
        self.lbl_chevron.setProperty("expanded", "true" if is_expanded else "false")
        self.lbl_chevron.setFixedWidth(14)
        self.lbl_chevron.setAlignment(Qt.AlignCenter)
        self.lbl_chevron.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.lbl_chevron, 0, Qt.AlignVCenter)

        # Заголовок категории
        self.lbl_title = QLabel(self.category_dto.get_title(), self)
        self.lbl_title.setObjectName("categoryTitle")
        self.lbl_title.setProperty("class", "CategoryTitle")
        self.lbl_title.setTextFormat(Qt.PlainText)
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.lbl_title, 1, Qt.AlignVCenter)

    def set_chevron(self, is_expanded: bool) -> None:
        """Обновляет глиф шеврона в соответствии со статусом раскрытия."""
        self.lbl_chevron.setText("⌄" if is_expanded else "›")
        self.setProperty("expanded", "true" if is_expanded else "false")
        self.lbl_chevron.setProperty("expanded", "true" if is_expanded else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.lbl_chevron.style().unpolish(self.lbl_chevron)
        self.lbl_chevron.style().polish(self.lbl_chevron)

    def retranslate_ui(self) -> None:
        """Обновляет локализованный заголовок категории."""
        self.lbl_title.setText(self.category_dto.get_title())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Клик левой кнопкой мыши по шапке переключает состояние аккордеона."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class ActionCategorySection(QFrame):
    """
    Сворачиваемая секция категории действий в аккордеоне библиотеки DuckDeck.
    Управляет списком дочерних карточек ActionItemWidget, переключением видимости
    и двуязычной фильтрацией поиска по локализованному названию и тегам keywords.
    """

    action_selected = Signal(object)
    expanded_changed = Signal(str, bool)

    def __init__(
        self,
        category_dto: ActionCategoryDTO,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.category_dto = category_dto
        self._is_expanded: bool = category_dto.is_expanded
        self._saved_expanded_state: bool = category_dto.is_expanded

        self.setObjectName(f"categorySection_{category_dto.id}")
        self.setProperty("class", "ActionCategorySection")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Шапка категории с шевроном
        self.header = ActionCategoryHeader(
            category_dto=category_dto,
            is_expanded=self._is_expanded,
            parent=self,
        )
        self.header.clicked.connect(self.toggle_expanded)
        layout.addWidget(self.header)

        # 2. Сворачиваемое тело со списком действий
        self.body_widget = QWidget(self)
        self.body_widget.setObjectName(f"categoryBody_{category_dto.id}")

        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(4, 2, 4, 4)
        self.body_layout.setSpacing(2)

        self.item_widgets: List[ActionItemWidget] = []
        for item_dto in category_dto.items:
            item_w = ActionItemWidget(item_dto=item_dto, parent=self.body_widget)
            item_w.item_clicked.connect(self.action_selected.emit)
            self.body_layout.addWidget(item_w)
            self.item_widgets.append(item_w)

        self.body_widget.setVisible(self._is_expanded)
        layout.addWidget(self.body_widget)

    @property
    def is_expanded(self) -> bool:
        """Возвращает текущее состояние раскрытия секции."""
        return self._is_expanded

    def set_expanded(self, expanded: bool) -> None:
        """Переключает видимость тела секции и обновляет шеврон."""
        self._is_expanded = expanded
        self.body_widget.setVisible(expanded)
        self.header.set_chevron(expanded)
        self.expanded_changed.emit(self.category_dto.id, expanded)

    def toggle_expanded(self) -> None:
        """Инвертирует текущее состояние раскрытия и сохраняет его для сброса фильтра."""
        new_state = not self._is_expanded
        self._saved_expanded_state = new_state
        self.set_expanded(new_state)

    def retranslate_ui(self) -> None:
        """Каскадно обновляет локализацию шапки и всех дочерних действий."""
        self.header.retranslate_ui()
        for item in self.item_widgets:
            item.retranslate_ui()

    def apply_filter(self, query: str) -> int:
        """
        Выполняет двуязычную фильтрацию действий в секции.
        Сопоставляет подстроку запроса с:
          1) Локализованным названием действия (item_dto.get_title());
          2) Идентификатором действия (item_dto.id);
          3) Двуязычными поисковыми тегами (item_dto.keywords на RU и EN);
          4) Названием самой категории.

        Возвращает количество совпавших элементов в секции.
        """
        if not query or not query.strip():
            for item in self.item_widgets:
                item.setVisible(True)
            self.setVisible(True)
            self.set_expanded(self._saved_expanded_state)
            return len(self.item_widgets)

        q = query.strip().lower()
        match_count = 0

        # Проверка совпадения по названию категории
        cat_title = self.category_dto.get_title().lower()
        cat_matched = q in cat_title or q in self.category_dto.id.lower()

        for item in self.item_widgets:
            dto = item.item_dto
            item_matched = (
                cat_matched
                or q in dto.get_title().lower()
                or q in dto.id.lower()
                or any(q in kw.lower() for kw in dto.keywords)
            )
            item.setVisible(item_matched)
            if item_matched:
                match_count += 1

        if match_count > 0:
            self.setVisible(True)
            self._is_expanded = True
            self.body_widget.setVisible(True)
            self.header.set_chevron(True)
        else:
            self.setVisible(False)
            self._is_expanded = False
            self.body_widget.setVisible(False)
            self.header.set_chevron(False)

        return match_count
