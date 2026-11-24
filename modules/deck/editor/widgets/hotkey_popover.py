"""
Всплывающий конструктор комбинаций клавиш DuckDeck (HotkeyBuilderPopover).
Позволяет вручную выбрать модификаторы (Ctrl, Alt, Shift, Win) и любую конечную клавишу
(Tab, Esc, F1-F12, спецклавиши или символ), а также быстро выбрать системные комбинации
(Ctrl+Shift+Esc, Alt+Tab, Win+D), которые Windows перехватывает до Qt.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.styles import INPUT_HEIGHT

MODIFIER_KEYS = ["Ctrl", "Alt", "Shift", "Win"]

SPECIAL_KEYS = [
    "Tab",
    "Esc",
    "Enter",
    "Space",
    "Backspace",
    "Delete",
    "PrintScreen",
    "Insert",
    "Home",
    "End",
    "PageUp",
    "PageDown",
    "Up",
    "Down",
    "Left",
    "Right",
    *[f"F{i}" for i in range(1, 13)],
]

SYSTEM_HOTKEY_PRESETS = [
    "Ctrl+Shift+Esc",
    "Alt+Tab",
    "Win+D",
]

HOTKEY_POPOVER_QSS = """
QWidget#hotkeyBuilderPopover {
    background-color: #121824;
    border: 1px solid #334155;
    border-radius: 10px;
}

QLabel.HotkeyPopoverHeader {
    color: #f8fafc;
    font-size: 12px;
    font-weight: bold;
}

QLabel.HotkeyPopoverLabel {
    color: #94a3b8;
    font-size: 11px;
}

QPushButton.HotkeyModButton {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 8px;
}

QPushButton.HotkeyModButton:hover {
    background-color: #334155;
    color: #f8fafc;
}

QPushButton.HotkeyModButton:checked {
    background-color: #0369a1;
    color: #ffffff;
    border: 1px solid #38bdf8;
}

QPushButton.HotkeyPresetPill {
    background-color: #141924;
    color: #38bdf8;
    border: 1px solid #202a3c;
    border-radius: 5px;
    font-size: 10px;
    font-weight: 600;
    padding: 3px 7px;
}

QPushButton.HotkeyPresetPill:hover {
    background-color: #1c2940;
    border-color: #38bdf8;
    color: #ffffff;
}

QPushButton.HotkeyPopoverClearBtn {
    background-color: transparent;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 5px;
    font-size: 11px;
    padding: 4px 10px;
}

QPushButton.HotkeyPopoverClearBtn:hover {
    color: #f8fafc;
    border-color: #64748b;
}

QPushButton.HotkeyPopoverApplyBtn {
    background-color: #0078d4;
    color: #ffffff;
    border: 1px solid #0078d4;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 12px;
}

QPushButton.HotkeyPopoverApplyBtn:hover {
    background-color: #0284c7;
    border-color: #38bdf8;
}

QComboBox#comboHotkeySpecialKey {
    background-color: #141924;
    border: 1px solid #202a3c;
    border-radius: 5px;
    color: #f8fafc;
    font-size: 11px;
    padding: 2px 8px;
}

QLineEdit#editHotkeyCustomKey {
    background-color: #141924;
    border: 1px solid #202a3c;
    border-radius: 5px;
    color: #f8fafc;
    font-size: 11px;
    padding: 2px 8px;
}

