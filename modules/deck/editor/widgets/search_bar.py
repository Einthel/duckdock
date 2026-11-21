"""
Компонент поисковой строки каталога действий DuckDeck (ActionSearchBar).
Включает поле ввода с инлайн-лупой, микро-кнопку очистки и служебную кнопку вида с поддержкой i18n.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.styles import SEARCH_BAR_HEIGHT, SEARCH_SLOT_HEIGHT


class ActionSearchBar(QFrame):
    """
    Поисковая строка каталога действий библиотеки DuckDeck.
    Содержит поле ввода QLineEdit со встроенной лупой и кнопкой очистки ✕,
    а также кнопку переключения вида ☰.
    """

    search_changed = Signal(str)
    view_options_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("actionSearchBar")
        self.setFixedHeight(SEARCH_SLOT_HEIGHT)

        # Главный горизонтальный лэйаут
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(8)

        # Поле ввода поиска
        self.search_input = QLineEdit(self)
        self.search_input.setObjectName("actionSearchInput")
        self.search_input.setProperty("class", "ActionSearchInput")
        self.search_input.setFixedHeight(SEARCH_BAR_HEIGHT)

        # Внутренний лэйаут поля ввода для инлайн-элементов (лупа слева, крестик справа)
        input_layout = QHBoxLayout(self.search_input)
        input_layout.setContentsMargins(8, 0, 6, 0)
        input_layout.setSpacing(4)

        # Инлайн-иконка лупы
        self.lbl_search_icon = QLabel("🔍", self.search_input)
        self.lbl_search_icon.setObjectName("searchIconLabel")
        self.lbl_search_icon.setProperty("class", "SearchIconLabel")
        self.lbl_search_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        input_layout.addWidget(self.lbl_search_icon, 0, Qt.AlignLeft | Qt.AlignVCenter)

        input_layout.addStretch(1)

        # Микро-кнопка очистки текста
        self.btn_clear = QPushButton("✕", self.search_input)
        self.btn_clear.setObjectName("searchClearButton")
        self.btn_clear.setProperty("class", "SearchClearButton")
        self.btn_clear.setFixedSize(18, 18)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.hide()
        input_layout.addWidget(self.btn_clear, 0, Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self.search_input, 1)

        # Служебная кнопка опций отображения (вид меню ☰)
        self.btn_view_options = QPushButton("☰", self)
        self.btn_view_options.setObjectName("actionViewButton")
        self.btn_view_options.setProperty("class", "ActionViewButton")
        self.btn_view_options.setFixedSize(32, 32)
        self.btn_view_options.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_view_options, 0, Qt.AlignVCenter)

        # Подключение внутренних сигналов
        self.search_input.textChanged.connect(self._on_text_changed)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        self.btn_view_options.clicked.connect(self.view_options_clicked.emit)

        # Первичная инициализация текстов локализации
        self.retranslate_ui()

    def _on_text_changed(self, text: str) -> None:
        """Обработчик изменения текста в поле ввода."""
        self.btn_clear.setVisible(bool(text))
        self.search_changed.emit(text)

    def _on_clear_clicked(self) -> None:
        """Обработчик клика по кнопке очистки: сброс текста и возврат фокуса."""
        self.clear_query()
        self.search_input.setFocus()

    def get_query(self) -> str:
        """Возвращает текущий текст поискового запроса."""
        return self.search_input.text()

    def clear_query(self) -> None:
        """Очищает строку поиска и скрывает кнопку очистки."""
        self.search_input.clear()
        self.btn_clear.hide()

    def set_focus(self) -> None:
        """Устанавливает клавиатурный фокус в поле ввода поиска."""
        self.search_input.setFocus()

    def retranslate_ui(self) -> None:
        """Обновляет локализованные строки плейсхолдера и тултипов."""
        self.search_input.setPlaceholderText(t("deck.editor.drawer.search_placeholder"))
        self.btn_view_options.setToolTip(t("deck.editor.drawer.view_options_tooltip"))
