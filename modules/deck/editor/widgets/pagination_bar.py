"""
Панель пагинации страниц DuckDeck Editor (PageNavigationBar).
Высота 36 px, центрирование кнопок Home (⭐), 1..8, Add (+),
поддержка тултипов с локализацией retranslate_ui() и индикация активной страницы.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
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
    - Кнопки страниц 1..8: выбор активной страницы.
    - Кнопка Add (+): запрос создания новой страницы.
    - Сигналы: page_changed(int), add_page_requested().
    - Реактивное обновление подсказок: retranslate_ui().
    """

    page_changed = Signal(int)
    add_page_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_page = 1
        self.page_buttons: List[QPushButton] = []

        self.setObjectName("pageNavigationBar")
        self.setFixedHeight(PAGINATION_SLOT_HEIGHT)
        self.setFocusPolicy(Qt.NoFocus)

        self._build_ui()
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # Кнопка Home (⭐)
        self.btn_home = QPushButton("⭐", self)
        self.btn_home.setObjectName("btnPageHome")
        self.btn_home.setFixedSize(PAGE_NAV_BTN_SIZE, PAGE_NAV_BTN_SIZE)
        self.btn_home.setCursor(Qt.PointingHandCursor)
        self.btn_home.setFocusPolicy(Qt.NoFocus)
        self.btn_home.setProperty("class", "PageNavButton")
        self.btn_home.clicked.connect(lambda: self._on_page_clicked(1))
        layout.addWidget(self.btn_home)

        # Группа кнопок 1..8
        for page_idx in range(1, 9):
            btn = QPushButton(str(page_idx), self)
            btn.setObjectName(f"btnPage_{page_idx}")
            btn.setFixedSize(PAGE_NAV_BTN_SIZE, PAGE_NAV_BTN_SIZE)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setProperty("class", "PageNavButton")
            btn.setProperty("active", "true" if page_idx == 1 else "false")
            btn.clicked.connect(lambda checked=False, p=page_idx: self._on_page_clicked(p))
            layout.addWidget(btn)
            self.page_buttons.append(btn)

        # Кнопка Add (+)
        self.btn_add = QPushButton("+", self)
        self.btn_add.setObjectName("btnPageAdd")
        self.btn_add.setFixedSize(PAGE_NAV_BTN_SIZE, PAGE_NAV_BTN_SIZE)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFocusPolicy(Qt.NoFocus)
        self.btn_add.setProperty("class", "PageNavButton")
        self.btn_add.clicked.connect(self.add_page_requested.emit)
        layout.addWidget(self.btn_add)

    def _on_page_clicked(self, page_index: int) -> None:
        """
        Обработчик нажатия на кнопку страницы: активирует страницу и эмитирует page_changed.
        """
        self.set_current_page(page_index)
        self.page_changed.emit(page_index)

    def set_current_page(self, page_index: int) -> None:
        """
        Задает активную страницу (1..8) и обновляет визуальное состояние кнопок.
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
        Возвращает номер текущей активной страницы (1..8).
        """
        return self._current_page

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованные подсказки кнопок Home и Add.
        """
        self.btn_home.setToolTip(t("deck.editor.canvas.pagination.home_tooltip"))
        self.btn_add.setToolTip(t("deck.editor.canvas.pagination.add_tooltip"))
