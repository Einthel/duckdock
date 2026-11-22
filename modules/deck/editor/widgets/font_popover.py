"""
Всплывающее меню настройки типографики кнопки DuckDeck (FontCustomizationPopover).
Реализует всплывающее окно (Qt.Popup | Qt.FramelessWindowHint) в стиле Dark Obsidian v2:
  - Выбор размера шрифта (9px, 11px, 13px, 15px)
  - Выравнивание текста (Снизу, По центру, Сверху)
  - Цветовая палитра текста (5 неоновых чипов + сброс)
  - Флаг скрытия заголовка (режим чистой иконки)
Строго соблюдает инвариант Stealth Focus (Qt.WA_ShowWithoutActivating, Qt.NoFocus)
и 100% локализацию (In-place Retranslate Invariant).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t

logger = logging.getLogger("duckdock.deck.editor.font_popover")

TEXT_COLORS = [
    "#f8fafc",  # Белый (Slate 50)
    "#94a3b8",  # Серый (Slate 400)
    "#38bdf8",  # Неоновый голубой (Cyan)
    "#f59e0b",  # Янтарный (Amber)
    "#10b981",  # Изумрудный (Emerald)
]

FONT_SIZES = [9, 11, 13, 15]

FONT_POPOVER_QSS = """
QWidget#fontCustomizationPopover {
    background-color: #121824;
    border: 1px solid #334155;
    border-radius: 10px;
}

QLabel.PopoverHeader {
    color: #f8fafc;
    font-size: 12px;
    font-weight: bold;
}

QLabel.PopoverSectionLabel {
    color: #94a3b8;
    font-size: 11px;
}

QPushButton.PopoverOptionButton {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 5px;
    font-size: 11px;
    padding: 3px 6px;
}

QPushButton.PopoverOptionButton:hover {
    background-color: #334155;
    color: #f8fafc;
    border-color: #475569;
}

QPushButton.PopoverOptionButton[active="true"] {
    background-color: #0369a1;
    color: #ffffff;
    border: 1px solid #38bdf8;
    font-weight: bold;
}

QPushButton.PopoverColorSwatch {
    border-radius: 9px;
    border: 1px solid #334155;
}

QPushButton.PopoverColorSwatch[active="true"] {
    border: 2px solid #ffffff;
}

QPushButton.PopoverResetButton {
    background-color: transparent;
    color: #64748b;
    border: 1px dashed #475569;
    border-radius: 5px;
    font-size: 10px;
    padding: 2px 6px;
}

QPushButton.PopoverResetButton:hover {
    color: #cbd5e1;
    border-color: #94a3b8;
}

QCheckBox.PopoverCheckBox {
    color: #cbd5e1;
    font-size: 11px;
    spacing: 6px;
}

QCheckBox.PopoverCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #475569;
    background-color: #1e293b;
}

