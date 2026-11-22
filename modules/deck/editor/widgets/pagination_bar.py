"""
Панель пагинации страниц DuckDeck Editor (PageNavigationBar).
Высота 36 px, центрирование кнопок Home (⭐), 1..N (минимум 1 страница), Add (+),
поддержка тултипов с локализацией retranslate_ui(), индикация активной страницы
и контекстное меню ПКМ (переименовать, дублировать, очистить, удалить).
"""
from __future__ import annotations

import logging
from typing import List, Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.styles import (
    PAGE_NAV_BTN_SIZE,
    PAGINATION_SLOT_HEIGHT,
)

logger = logging.getLogger(__name__)


class PageNavigationBar(QFrame):
    """
    Панель пагинации страниц холста DuckDeck (высота 36 px).
    - Кнопка Home (⭐): переход на первую страницу.
    - Кнопки страниц 1..N: выбор активной страницы (минимум 1).
    - Кнопка Add (+): запрос создания новой страницы.
    - Контекстное меню ПКМ по иконке страницы:
        * Переименовать страницу
        * Дублировать страницу
        * Очистить страницу
        * Удалить страницу (недоступно, если осталась всего 1 страница)
    - Сигналы:
        * page_changed(int)
        * add_page_requested()
        * rename_page_requested(int)
        * duplicate_page_requested(int)
        * clear_page_requested(int)
        * delete_page_requested(int)
    """

    page_changed = Signal(int)
    add_page_requested = Signal()
    rename_page_requested = Signal(int)
    duplicate_page_requested = Signal(int)
    clear_page_requested = Signal(int)
    delete_page_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_page = 1
        self.page_buttons: List[QPushButton] = []

        self.setObjectName("pageNavigationBar")
        self.setFixedHeight(PAGINATION_SLOT_HEIGHT)
        self.setFocusPolicy(Qt.NoFocus)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._layout.setAlignment(Qt.AlignCenter)

        self._build_ui()
        self.retranslate_ui()

    def _build_ui(self) -> None:
        # Кнопка Home (⭐)
        self.btn_home = QPushButton("⭐", self)
        self.btn_home.setObjectName("btnPageHome")
        self.btn_home.setFixedSize(PAGE_NAV_BTN_SIZE, PAGE_NAV_BTN_SIZE)
        self.btn_home.setCursor(Qt.PointingHandCursor)
        self.btn_home.setFocusPolicy(Qt.NoFocus)
        self.btn_home.setProperty("class", "PageNavButton")
        self.btn_home.clicked.connect(lambda: self._on_page_clicked(1))
        self.btn_home.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_home.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(1, self.btn_home.mapToGlobal(pos))
        )
        self._layout.addWidget(self.btn_home)

        # Начальная кнопка: минимум 1 страница
        self._create_page_button(1)

        # Кнопка Add (+)
        self.btn_add = QPushButton("+", self)
        self.btn_add.setObjectName("btnPageAdd")
        self.btn_add.setFixedSize(PAGE_NAV_BTN_SIZE, PAGE_NAV_BTN_SIZE)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFocusPolicy(Qt.NoFocus)
        self.btn_add.setProperty("class", "PageNavButton")
        self.btn_add.clicked.connect(self.add_page_requested.emit)
        self._layout.addWidget(self.btn_add)

    def _create_page_button(self, page_idx: int) -> QPushButton:
        """Создает и регистрирует кнопку страницы с привязкой сигналов и контекстного меню."""
        btn = QPushButton(str(page_idx), self)
        btn.setObjectName(f"btnPage_{page_idx}")
        btn.setFixedSize(PAGE_NAV_BTN_SIZE, PAGE_NAV_BTN_SIZE)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setProperty("class", "PageNavButton")
        btn.setProperty("active", "true" if page_idx == self._current_page else "false")
        btn.clicked.connect(lambda checked=False, p=page_idx: self._on_page_clicked(p))
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, p=page_idx: self._show_context_menu(p, btn.mapToGlobal(pos))
        )
        btn.setToolTip(t("deck.editor.canvas.pagination.page_tooltip", number=page_idx))

        # Добавляем перед кнопкой Add (+), если она уже в разметке
        if hasattr(self, "btn_add") and self.btn_add in self.children():
            self._layout.insertWidget(self._layout.count() - 1, btn)
        else:
            self._layout.addWidget(btn)

        self.page_buttons.append(btn)
        return btn

    def add_page_button(self) -> int:
        """
        Динамически добавляет новую кнопку страницы (2, 3...)
        и возвращает ее порядковый номер.
        """
        new_page_idx = len(self.page_buttons) + 1
        self._create_page_button(new_page_idx)
        return new_page_idx

    def set_page_count(self, count: int) -> None:
        """Гарантирует отображение точного количества страниц (минимум 1)."""
        target_count = max(1, count)
        # Добавляем недостающие кнопки
        while len(self.page_buttons) < target_count:
            self.add_page_button()
        # Удаляем лишние кнопки с конца
        while len(self.page_buttons) > target_count:
            btn = self.page_buttons.pop()
            self._layout.removeWidget(btn)
            btn.setParent(None)
            btn.deleteLater()

        if self._current_page > len(self.page_buttons):
            self.set_current_page(len(self.page_buttons))

    def remove_page_button(self, page_idx: int) -> None:
        """Удаляет кнопку страницы и перенумеровывает оставшиеся (минимум 1 страница)."""
        if len(self.page_buttons) <= 1:
            return  # Единственную страницу удалить нельзя!
        if not (1 <= page_idx <= len(self.page_buttons)):
            return

        btn = self.page_buttons.pop(page_idx - 1)
        self._layout.removeWidget(btn)
        btn.setParent(None)
        btn.deleteLater()

        # Перенумеровываем и перепривязываем оставшиеся кнопки 1..N
        for idx, b in enumerate(self.page_buttons, start=1):
            b.setText(str(idx))
            b.setObjectName(f"btnPage_{idx}")
            b.setToolTip(t("deck.editor.canvas.pagination.page_tooltip", number=idx))
            try:
                b.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            b.clicked.connect(lambda checked=False, p=idx: self._on_page_clicked(p))
            try:
                b.customContextMenuRequested.disconnect()
            except (RuntimeError, TypeError):
                pass
            b.customContextMenuRequested.connect(
                lambda pos, p=idx, target_btn=b: self._show_context_menu(p, target_btn.mapToGlobal(pos))
            )

        if self._current_page > len(self.page_buttons):
            self.set_current_page(len(self.page_buttons))
        else:
            self.set_current_page(self._current_page)

    def _show_context_menu(self, page_index: int, global_pos: QPoint) -> None:
        """
        Отображает контекстное меню для указанной страницы:
        - Переименовать страницу
        - Дублировать страницу
        - Очистить страницу
        - Удалить страницу (заблокировано, если осталась 1 страница)
        """
        menu = QMenu(self)
        menu.setObjectName("pageContextMenu")

        rename_action = menu.addAction(t("deck.editor.canvas.pagination.context_menu_rename"))
        duplicate_action = menu.addAction(t("deck.editor.canvas.pagination.context_menu_duplicate"))
        clear_action = menu.addAction(t("deck.editor.canvas.pagination.context_menu_clear"))
        menu.addSeparator()

        delete_action = menu.addAction(t("deck.editor.canvas.pagination.context_menu_delete"))
        # Если страница единственная, ее нельзя удалить (только очистить)
        if len(self.page_buttons) <= 1:
            delete_action.setEnabled(False)

        selected = menu.exec(global_pos)
        if selected == rename_action:
            self.rename_page_requested.emit(page_index)
        elif selected == duplicate_action:
            self.duplicate_page_requested.emit(page_index)
        elif selected == clear_action:
            self.clear_page_requested.emit(page_index)
        elif selected == delete_action:
            self.delete_page_requested.emit(page_index)

    def _on_page_clicked(self, page_index: int) -> None:
        """
        Обработчик нажатия на кнопку страницы: активирует страницу и эмитирует page_changed.
        """
        self.set_current_page(page_index)
        self.page_changed.emit(page_index)

    def set_current_page(self, page_index: int) -> None:
        """
        Задает активную страницу (1..N) и обновляет визуальное состояние кнопок.
        """
        self._current_page = page_index
        for idx, btn in enumerate(self.page_buttons, start=1):
            is_active = (idx == page_index)
            val_str = "true" if is_active else "false"
            if btn.property("active") != val_str:
                btn.setProperty("active", val_str)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.update()

    def get_current_page(self) -> int:
        """
        Возвращает номер текущей активной страницы (1..N).
        """
        return self._current_page

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованные подсказки кнопок Home, Add и страниц 1..N.
        """
        self.btn_home.setToolTip(t("deck.editor.canvas.pagination.home_tooltip"))
        self.btn_add.setToolTip(t("deck.editor.canvas.pagination.add_tooltip"))
        for idx, btn in enumerate(self.page_buttons, start=1):
            btn.setToolTip(t("deck.editor.canvas.pagination.page_tooltip", number=idx))