QLineEdit#editHotkeyCustomKey:focus {
    border: 1px solid #38bdf8;
}
"""


class HotkeyBuilderPopover(QWidget):
    """
    Компактный поповер ручного конструктора комбинаций клавиш (Dark Obsidian v2).
    """

    hotkey_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("hotkeyBuilderPopover")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(290)
        self.setStyleSheet(HOTKEY_POPOVER_QSS)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

        self._mod_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        self.retranslate_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)

        # Заголовок
        self.lbl_header = QLabel(self)
        self.lbl_header.setProperty("class", "HotkeyPopoverHeader")
        root.addWidget(self.lbl_header)

        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1e293b; border: none;")
        root.addWidget(sep)

        # Секция модификаторов
        self.lbl_modifiers = QLabel(self)
        self.lbl_modifiers.setProperty("class", "HotkeyPopoverLabel")
        root.addWidget(self.lbl_modifiers)

        mod_row = QHBoxLayout()
        mod_row.setSpacing(6)
        for mod in MODIFIER_KEYS:
            btn = QPushButton(mod, self)
            btn.setProperty("class", "HotkeyModButton")
            btn.setCheckable(True)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setCursor(Qt.PointingHandCursor)
            self._mod_buttons[mod] = btn
            mod_row.addWidget(btn, 1)
        root.addLayout(mod_row)

        # Секция конечной клавиши (спецклавиша + ручной ввод)
        self.lbl_key = QLabel(self)
        self.lbl_key.setProperty("class", "HotkeyPopoverLabel")
        root.addWidget(self.lbl_key)

        key_row = QHBoxLayout()
        key_row.setSpacing(6)

        self.combo_special = QComboBox(self)
        self.combo_special.setObjectName("comboHotkeySpecialKey")
        self.combo_special.setFixedHeight(INPUT_HEIGHT)
        self.combo_special.setFocusPolicy(Qt.NoFocus)
        self.combo_special.addItem("", "")
        for sk in SPECIAL_KEYS:
            self.combo_special.addItem(sk, sk)
        self.combo_special.currentIndexChanged.connect(self._on_special_changed)

        self.edit_custom = QLineEdit(self)
        self.edit_custom.setObjectName("editHotkeyCustomKey")
        self.edit_custom.setFixedHeight(INPUT_HEIGHT)
        self.edit_custom.setMaxLength(16)
        self.edit_custom.textEdited.connect(self._on_custom_edited)

        key_row.addWidget(self.combo_special, 1)
        key_row.addWidget(self.edit_custom, 1)
        root.addLayout(key_row)

        # Быстрые системные пресеты (OS-reserved)
        self.lbl_presets = QLabel(self)
        self.lbl_presets.setProperty("class", "HotkeyPopoverLabel")
        root.addWidget(self.lbl_presets)

        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        for combo in SYSTEM_HOTKEY_PRESETS:
            pill = QPushButton(combo, self)
            pill.setProperty("class", "HotkeyPresetPill")
            pill.setFocusPolicy(Qt.NoFocus)
            pill.setCursor(Qt.PointingHandCursor)
            pill.clicked.connect(lambda checked=False, c=combo: self._apply_preset(c))
            presets_row.addWidget(pill)
        presets_row.addStretch(1)
        root.addLayout(presets_row)

        # Футер: Очистить / Применить
        footer_row = QHBoxLayout()
        footer_row.setSpacing(6)

        self.btn_clear = QPushButton(self)
        self.btn_clear.setObjectName("btnHotkeyPopoverClear")
        self.btn_clear.setProperty("class", "HotkeyPopoverClearBtn")
        self.btn_clear.setFocusPolicy(Qt.NoFocus)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self._on_clear_clicked)

        self.btn_apply = QPushButton(self)
        self.btn_apply.setObjectName("btnHotkeyPopoverApply")
        self.btn_apply.setProperty("class", "HotkeyPopoverApplyBtn")
        self.btn_apply.setFocusPolicy(Qt.NoFocus)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._on_apply_clicked)

        footer_row.addWidget(self.btn_clear)
        footer_row.addStretch(1)
        footer_row.addWidget(self.btn_apply)
        root.addLayout(footer_row)

    def _on_special_changed(self, index: int) -> None:
        if index > 0:
            self.edit_custom.blockSignals(True)
            self.edit_custom.clear()
            self.edit_custom.blockSignals(False)

    def _on_custom_edited(self, text: str) -> None:
        if text.strip():
            self.combo_special.blockSignals(True)
            self.combo_special.setCurrentIndex(0)
            self.combo_special.blockSignals(False)

    def _apply_preset(self, combo: str) -> None:
        self.hotkey_selected.emit(combo)
        self.hide()

    def _on_clear_clicked(self) -> None:
        self.hotkey_selected.emit("")
        self.hide()

    def _on_apply_clicked(self) -> None:
        combo = self.build_hotkey_string()
        if combo:
            self.hotkey_selected.emit(combo)
        self.hide()

    def build_hotkey_string(self) -> str:
        """Собирает каноническую строку хоткея из выбранных модификаторов и клавиши."""
        parts = [mod for mod in MODIFIER_KEYS if self._mod_buttons[mod].isChecked()]
        special = str(self.combo_special.currentData() or "").strip()
        custom = self.edit_custom.text().strip()
        key = special or (custom.upper() if len(custom) == 1 else custom)
        if key and key not in parts:
            parts.append(key)
        return "+".join(parts)

    def set_hotkey(self, hotkey: str) -> None:
        """Заполняет состояние конструктора из существующей строки хоткея."""
        tokens = [tok.strip() for tok in (hotkey or "").split("+") if tok.strip()]
        lower_tokens = {tok.lower() for tok in tokens}

        for mod, btn in self._mod_buttons.items():
            btn.setChecked(mod.lower() in lower_tokens)

        non_mods = [tok for tok in tokens if tok.lower() not in {"ctrl", "alt", "shift", "win", "meta", "cmd"}]
        self.combo_special.blockSignals(True)
        self.edit_custom.blockSignals(True)
        try:
            self.combo_special.setCurrentIndex(0)
            self.edit_custom.clear()
            if non_mods:
                target_key = non_mods[0]
                matched_idx = -1
                for idx in range(1, self.combo_special.count()):
                    if str(self.combo_special.itemData(idx)).lower() == target_key.lower():
                        matched_idx = idx
                        break
                if matched_idx > 0:
                    self.combo_special.setCurrentIndex(matched_idx)
                else:
                    self.edit_custom.setText(target_key)
        finally:
            self.combo_special.blockSignals(False)
            self.edit_custom.blockSignals(False)

    def show_at_widget(self, anchor: QWidget) -> None:
        """Показывает поповер рядом с кнопкой захвата."""
        self.adjustSize()
        global_pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 4))
        screen = anchor.screen()
        if screen is not None:
            geo = screen.availableGeometry()
            if global_pos.x() + self.width() > geo.right():
                global_pos.setX(max(geo.left(), geo.right() - self.width()))
            if global_pos.y() + self.height() > geo.bottom():
                global_pos.setY(
                    max(geo.top(), anchor.mapToGlobal(QPoint(0, 0)).y() - self.height() - 4)
                )
        self.move(global_pos)
        self.show()

    def retranslate_ui(self) -> None:
        """Обновляет локализованные подписи поповера."""
        self.lbl_header.setText(t("deck.editor.inspector.hotkey_builder.title"))
        self.lbl_modifiers.setText(t("deck.editor.inspector.hotkey_builder.modifiers"))
        self.lbl_key.setText(t("deck.editor.inspector.hotkey_builder.key"))
        self.combo_special.setItemText(0, t("deck.editor.inspector.hotkey_builder.key_none"))
        self.edit_custom.setPlaceholderText(t("deck.editor.inspector.hotkey_builder.custom_key_placeholder"))
        self.lbl_presets.setText(t("deck.editor.inspector.hotkey_builder.presets"))
        self.btn_clear.setText(t("deck.editor.inspector.hotkey_builder.clear"))
        self.btn_apply.setText(t("deck.editor.inspector.hotkey_builder.apply"))