QCheckBox.PopoverCheckBox::indicator:checked {
    background-color: #0284c7;
    border-color: #38bdf8;
}
"""


class FontCustomizationPopover(QWidget):
    """
    Всплывающее меню настройки типографики DuckDeck.
    Инварианты:
      - Qt.Popup | Qt.FramelessWindowHint, Qt.WA_ShowWithoutActivating
      - Эмиссия font_changed(dict)
      - Автопозиционирование относительно кнопки-якоря
    """

    font_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("fontCustomizationPopover")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(260, 240)
        self.setStyleSheet(FONT_POPOVER_QSS)

        # Мягкая тень окна
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

        self._font_size: int = 11
        self._font_color: str = "#d4d4d8"
        self._text_alignment: str = "bottom"
        self._hide_title: bool = False

        self._size_buttons: dict[int, QPushButton] = {}
        self._align_buttons: dict[str, QPushButton] = {}
        self._color_buttons: dict[str, QPushButton] = {}

        self._setup_ui()
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # Заголовок поповера
        self.lbl_title = QLabel(self)
        self.lbl_title.setProperty("class", "PopoverHeader")
        root_layout.addWidget(self.lbl_title)

        sep1 = QFrame(self)
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("border: none; background-color: #1e293b; height: 1px;")
        root_layout.addWidget(sep1)

        # Секция 1: Размер шрифта
        size_layout = QHBoxLayout()
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(4)

        self.lbl_size = QLabel(self)
        self.lbl_size.setProperty("class", "PopoverSectionLabel")
        self.lbl_size.setFixedWidth(70)
        size_layout.addWidget(self.lbl_size)

        self.size_group = QButtonGroup(self)
        self.size_group.setExclusive(True)

        for sz in FONT_SIZES:
            btn = QPushButton(f"{sz}px", self)
            btn.setProperty("class", "PopoverOptionButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, s=sz: self._on_size_clicked(s))
            self.size_group.addButton(btn)
            size_layout.addWidget(btn)
            self._size_buttons[sz] = btn

        root_layout.addLayout(size_layout)

        # Секция 2: Выравнивание
        align_layout = QHBoxLayout()
        align_layout.setContentsMargins(0, 0, 0, 0)
        align_layout.setSpacing(4)

        self.lbl_align = QLabel(self)
        self.lbl_align.setProperty("class", "PopoverSectionLabel")
        self.lbl_align.setFixedWidth(70)
        align_layout.addWidget(self.lbl_align)

        self.align_group = QButtonGroup(self)
        self.align_group.setExclusive(True)

        align_configs = [
            ("bottom", "deck.editor.font_popover.align_bottom", "⬇"),
            ("center", "deck.editor.font_popover.align_center", "⬌"),
            ("top", "deck.editor.font_popover.align_top", "⬆"),
        ]

        for align_key, loc_key, glyph in align_configs:
            btn = QPushButton(glyph, self)
            btn.setProperty("class", "PopoverOptionButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=align_key: self._on_align_clicked(k))
            self.align_group.addButton(btn)
            align_layout.addWidget(btn)
            self._align_buttons[align_key] = btn

        root_layout.addLayout(align_layout)

        # Секция 3: Цвет текста
        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(6)

        self.lbl_color = QLabel(self)
        self.lbl_color.setProperty("class", "PopoverSectionLabel")
        self.lbl_color.setFixedWidth(70)
        color_layout.addWidget(self.lbl_color)

        for hex_col in TEXT_COLORS:
            btn = QPushButton(self)
            btn.setProperty("class", "PopoverColorSwatch")
            btn.setFixedSize(18, 18)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {hex_col}; border-radius: 9px;")
            btn.clicked.connect(lambda checked=False, c=hex_col: self._on_color_clicked(c))
            color_layout.addWidget(btn)
            self._color_buttons[hex_col] = btn

        self.btn_reset_color = QPushButton(self)
        self.btn_reset_color.setProperty("class", "PopoverResetButton")
        self.btn_reset_color.setCursor(Qt.PointingHandCursor)
        self.btn_reset_color.clicked.connect(lambda: self._on_color_clicked("#d4d4d8"))
        color_layout.addWidget(self.btn_reset_color)
        color_layout.addStretch(1)

        root_layout.addLayout(color_layout)

        # Секция 4: Скрытие заголовка
        self.chk_hide_title = QCheckBox(self)
        self.chk_hide_title.setProperty("class", "PopoverCheckBox")
        self.chk_hide_title.setCursor(Qt.PointingHandCursor)
        self.chk_hide_title.toggled.connect(self._on_hide_title_toggled)
        root_layout.addWidget(self.chk_hide_title)

        root_layout.addStretch(1)

    def set_current_settings(
        self,
        font_size: int = 11,
        font_color: str = "#d4d4d8",
        text_alignment: str = "bottom",
        hide_title: bool = False,
    ) -> None:
        """Синхронизирует текущее состояние элементов управления с DTO без эмиссии сигналов."""
        self._font_size = font_size if font_size in FONT_SIZES else 11
        self._font_color = font_color or "#d4d4d8"
        self._text_alignment = text_alignment if text_alignment in ("bottom", "center", "top") else "bottom"
        self._hide_title = bool(hide_title)

        # Размер шрифта
        for sz, btn in self._size_buttons.items():
            btn.blockSignals(True)
            is_active = (sz == self._font_size)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.blockSignals(False)

        # Выравнивание
        for ak, btn in self._align_buttons.items():
            btn.blockSignals(True)
            is_active = (ak == self._text_alignment)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.blockSignals(False)

        # Цвет
        norm_col = self._font_color.lower().strip()
        for hex_col, btn in self._color_buttons.items():
            is_active = (hex_col.lower() == norm_col)
            btn.setProperty("active", "true" if is_active else "false")
            if is_active:
                btn.setStyleSheet(f"background-color: {hex_col}; border-radius: 9px; border: 2px solid #ffffff;")
            else:
                btn.setStyleSheet(f"background-color: {hex_col}; border-radius: 9px; border: 1px solid #334155;")

        # Скрытие заголовка
        self.chk_hide_title.blockSignals(True)
        self.chk_hide_title.setChecked(self._hide_title)
        self.chk_hide_title.blockSignals(False)

    # Псевдоним для совместимости API формы свойств
    set_state = set_current_settings

    def _on_size_clicked(self, font_size: int) -> None:
        self._font_size = font_size
        self._update_size_styles()
        self._emit_change()

    def _on_align_clicked(self, alignment: str) -> None:
        self._text_alignment = alignment
        self._update_align_styles()
        self._emit_change()

    def _on_color_clicked(self, color_hex: str) -> None:
        self._font_color = color_hex
        self._update_color_styles()
        self._emit_change()

    def _on_hide_title_toggled(self, checked: bool) -> None:
        self._hide_title = checked
        self._emit_change()

    def _update_size_styles(self) -> None:
        for sz, btn in self._size_buttons.items():
            is_active = (sz == self._font_size)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_align_styles(self) -> None:
        for ak, btn in self._align_buttons.items():
            is_active = (ak == self._text_alignment)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_color_styles(self) -> None:
        norm_col = self._font_color.lower().strip()
        for hex_col, btn in self._color_buttons.items():
            is_active = (hex_col.lower() == norm_col)
            btn.setProperty("active", "true" if is_active else "false")
            if is_active:
                btn.setStyleSheet(f"background-color: {hex_col}; border-radius: 9px; border: 2px solid #ffffff;")
            else:
                btn.setStyleSheet(f"background-color: {hex_col}; border-radius: 9px; border: 1px solid #334155;")

    def _emit_change(self) -> None:
        self.font_changed.emit({
            "font_size": self._font_size,
            "font_color": self._font_color,
            "text_alignment": self._text_alignment,
            "hide_title": self._hide_title,
        })

    def show_at_widget(self, target_widget: QWidget) -> None:
        """Позиционирует поповер относительно целевого виджета с учетом границ экрана."""
        if not target_widget:
            return

        pos = target_widget.mapToGlobal(QPoint(0, target_widget.height() + 4))
        screen = target_widget.screen()
        if screen:
            geo = screen.availableGeometry()
            if pos.x() + self.width() > geo.right():
                pos.setX(geo.right() - self.width() - 8)
            if pos.y() + self.height() > geo.bottom():
                pos.setY(target_widget.mapToGlobal(QPoint(0, -self.height() - 4)).y())

        self.move(pos)
        self.show()
        self.raise_()

    def retranslate_ui(self) -> None:
        """Обновляет локализованные строки поповера."""
        self.lbl_title.setText(t("deck.editor.font_popover.title"))
        self.lbl_size.setText(t("deck.editor.font_popover.font_size"))
        self.lbl_align.setText(t("deck.editor.font_popover.alignment"))
        self.lbl_color.setText(t("deck.editor.font_popover.text_color"))
        self.btn_reset_color.setText(t("deck.editor.font_popover.reset"))
        self.chk_hide_title.setText(t("deck.editor.font_popover.hide_title"))

        if "bottom" in self._align_buttons:
            self._align_buttons["bottom"].setToolTip(t("deck.editor.font_popover.align_bottom"))
        if "center" in self._align_buttons:
            self._align_buttons["center"].setToolTip(t("deck.editor.font_popover.align_center"))
        if "top" in self._align_buttons:
            self._align_buttons["top"].setToolTip(t("deck.editor.font_popover.align_top"))


__all__ = ["FontCustomizationPopover", "FONT_SIZES", "TEXT_COLORS"]
