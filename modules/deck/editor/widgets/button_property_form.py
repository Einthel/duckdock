"""
Форма инспектора свойств кнопки (ButtonPropertyForm).
Включает шапку с категорией и корзиной 🗑️, плитку превью иконки (84x84 px),
палитру акцентных цветов ColorAccentPicker (5 неоновых свотчей), поля Title, Actions (пресеты)
и динамический стек подформ параметров QStackedLayout (Hotkey, Hotkey Switch, Path/URL, Multimedia, Text Macro, Volume Control).
Строго соблюдает бюджет высоты 220 px и инвариант In-place Retranslate без потери данных.
"""
from __future__ import annotations

import os
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.styles import (
    BORDER_SURFACE_2,
    FORM_LABEL_WIDTH,
    INPUT_HEIGHT,
    INSPECTOR_HEIGHT,
)
from modules.deck.editor.widgets.font_popover import FontCustomizationPopover
from modules.deck.editor.widgets.hotkey_capture import HotkeyCaptureButton
from modules.deck.editor.widgets.key_preview_tile import KeyPreviewTile

# Список 5 фирменных неоновых цветов
ACCENT_COLORS = [
    "#38bdf8",  # Cyan
    "#10b981",  # Emerald
    "#f59e0b",  # Amber
    "#f43f5e",  # Rose
    "#a855f7",  # Violet
]

# Ключи пресетов действий в комбобоксе
ACTION_PRESET_KEYS = [
    "hotkey",
    "hotkey_switch",
    "website",
    "open_app",
    "open_path",
    "close_window",
    "text_macro",
    "multimedia",
    "volume_control",
    "audio_device",
    "screenshot",
    "system",
    "play_audio",
    "stop_audio",
]

# Источники данных живых тайлов (Live Status Tiles)
STATUS_SOURCE_KEYS = [
    "none",
    "mic_mute",
    "audio_device",
    "dimmer",
    "cpu_temp",
    "gpu_temp",
]

# Настройка индивидуального звука клика (sound_override)
CLICK_SOUND_KEYS = [
    "default",
    "muted",
    "custom",
]

# Команды мультимедиа
MEDIA_COMMAND_KEYS = [
    "play_pause",
    "next_track",
    "prev_track",
    "stop",
    "mute",
    "volume_up",
    "volume_down",
]

# Цели регулировки звука
VOLUME_TARGET_KEYS = [
    "focus_app",
    "master",
    "microphone",
]

# Действия со звуком
VOLUME_ACTION_KEYS = [
    "toggle_mute",
    "volume_up",
    "volume_down",
]

# Режимы аудиоустройства
AUDIO_MODE_KEYS = [
    "toggle",
    "specific",
]

# Цели скриншота
SCREENSHOT_TARGET_KEYS = [
    "primary_screen",
    "active_window",
]

# Системные команды
SYSTEM_COMMAND_KEYS = [
    "toggle_dimmer",
    "lock_workstation",
    "sleep_display",
]


class ColorAccentPicker(QWidget):
    """
    Горизонтальный стрип выбора акцентного цвета кнопки из 5 круглых свотчей (20x20 px).
    """

    color_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("colorAccentPicker")
        self.setFixedHeight(28)

        self._current_color: str = ACCENT_COLORS[0]
        self._buttons: list[QPushButton] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        for col in ACCENT_COLORS:
            btn = QPushButton(self)
            btn.setProperty("class", "ColorAccentSwatch")
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"background-color: {col}; border-radius: 10px; border: 1px solid {BORDER_SURFACE_2};"
            )
            btn.clicked.connect(lambda checked=False, c=col: self._on_color_clicked(c))
            layout.addWidget(btn)
            self._buttons.append(btn)

        self.set_color(self._current_color)

    def get_color(self) -> str:
        return self._current_color

    def set_color(self, hex_color: str) -> None:
        target = hex_color.lower().strip() if hex_color else ACCENT_COLORS[0]
        matched = False
        for btn, col in zip(self._buttons, ACCENT_COLORS):
            is_active = (col.lower() == target)
            if is_active:
                matched = True
                self._current_color = col
                btn.setProperty("selected", "true")
                btn.setStyleSheet(f"background-color: {col}; border-radius: 10px; border: 2px solid #ffffff;")
            else:
                btn.setProperty("selected", "false")
                btn.setStyleSheet(f"background-color: {col}; border-radius: 10px; border: 1px solid {BORDER_SURFACE_2};")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if not matched and self._buttons:
            self._current_color = ACCENT_COLORS[0]
            self._buttons[0].setProperty("selected", "true")
            self._buttons[0].setStyleSheet(
                f"background-color: {ACCENT_COLORS[0]}; border-radius: 10px; border: 2px solid #ffffff;"
            )

    def _on_color_clicked(self, hex_color: str) -> None:
        self.set_color(hex_color)
        self.color_selected.emit(self._current_color)


class HotkeySubform(QWidget):
    """Подформа 0: Одиночный захват горячей клавиши."""

    hotkey_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.btn_hotkey = HotkeyCaptureButton(self)
        self.btn_hotkey.hotkey_changed.connect(self.hotkey_changed.emit)
        layout.addWidget(self.btn_hotkey)

    def get_hotkey(self) -> str:
        return self.btn_hotkey.get_hotkey()

    def set_hotkey(self, hotkey: str) -> None:
        self.btn_hotkey.set_hotkey(hotkey)

    def retranslate_ui(self) -> None:
        self.btn_hotkey.retranslate_ui()


class HotkeySwitchSubform(QWidget):
    """Подформа 1: Двухпозиционный переключатель хоткеев (State 1 ⇄ State 2)."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.lbl_s1 = QLabel(self)
        self.lbl_s1.setProperty("class", "InspectorFieldLabel")
        self.btn_s1 = HotkeyCaptureButton(self)

        self.lbl_arrow = QLabel("⇄", self)
        self.lbl_arrow.setProperty("class", "InspectorFieldLabel")
        self.lbl_arrow.setAlignment(Qt.AlignCenter)

        self.lbl_s2 = QLabel(self)
        self.lbl_s2.setProperty("class", "InspectorFieldLabel")
        self.btn_s2 = HotkeyCaptureButton(self)

        self.btn_s1.hotkey_changed.connect(self._emit_params)
        self.btn_s2.hotkey_changed.connect(self._emit_params)

        layout.addWidget(self.lbl_s1)
        layout.addWidget(self.btn_s1, 1)
        layout.addWidget(self.lbl_arrow)
        layout.addWidget(self.lbl_s2)
        layout.addWidget(self.btn_s2, 1)

        self.retranslate_ui()

    def _emit_params(self) -> None:
        s1_keys = [k.strip() for k in self.btn_s1.get_hotkey().split("+") if k.strip()]
        s2_keys = [k.strip() for k in self.btn_s2.get_hotkey().split("+") if k.strip()]
        params = {
            "state_1": {"title": "State 1", "keys": s1_keys},
            "state_2": {"title": "State 2", "keys": s2_keys},
            "current_state": 1,
        }
        self.params_changed.emit(params)

    def set_params(self, params: dict[str, Any]) -> None:
        self.btn_s1.blockSignals(True)
        self.btn_s2.blockSignals(True)
        try:
            s1 = params.get("state_1", {})
            s2 = params.get("state_2", {})
            k1 = s1.get("keys", []) if isinstance(s1, dict) else getattr(s1, "keys", [])
            k2 = s2.get("keys", []) if isinstance(s2, dict) else getattr(s2, "keys", [])
            self.btn_s1.set_hotkey(" + ".join(k1) if k1 else "")
            self.btn_s2.set_hotkey(" + ".join(k2) if k2 else "")
        finally:
            self.btn_s1.blockSignals(False)
            self.btn_s2.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.lbl_s1.setText(t("deck.editor.inspector.fields.state_1"))
        self.lbl_s2.setText(t("deck.editor.inspector.fields.state_2"))
        self.btn_s1.retranslate_ui()
        self.btn_s2.retranslate_ui()


class PathUrlSubform(QWidget):
    """Подформа 2: Поле ввода URL или пути к приложению/папке с кнопкой обзора 📂."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)
        self._mode: str = "website"  # "website", "open_app", "open_path"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.edit_input = QLineEdit(self)
        self.edit_input.setProperty("class", "InspectorLineEdit")
        self.edit_input.setFixedHeight(INPUT_HEIGHT)
        self.edit_input.textEdited.connect(self._on_text_edited)
        self.edit_path = self.edit_input

        self.btn_browse = QPushButton(self)
        self.btn_browse.setProperty("class", "InspectorBrowseButton")
        self.btn_browse.setFixedSize(INPUT_HEIGHT, INPUT_HEIGHT)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._on_browse_clicked)

        layout.addWidget(self.edit_input, 1)
        layout.addWidget(self.btn_browse)

        self.retranslate_ui()

    def get_path_or_url(self) -> str:
        return self.edit_input.text()

    def set_path_or_url(self, text: str) -> None:
        self.edit_input.setText(text)
        self._on_text_edited(text)

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "website":
            self.edit_input.setPlaceholderText("https://...")
            self.btn_browse.setVisible(False)
        elif mode == "open_app":
            self.edit_input.setPlaceholderText("C:\\Program Files\\...")
            self.btn_browse.setVisible(True)
        else:  # open_path
            self.edit_input.setPlaceholderText("C:\\Folder\\Document.pdf")
            self.btn_browse.setVisible(True)

    def _on_text_edited(self, text: str) -> None:
        if self._mode == "website":
            self.params_changed.emit({"url": text})
        elif self._mode == "open_app":
            self.params_changed.emit({"executable": text, "args": []})
        else:
            self.params_changed.emit({"path": text})

    def _on_browse_clicked(self) -> None:
        if self._mode == "open_app":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t("deck.editor.inspector.fields.executable"),
                os.path.expandvars("%ProgramFiles%"),
                "Executable (*.exe *.bat *.cmd);;All Files (*.*)",
            )
            if file_path:
                self.edit_input.setText(file_path)
                self._on_text_edited(file_path)
        elif self._mode == "open_path":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t("deck.editor.inspector.fields.path"),
                os.path.expanduser("~"),
                "All Files (*.*)",
            )
            if file_path:
                self.edit_input.setText(file_path)
                self._on_text_edited(file_path)

    def set_params(self, params: dict[str, Any]) -> None:
        self.edit_input.blockSignals(True)
        try:
            if self._mode == "website":
                self.edit_input.setText(params.get("url", ""))
            elif self._mode == "open_app":
                target_val = params.get("executable") or params.get("path") or ""
                self.edit_input.setText(target_val)
            else:
                self.edit_input.setText(params.get("path", ""))
        finally:
            self.edit_input.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.btn_browse.setText(t("deck.editor.inspector.fields.browse"))


class MultimediaSubform(QWidget):
    """Подформа 3: Выбор мультимедийной команды Windows."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.combo_cmd = QComboBox(self)
        self.combo_cmd.setFixedHeight(INPUT_HEIGHT)
        self.combo_cmd.setCursor(Qt.PointingHandCursor)
        for key in MEDIA_COMMAND_KEYS:
            self.combo_cmd.addItem(t(f"deck.editor.inspector.media_commands.{key}"), key)
        self.combo_cmd.currentIndexChanged.connect(self._on_cmd_changed)

        layout.addWidget(self.combo_cmd)
        self.retranslate_ui()

    def _on_cmd_changed(self, index: int) -> None:
        cmd_key = self.combo_cmd.itemData(index) or MEDIA_COMMAND_KEYS[0]
        self.params_changed.emit({"command": cmd_key})

    def set_params(self, params: dict[str, Any]) -> None:
        cmd = params.get("command", MEDIA_COMMAND_KEYS[0])
        self.combo_cmd.blockSignals(True)
        try:
            for i in range(self.combo_cmd.count()):
                if self.combo_cmd.itemData(i) == cmd:
                    self.combo_cmd.setCurrentIndex(i)
                    break
        finally:
            self.combo_cmd.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.combo_cmd.blockSignals(True)
        try:
            for i in range(self.combo_cmd.count()):
                key = self.combo_cmd.itemData(i)
                if key:
                    self.combo_cmd.setItemText(i, t(f"deck.editor.inspector.media_commands.{key}"))
        finally:
            self.combo_cmd.blockSignals(False)


class TextMacroSubform(QWidget):
    """Подформа 4: Поле ввода текстового шаблона + чекбокс Enter."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.edit_text = QLineEdit(self)
        self.edit_text.setProperty("class", "InspectorLineEdit")
        self.edit_text.setFixedHeight(INPUT_HEIGHT)
        self.edit_text.textEdited.connect(self._emit_params)

        self.chk_enter = QCheckBox(self)
        self.chk_enter.setCursor(Qt.PointingHandCursor)
        self.chk_enter.stateChanged.connect(self._emit_params)

        layout.addWidget(self.edit_text, 1)
        layout.addWidget(self.chk_enter)

        self.retranslate_ui()

    def _emit_params(self) -> None:
        self.params_changed.emit({
            "text": self.edit_text.text(),
            "send_enter": self.chk_enter.isChecked(),
        })

    def set_params(self, params: dict[str, Any]) -> None:
        self.edit_text.blockSignals(True)
        self.chk_enter.blockSignals(True)
        try:
            self.edit_text.setText(params.get("text", ""))
            self.chk_enter.setChecked(bool(params.get("send_enter", False)))
        finally:
            self.edit_text.blockSignals(False)
            self.chk_enter.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.chk_enter.setText(t("deck.editor.inspector.fields.send_enter"))


class VolumeSubform(QWidget):
    """Подформа 5: Управление громкостью (Цель + Действие)."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.combo_target = QComboBox(self)
        self.combo_target.setFixedHeight(INPUT_HEIGHT)
        self.combo_target.setCursor(Qt.PointingHandCursor)
        for key in VOLUME_TARGET_KEYS:
            self.combo_target.addItem(t(f"deck.editor.inspector.volume_targets.{key}"), key)
        self.combo_target.currentIndexChanged.connect(self._emit_params)

        self.combo_action = QComboBox(self)
        self.combo_action.setFixedHeight(INPUT_HEIGHT)
        self.combo_action.setCursor(Qt.PointingHandCursor)
        for key in VOLUME_ACTION_KEYS:
            self.combo_action.addItem(t(f"deck.editor.inspector.volume_actions.{key}"), key)
        self.combo_action.currentIndexChanged.connect(self._emit_params)

        layout.addWidget(self.combo_target, 1)
        layout.addWidget(self.combo_action, 1)

        self.retranslate_ui()

    def _emit_params(self) -> None:
        t_key = self.combo_target.itemData(self.combo_target.currentIndex()) or VOLUME_TARGET_KEYS[0]
        a_key = self.combo_action.itemData(self.combo_action.currentIndex()) or VOLUME_ACTION_KEYS[0]
        self.params_changed.emit({
            "target": t_key,
            "command": a_key,
            "step_percent": 5,
        })

    def set_params(self, params: dict[str, Any]) -> None:
        t_key = params.get("target", VOLUME_TARGET_KEYS[0])
        a_key = params.get("command", VOLUME_ACTION_KEYS[0])
        self.combo_target.blockSignals(True)
        self.combo_action.blockSignals(True)
        try:
            for i in range(self.combo_target.count()):
                if self.combo_target.itemData(i) == t_key:
                    self.combo_target.setCurrentIndex(i)
                    break
            for i in range(self.combo_action.count()):
                if self.combo_action.itemData(i) == a_key:
                    self.combo_action.setCurrentIndex(i)
                    break
        finally:
            self.combo_target.blockSignals(False)
            self.combo_action.blockSignals(False)

    def get_params(self) -> dict[str, Any]:
        return {
            "target": self.combo_target.currentData() or VOLUME_TARGET_KEYS[0],
            "command": self.combo_action.currentData() or VOLUME_ACTION_KEYS[0],
            "step_percent": 5,
        }

    def retranslate_ui(self) -> None:
        self.combo_target.blockSignals(True)
        self.combo_action.blockSignals(True)
        try:
            for i in range(self.combo_target.count()):
                k = self.combo_target.itemData(i)
                if k:
                    self.combo_target.setItemText(i, t(f"deck.editor.inspector.volume_targets.{k}"))
            for i in range(self.combo_action.count()):
                k = self.combo_action.itemData(i)
                if k:
                    self.combo_action.setItemText(i, t(f"deck.editor.inspector.volume_actions.{k}"))
        finally:
            self.combo_target.blockSignals(False)
            self.combo_action.blockSignals(False)


class NoParamsSubform(QWidget):
    """Подформа 6: Информационная плашка для действий без параметров (28 px)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.banner = QFrame(self)
        self.banner.setObjectName("inspectorNoParamsBanner")
        self.banner.setProperty("class", "InspectorNoParamsBanner")

        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(8, 2, 8, 2)
        banner_layout.setSpacing(6)

        self.lbl_icon = QLabel("ℹ️", self.banner)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(self.lbl_icon)

        self.lbl_hint = QLabel(self.banner)
        self.lbl_hint.setObjectName("lblInspectorNoParamsHint")
        self.lbl_hint.setProperty("class", "InspectorFieldHint")
        banner_layout.addWidget(self.lbl_hint, 1)

        layout.addWidget(self.banner)
        self.retranslate_ui()

    @property
    def lbl_banner(self) -> QLabel:
        return self.lbl_hint

    def set_params(self, params: dict[str, Any]) -> None:
        pass

    def retranslate_ui(self) -> None:
        self.lbl_hint.setText(t("deck.editor.inspector.hints.no_params_required"))


class AudioDeviceSubform(QWidget):
    """Подформа 7: Выбор аудиоустройства / переключение (28 px)."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.combo_mode = QComboBox(self)
        self.combo_mode.setFixedHeight(INPUT_HEIGHT)
        self.combo_mode.setCursor(Qt.PointingHandCursor)
        for key in AUDIO_MODE_KEYS:
            self.combo_mode.addItem(t(f"deck.editor.inspector.audio_modes.{key}"), key)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)

        layout.addWidget(self.combo_mode, 1)
        self.retranslate_ui()

    def _on_mode_changed(self, index: int) -> None:
        mode_key = self.combo_mode.itemData(index) or AUDIO_MODE_KEYS[0]
        params: dict[str, Any] = {"mode": mode_key}
        if mode_key == "toggle":
            params["devices"] = ["Наушники", "Динамики"]
        self.params_changed.emit(params)

    def set_params(self, params: dict[str, Any]) -> None:
        mode = params.get("mode", AUDIO_MODE_KEYS[0])
        self.combo_mode.blockSignals(True)
        try:
            for i in range(self.combo_mode.count()):
                if self.combo_mode.itemData(i) == mode:
                    self.combo_mode.setCurrentIndex(i)
                    break
        finally:
            self.combo_mode.blockSignals(False)

    def get_params(self) -> dict[str, Any]:
        mode = self.combo_mode.currentData() or AUDIO_MODE_KEYS[0]
        params: dict[str, Any] = {"mode": mode}
        if mode == "toggle":
            params["devices"] = ["Наушники", "Динамики"]
        return params

    def retranslate_ui(self) -> None:
        self.combo_mode.blockSignals(True)
        try:
            for i in range(self.combo_mode.count()):
                key = self.combo_mode.itemData(i)
                if key:
                    self.combo_mode.setItemText(i, t(f"deck.editor.inspector.audio_modes.{key}"))
        finally:
            self.combo_mode.blockSignals(False)


class ScreenshotSubform(QWidget):
    """Подформа 8: Захват скриншота (область + буфер обмена, 28 px)."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.combo_target = QComboBox(self)
        self.combo_target.setFixedHeight(INPUT_HEIGHT)
        self.combo_target.setCursor(Qt.PointingHandCursor)
        for key in SCREENSHOT_TARGET_KEYS:
            self.combo_target.addItem(t(f"deck.editor.inspector.screenshot_targets.{key}"), key)
        self.combo_target.currentIndexChanged.connect(self._emit_params)

        self.chk_clipboard = QCheckBox(self)
        self.chk_clipboard.setCursor(Qt.PointingHandCursor)
        self.chk_clipboard.setChecked(True)
        self.chk_clipboard.stateChanged.connect(self._emit_params)

        layout.addWidget(self.combo_target, 1)
        layout.addWidget(self.chk_clipboard)
        self.retranslate_ui()

    def _emit_params(self) -> None:
        target = self.combo_target.itemData(self.combo_target.currentIndex()) or SCREENSHOT_TARGET_KEYS[0]
        self.params_changed.emit({
            "target": target,
            "clipboard": self.chk_clipboard.isChecked(),
        })

    def set_params(self, params: dict[str, Any]) -> None:
        target = params.get("target", SCREENSHOT_TARGET_KEYS[0])
        clipboard = bool(params.get("clipboard", True))
        self.combo_target.blockSignals(True)
        self.chk_clipboard.blockSignals(True)
        try:
            for i in range(self.combo_target.count()):
                if self.combo_target.itemData(i) == target:
                    self.combo_target.setCurrentIndex(i)
                    break
            self.chk_clipboard.setChecked(clipboard)
        finally:
            self.combo_target.blockSignals(False)
            self.chk_clipboard.blockSignals(False)

    def get_params(self) -> dict[str, Any]:
        return {
            "target": self.combo_target.currentData() or SCREENSHOT_TARGET_KEYS[0],
            "clipboard": self.chk_clipboard.isChecked(),
        }

    def retranslate_ui(self) -> None:
        self.combo_target.blockSignals(True)
        try:
            for i in range(self.combo_target.count()):
                key = self.combo_target.itemData(i)
                if key:
                    self.combo_target.setItemText(i, t(f"deck.editor.inspector.screenshot_targets.{key}"))
        finally:
            self.combo_target.blockSignals(False)
        self.chk_clipboard.setText(t("deck.editor.inspector.fields.copy_to_clipboard"))


class SystemSubform(QWidget):
    """Подформа 9: Выбор системной команды (28 px)."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.combo_cmd = QComboBox(self)
        self.combo_cmd.setFixedHeight(INPUT_HEIGHT)
        self.combo_cmd.setCursor(Qt.PointingHandCursor)
        for key in SYSTEM_COMMAND_KEYS:
            self.combo_cmd.addItem(t(f"deck.editor.inspector.system_commands.{key}"), key)
        self.combo_cmd.currentIndexChanged.connect(self._on_cmd_changed)

        layout.addWidget(self.combo_cmd, 1)
        self.retranslate_ui()

    def _on_cmd_changed(self, index: int) -> None:
        cmd_key = self.combo_cmd.itemData(index) or SYSTEM_COMMAND_KEYS[0]
        self.params_changed.emit({"command": cmd_key})

    def set_params(self, params: dict[str, Any]) -> None:
        cmd = params.get("command", SYSTEM_COMMAND_KEYS[0])
        self.combo_cmd.blockSignals(True)
        try:
            for i in range(self.combo_cmd.count()):
                if self.combo_cmd.itemData(i) == cmd:
                    self.combo_cmd.setCurrentIndex(i)
                    break
        finally:
            self.combo_cmd.blockSignals(False)

    def get_params(self) -> dict[str, Any]:
        return {
            "command": self.combo_cmd.currentData() or SYSTEM_COMMAND_KEYS[0],
        }

    def retranslate_ui(self) -> None:
        self.combo_cmd.blockSignals(True)
        try:
            for i in range(self.combo_cmd.count()):
                key = self.combo_cmd.itemData(i)
                if key:
                    self.combo_cmd.setItemText(i, t(f"deck.editor.inspector.system_commands.{key}"))
        finally:
            self.combo_cmd.blockSignals(False)


class SoundboardSubform(QWidget):
    """Подформа 10: Воспроизведение звука саундборда (файл + предпрослушка + громкость, 28 px)."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)
        self._is_previewing: bool = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.edit_sound_path = QLineEdit(self)
        self.edit_sound_path.setFixedHeight(INPUT_HEIGHT)
        self.edit_sound_path.setPlaceholderText("*.wav, *.mp3, *.ogg")
        self.edit_sound_path.textEdited.connect(self._emit_params)

        self.btn_browse = QPushButton("📁", self)
        self.btn_browse.setFixedSize(INPUT_HEIGHT, INPUT_HEIGHT)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._on_browse_clicked)

        self.btn_preview = QPushButton("▶", self)
        self.btn_preview.setProperty("class", "InspectorTestButton")
        self.btn_preview.setFixedSize(INPUT_HEIGHT, INPUT_HEIGHT)
        self.btn_preview.setCursor(Qt.PointingHandCursor)
        self.btn_preview.clicked.connect(self._on_preview_clicked)

        self.slider_vol = QSlider(Qt.Horizontal, self)
        self.slider_vol.setFixedHeight(INPUT_HEIGHT)
        self.slider_vol.setFixedWidth(75)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(100)
        self.slider_vol.valueChanged.connect(self._on_vol_changed)

        self.lbl_vol_val = QLabel("100%", self)
        self.lbl_vol_val.setFixedWidth(36)
        self.lbl_vol_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_vol_val.setStyleSheet("color: #94a3b8; font-size: 11px;")

        layout.addWidget(self.edit_sound_path, 1)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.btn_preview)
        layout.addWidget(self.slider_vol)
        layout.addWidget(self.lbl_vol_val)

        self.retranslate_ui()

    def _on_browse_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self.window(),
            t("deck.editor.inspector.fields.sound_file"),
            "",
            "Audio Files (*.wav *.mp3 *.ogg);;All Files (*.*)",
        )
        if file_path:
            self.edit_sound_path.setText(file_path)
            self._emit_params()

    def _on_preview_clicked(self) -> None:
        from modules.deck.sound_engine import DeckSoundEngine
        eng = DeckSoundEngine()
        if self._is_previewing:
            eng.stop_preview()
            self._is_previewing = False
            self.btn_preview.setText("▶")
        else:
            path = self.edit_sound_path.text().strip()
            if path:
                vol = self.slider_vol.value() / 100.0
                if eng.preview_sound(path, vol):
                    self._is_previewing = True
                    self.btn_preview.setText("⏹")
                else:
                    self._is_previewing = False
                    self.btn_preview.setText("▶")

    def _on_vol_changed(self, val: int) -> None:
        self.lbl_vol_val.setText(f"{val}%")
        self._emit_params()

    def _emit_params(self) -> None:
        path = self.edit_sound_path.text().strip()
        vol = self.slider_vol.value() / 100.0
        self.params_changed.emit({
            "file_path": path,
            "volume": vol,
            "stop_others": False,
        })

    def set_params(self, params: dict[str, Any]) -> None:
        path = params.get("file_path", "") or params.get("sound_path", "")
        vol = float(params.get("volume", 1.0))
        vol_pct = max(0, min(100, int(vol * 100)))

        self.edit_sound_path.blockSignals(True)
        self.slider_vol.blockSignals(True)
        try:
            self.edit_sound_path.setText(str(path))
            self.slider_vol.setValue(vol_pct)
            self.lbl_vol_val.setText(f"{vol_pct}%")
        finally:
            self.edit_sound_path.blockSignals(False)
            self.slider_vol.blockSignals(False)

    def get_params(self) -> dict[str, Any]:
        return {
            "file_path": self.edit_sound_path.text().strip(),
            "volume": self.slider_vol.value() / 100.0,
            "stop_others": False,
        }

    def retranslate_ui(self) -> None:
        self.btn_preview.setToolTip(t("deck.editor.inspector.tooltips.preview_sound"))
        self.btn_browse.setToolTip(t("deck.editor.inspector.fields.browse"))


class ButtonPropertyForm(QWidget):
    """
    Форма редактирования свойств кнопки сетки DuckDeck (0..9).
    Размещается на Index 1 стэка инспектора свойств (KeyPropertyInspector).
    Строго соблюдает бюджет высоты 220 px и инвариант In-place Retranslate.
    """

    property_changed = Signal(str, object)
    delete_requested = Signal()
    test_action_requested = Signal(int)
    font_settings_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("buttonPropertyForm")
        self.setFixedHeight(INSPECTOR_HEIGHT)

        self._slot_index: int = 0
        self._current_category_raw: str = "System: Hotkey"
        self._current_font_size: int = 11
        self._current_font_color: str = "#d4d4d8"
        self._current_text_alignment: str = "bottom"
        self._current_hide_title: bool = False
        self._font_popover: Optional[Any] = None
        self._sound_override_path: Optional[str] = None

        # Главный вертикальный лэйаут формы
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # ----------------------------------------------------------------------
        # 1. Шапка формы (Header Row: категория слева, корзина справа)
        # ----------------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_category = QLabel(self._current_category_raw, self)
        self.lbl_category.setObjectName("lblInspectorCategory")
        self.lbl_category.setProperty("class", "InspectorCategoryLabel")

        self.btn_test = QPushButton("▶", self)
        self.btn_test.setObjectName("btnInspectorTest")
        self.btn_test.setProperty("class", "InspectorTestButton")
        self.btn_test.setFixedSize(28, 28)
        self.btn_test.setCursor(Qt.PointingHandCursor)
        self.btn_test.clicked.connect(lambda: self.test_action_requested.emit(self._slot_index))

        self.btn_delete = QPushButton("🗑️", self)
        self.btn_delete.setObjectName("btnInspectorDelete")
        self.btn_delete.setProperty("class", "InspectorDeleteButton")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self.delete_requested.emit)

        header_layout.addWidget(self.lbl_category)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_test)
        header_layout.addWidget(self.btn_delete)
        root_layout.addLayout(header_layout)

        # Разделитель HLine (1px BORDER_SURFACE_1)
        separator = QFrame(self)
        separator.setObjectName("formSeparator")
        separator.setProperty("class", "FormSeparator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setFixedHeight(1)
        root_layout.addWidget(separator)

        # ----------------------------------------------------------------------
        # 2. Содержимое формы: Колонка превью (Превью 84x84 + ColorAccentPicker)
        #    и Сетка параметров (Title, Actions, Dynamic Params Subforms)
        # ----------------------------------------------------------------------
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 2, 0, 2)
        content_layout.setSpacing(12)

        # Левая колонка: Превью-плитка + Стрип выбора цвета акцента
        left_preview_layout = QVBoxLayout()
        left_preview_layout.setContentsMargins(0, 0, 0, 0)
        left_preview_layout.setSpacing(6)
        left_preview_layout.setAlignment(Qt.AlignTop)

        self.preview_tile = KeyPreviewTile(self)
        self.preview_tile.tile_clicked.connect(
            lambda: self.property_changed.emit("icon_clicked", None)
        )
        self.preview_tile.add_icon_clicked.connect(
            lambda: self.property_changed.emit("load_image", None)
        )
        self.preview_tile.icon_menu_clicked.connect(
            lambda: self.property_changed.emit("icon_menu", None)
        )
        self.preview_tile.open_library_requested.connect(self._open_icon_library_dialog)
        self.preview_tile.icon_selected.connect(self._on_icon_selected_directly)
        left_preview_layout.addWidget(self.preview_tile)

        self.accent_picker = ColorAccentPicker(self)
        self.accent_picker.color_selected.connect(self._on_color_accent_changed)
        left_preview_layout.addWidget(self.accent_picker)

        content_layout.addLayout(left_preview_layout)

        # Справа: сетка параметров (Title, Actions, Params Stack)
        fields_grid = QGridLayout()
        fields_grid.setContentsMargins(0, 0, 0, 0)
        fields_grid.setVerticalSpacing(8)
        fields_grid.setHorizontalSpacing(8)

        # Строка 0: Title
        self.lbl_title_field = QLabel(self)
        self.lbl_title_field.setObjectName("lblTitleField")
        self.lbl_title_field.setProperty("class", "InspectorFieldLabel")
        self.lbl_title_field.setFixedWidth(FORM_LABEL_WIDTH)

        self.edit_title = QLineEdit(self)
        self.edit_title.setObjectName("editTitle")
        self.edit_title.setProperty("class", "InspectorLineEdit")
        self.edit_title.setFixedHeight(INPUT_HEIGHT)
        self.edit_title.textEdited.connect(
            lambda text: self.property_changed.emit("title", text)
        )

        self.btn_font = QPushButton("T ▾", self)
        self.btn_font.setObjectName("btnFontSettings")
        self.btn_font.setProperty("class", "FontSettingButton")
        self.btn_font.setFixedSize(INPUT_HEIGHT, INPUT_HEIGHT)
        self.btn_font.setCursor(Qt.PointingHandCursor)
        self.btn_font.clicked.connect(self._show_font_popover)

        fields_grid.addWidget(self.lbl_title_field, 0, 0, Qt.AlignVCenter)
        fields_grid.addWidget(self.edit_title, 0, 1)
        fields_grid.addWidget(self.btn_font, 0, 2)

        # Строка 1: Actions (пресеты)
        self.lbl_actions_field = QLabel(self)
        self.lbl_actions_field.setObjectName("lblActionsField")
        self.lbl_actions_field.setProperty("class", "InspectorFieldLabel")
        self.lbl_actions_field.setFixedWidth(FORM_LABEL_WIDTH)

        self.combo_actions = QComboBox(self)
        self.combo_actions.setObjectName("comboActions")
        self.combo_actions.setFixedHeight(INPUT_HEIGHT)
        self.combo_actions.setCursor(Qt.PointingHandCursor)
        for key in ACTION_PRESET_KEYS:
            self.combo_actions.addItem(
                t(f"deck.editor.inspector.actions_presets.{key}"), key
            )
        self.combo_actions.currentIndexChanged.connect(self._on_action_type_changed)

        fields_grid.addWidget(self.lbl_actions_field, 1, 0, Qt.AlignVCenter)
        fields_grid.addWidget(self.combo_actions, 1, 1, 1, 2)

        # Строка 2: Params (Динамический стек подформ в одну строку 28 px)
        self.lbl_params_field = QLabel(self)
        self.lbl_params_field.setObjectName("lblParamsField")
        self.lbl_params_field.setProperty("class", "InspectorFieldLabel")
        self.lbl_params_field.setFixedWidth(FORM_LABEL_WIDTH)
        self.lbl_hotkey_field = self.lbl_params_field  # Backward compatibility shim

        params_container = QWidget(self)
        params_container.setFixedHeight(INPUT_HEIGHT)
        self.params_stack = QStackedLayout(params_container)
        self.params_stack.setContentsMargins(0, 0, 0, 0)

        # Подформы 0..10
        self.subform_hotkey = HotkeySubform(params_container)
        self.subform_hotkey_switch = HotkeySwitchSubform(params_container)
        self.subform_path_url = PathUrlSubform(params_container)
        self.subform_multimedia = MultimediaSubform(params_container)
        self.subform_text_macro = TextMacroSubform(params_container)
        self.subform_volume = VolumeSubform(params_container)
        self.subform_no_params = NoParamsSubform(params_container)
        self.subform_audio_device = AudioDeviceSubform(params_container)
        self.subform_screenshot = ScreenshotSubform(params_container)
        self.subform_system = SystemSubform(params_container)
        self.subform_soundboard = SoundboardSubform(params_container)

        # Подписка на сигналы изменения подформ
        self.subform_hotkey.hotkey_changed.connect(
            lambda hk: self.property_changed.emit("hotkey", hk)
        )
        self.subform_hotkey_switch.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_path_url.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_multimedia.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_text_macro.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_volume.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_audio_device.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_screenshot.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_system.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_soundboard.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )

        self.params_stack.addWidget(self.subform_hotkey)         # Index 0
        self.params_stack.addWidget(self.subform_hotkey_switch)  # Index 1
        self.params_stack.addWidget(self.subform_path_url)       # Index 2
        self.params_stack.addWidget(self.subform_multimedia)     # Index 3
        self.params_stack.addWidget(self.subform_text_macro)     # Index 4
        self.params_stack.addWidget(self.subform_volume)         # Index 5
        self.params_stack.addWidget(self.subform_no_params)      # Index 6
        self.params_stack.addWidget(self.subform_audio_device)   # Index 7
        self.params_stack.addWidget(self.subform_screenshot)     # Index 8
        self.params_stack.addWidget(self.subform_system)         # Index 9
        self.params_stack.addWidget(self.subform_soundboard)     # Index 10

        fields_grid.addWidget(self.lbl_params_field, 2, 0, Qt.AlignVCenter)
        fields_grid.addWidget(params_container, 2, 1, 1, 2)

        # Строка 3: Живой статус (Live Status) & Звук клика (sound_override)
        self.lbl_status_field = QLabel(self)
        self.lbl_status_field.setObjectName("lblStatusField")
        self.lbl_status_field.setProperty("class", "InspectorFieldLabel")
        self.lbl_status_field.setFixedWidth(FORM_LABEL_WIDTH)

        row3_container = QWidget(self)
        row3_container.setFixedHeight(INPUT_HEIGHT)
        row3_layout = QHBoxLayout(row3_container)
        row3_layout.setContentsMargins(0, 0, 0, 0)
        row3_layout.setSpacing(6)

        self.combo_status_source = QComboBox(row3_container)
        self.combo_status_source.setFixedHeight(INPUT_HEIGHT)
        self.combo_status_source.setCursor(Qt.PointingHandCursor)
        for key in STATUS_SOURCE_KEYS:
            self.combo_status_source.addItem(
                t(f"deck.editor.inspector.status_sources.{key}"), key
            )
        self.combo_status_source.currentIndexChanged.connect(self._on_status_source_changed)

        self.lbl_click_sound_field = QLabel(self)
        self.lbl_click_sound_field.setObjectName("lblClickSoundField")
        self.lbl_click_sound_field.setProperty("class", "InspectorFieldLabel")

        self.combo_click_sound = QComboBox(row3_container)
        self.combo_click_sound.setFixedHeight(INPUT_HEIGHT)
        self.combo_click_sound.setCursor(Qt.PointingHandCursor)
        for key in CLICK_SOUND_KEYS:
            self.combo_click_sound.addItem(
                t(f"deck.editor.inspector.fields.click_sound_{key}"), key
            )
        self.combo_click_sound.currentIndexChanged.connect(self._on_click_sound_changed)

        self.btn_click_sound_browse = QPushButton("📁", row3_container)
        self.btn_click_sound_browse.setFixedSize(INPUT_HEIGHT, INPUT_HEIGHT)
        self.btn_click_sound_browse.setCursor(Qt.PointingHandCursor)
        self.btn_click_sound_browse.clicked.connect(self._on_click_sound_browse_clicked)
        self.btn_click_sound_browse.setVisible(False)

        self.btn_click_sound_preview = QPushButton("▶", row3_container)
        self.btn_click_sound_preview.setProperty("class", "InspectorTestButton")
        self.btn_click_sound_preview.setFixedSize(INPUT_HEIGHT, INPUT_HEIGHT)
        self.btn_click_sound_preview.setCursor(Qt.PointingHandCursor)
        self.btn_click_sound_preview.clicked.connect(self._on_click_sound_preview_clicked)
        self.btn_click_sound_preview.setVisible(False)

        row3_layout.addWidget(self.combo_status_source, 1)
        row3_layout.addWidget(self.lbl_click_sound_field)
        row3_layout.addWidget(self.combo_click_sound, 1)
        row3_layout.addWidget(self.btn_click_sound_browse)
        row3_layout.addWidget(self.btn_click_sound_preview)

        fields_grid.addWidget(self.lbl_status_field, 3, 0, Qt.AlignVCenter)
        fields_grid.addWidget(row3_container, 3, 1, 1, 2)

        content_layout.addLayout(fields_grid)
        root_layout.addLayout(content_layout)

        # Эластичный спейсер для плотной фиксации в пределах 220 px
        root_layout.addStretch(1)

        # Обратная совместимость для существующих тестов, читающих btn_hotkey
        self.btn_hotkey = self.subform_hotkey.btn_hotkey

        # Начальная инициализация локализованных строк
        self.retranslate_ui()

    def set_category(self, category: str) -> None:
        """Устанавливает отображаемое имя категории/типа в шапке формы."""
        self._current_category_raw = category
        self.lbl_category.setText(category)

    def get_category(self) -> str:
        """Возвращает текущую строку категории."""
        return self._current_category_raw

    def get_slot_index(self) -> int:
        """Возвращает индекс текущего редактируемого слота кнопки."""
        return self._slot_index

    def load_slot_data(self, dto: ButtonSlotDTO) -> None:
        """
        Заполняет поля формы данными из DTO кнопки с защитой blockSignals(True)
        для предотвращения сигнального эха и ложных событий изменения.
        """
        self._slot_index = dto.slot_index

        self.edit_title.blockSignals(True)
        self.combo_actions.blockSignals(True)
        self.btn_hotkey.blockSignals(True)
        try:
            category_text = dto.category if dto.category else "System: Hotkey"
            self.set_category(category_text)
            self.edit_title.setText(dto.title)

            # Сохранение и загрузка параметров типографики
            self._current_font_size = dto.font_size if hasattr(dto, "font_size") else 11
            self._current_font_color = dto.font_color if hasattr(dto, "font_color") else "#d4d4d8"
            self._current_text_alignment = dto.text_alignment if hasattr(dto, "text_alignment") else "bottom"
            self._current_hide_title = bool(dto.hide_title) if hasattr(dto, "hide_title") else False

            # Выбор цвета акцента
            accent_col = dto.color_accent or ACCENT_COLORS[0]
            self.accent_picker.set_color(accent_col)

            # Загрузка живого статуса (Live Status)
            src_val = dto.status_source or "none"
            self.combo_status_source.blockSignals(True)
            try:
                found_s = False
                for i in range(self.combo_status_source.count()):
                    if self.combo_status_source.itemData(i) == src_val:
                        self.combo_status_source.setCurrentIndex(i)
                        found_s = True
                        break
                if not found_s:
                    self.combo_status_source.setCurrentIndex(0)
            finally:
                self.combo_status_source.blockSignals(False)

            # Загрузка индивидуального звука клика (sound_override)
            snd_val = dto.sound_override
            self.combo_click_sound.blockSignals(True)
            try:
                if snd_val == "muted":
                    target_mode = "muted"
                    self._sound_override_path = None
                    self.btn_click_sound_browse.setVisible(False)
                    self.btn_click_sound_preview.setVisible(False)
                elif snd_val and snd_val != "default":
                    target_mode = "custom"
                    self._sound_override_path = snd_val
                    self.btn_click_sound_browse.setVisible(True)
                    self.btn_click_sound_preview.setVisible(True)
                else:
                    target_mode = "default"
                    self._sound_override_path = None
                    self.btn_click_sound_browse.setVisible(False)
                    self.btn_click_sound_preview.setVisible(False)

                for i in range(self.combo_click_sound.count()):
                    if self.combo_click_sound.itemData(i) == target_mode:
                        self.combo_click_sound.setCurrentIndex(i)
                        break
            finally:
                self.combo_click_sound.blockSignals(False)

            # Сопоставление типа действия с элементом комбобокса
            raw_action = dto.action_type.strip().lower().replace(" ", "_")
            mapped_params = dict(dto.action_params) if dto.action_params else {}

            # Авто-мапинг регуляторов громкости и действий каталога
            if raw_action == "auto_software_vol":
                raw_action = "volume_control"
                mapped_params.setdefault("target", "focus_app")
                mapped_params.setdefault("command", "toggle_mute")
            elif raw_action in ("master_volume_control", "mute_audio"):
                raw_action = "volume_control"
                mapped_params.setdefault("target", "master")
                mapped_params.setdefault("command", "toggle_mute")
            elif raw_action == "mic_mute_control":
                raw_action = "volume_control"
                mapped_params.setdefault("target", "microphone")
                mapped_params.setdefault("command", "toggle_mute")
            elif raw_action == "volume_up":
                raw_action = "volume_control"
                mapped_params.setdefault("target", "master")
                mapped_params.setdefault("command", "volume_up")
            elif raw_action == "volume_down":
                raw_action = "volume_control"
                mapped_params.setdefault("target", "master")
                mapped_params.setdefault("command", "volume_down")
            elif raw_action in ("output_device_toggle", "toggle_device"):
                raw_action = "audio_device"
                mapped_params.setdefault("mode", "toggle")
            elif raw_action in ("open_application", "launch"):
                raw_action = "open_app"
            elif raw_action in ("media_control", "media"):
                raw_action = "multimedia"
            elif raw_action in ("open_website", "web"):
                raw_action = "website"
            elif raw_action in ("play_audio", "soundboard"):
                raw_action = "play_audio"
            elif raw_action in ("stop_audio", "soundboard_stop"):
                raw_action = "stop_audio"

            target_idx = 0
            for i in range(self.combo_actions.count()):
                val = str(self.combo_actions.itemData(i)).lower()
                if raw_action == val:
                    target_idx = i
                    break

            self.combo_actions.setCurrentIndex(target_idx)
            self._update_subform_visibility(self.combo_actions.itemData(target_idx))

            # Загрузка параметров в подформы
            self.subform_hotkey.set_hotkey(dto.hotkey)
            self.subform_hotkey_switch.set_params(mapped_params)
            self.subform_path_url.set_params(mapped_params)
            self.subform_multimedia.set_params(mapped_params)
            self.subform_text_macro.set_params(mapped_params)
            self.subform_volume.set_params(mapped_params)
            self.subform_no_params.set_params(mapped_params)
            self.subform_audio_device.set_params(mapped_params)
            self.subform_screenshot.set_params(mapped_params)
            self.subform_system.set_params(mapped_params)
            self.subform_soundboard.set_params(mapped_params)

            self.preview_tile.set_icon(dto.icon)
        finally:
            self.edit_title.blockSignals(False)
            self.combo_actions.blockSignals(False)
            self.btn_hotkey.blockSignals(False)

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованные подписи полей, тултипы и элементы пресетов действий.
        Строго сохраняет введенный пользователем текст в edit_title и параметры подформ.
        (In-place Retranslate Invariant).
        """
        self.btn_delete.setToolTip(t("deck.editor.inspector.tooltips.delete_action"))
        if hasattr(self, "btn_test"):
            self.btn_test.setToolTip(t("deck.editor.inspector.tooltips.test_action"))

        # Подписи полей формы
        self.lbl_title_field.setText(t("deck.editor.inspector.fields.title"))
        self.lbl_actions_field.setText(t("deck.editor.inspector.fields.actions"))
        self.lbl_status_field.setText(t("deck.editor.inspector.fields.status_source"))
        self.lbl_click_sound_field.setText(t("deck.editor.inspector.fields.click_sound"))
        self.btn_font.setToolTip(t("deck.editor.font_popover.title"))
        self.btn_click_sound_browse.setToolTip(t("deck.editor.inspector.fields.sound_file"))
        self.btn_click_sound_preview.setToolTip(t("deck.editor.inspector.tooltips.test_action"))

        curr_action = self.combo_actions.itemData(self.combo_actions.currentIndex())
        if curr_action == "hotkey":
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.hotkey"))
        else:
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))

        # Пресеты в комбобоксе: обновление текстов по сохраненному userData ключу
        self.combo_actions.blockSignals(True)
        try:
            for i in range(self.combo_actions.count()):
                preset_key = self.combo_actions.itemData(i)
                if preset_key:
                    self.combo_actions.setItemText(
                        i, t(f"deck.editor.inspector.actions_presets.{preset_key}")
                    )
        finally:
            self.combo_actions.blockSignals(False)

        # Источники статуса в комбобоксе
        self.combo_status_source.blockSignals(True)
        try:
            for i in range(self.combo_status_source.count()):
                key = self.combo_status_source.itemData(i)
                if key:
                    self.combo_status_source.setItemText(
                        i, t(f"deck.editor.inspector.status_sources.{key}")
                    )
        finally:
            self.combo_status_source.blockSignals(False)

        # Варианты звука клика в комбобоксе
        self.combo_click_sound.blockSignals(True)
        try:
            for i in range(self.combo_click_sound.count()):
                key = self.combo_click_sound.itemData(i)
                if key:
                    self.combo_click_sound.setItemText(
                        i, t(f"deck.editor.inspector.fields.click_sound_{key}")
                    )
        finally:
            self.combo_click_sound.blockSignals(False)

        # Каскадный вызов локализации подформ и дочерних компонентов
        self.preview_tile.retranslate_ui()
        self.subform_hotkey.retranslate_ui()
        self.subform_hotkey_switch.retranslate_ui()
        self.subform_path_url.retranslate_ui()
        self.subform_multimedia.retranslate_ui()
        self.subform_text_macro.retranslate_ui()
        self.subform_volume.retranslate_ui()
        self.subform_no_params.retranslate_ui()
        self.subform_audio_device.retranslate_ui()
        self.subform_screenshot.retranslate_ui()
        self.subform_system.retranslate_ui()
        self.subform_soundboard.retranslate_ui()
        if self._font_popover is not None:
            self._font_popover.retranslate_ui()

    def _update_subform_visibility(self, action_key: Optional[str]) -> None:
        """Переключает активную страницу стэка подформ в зависимости от выбранного действия."""
        if action_key == "hotkey":
            self.params_stack.setCurrentIndex(0)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.hotkey"))
        elif action_key == "hotkey_switch":
            self.params_stack.setCurrentIndex(1)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key in ("website", "open_app", "open_path"):
            self.params_stack.setCurrentIndex(2)
            self.subform_path_url.set_mode(action_key)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "multimedia":
            self.params_stack.setCurrentIndex(3)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "text_macro":
            self.params_stack.setCurrentIndex(4)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "volume_control":
            self.params_stack.setCurrentIndex(5)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "close_window":
            self.params_stack.setCurrentIndex(6)
            self.subform_no_params.lbl_hint.setText(t("deck.editor.inspector.hints.no_params_required"))
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "audio_device":
            self.params_stack.setCurrentIndex(7)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "screenshot":
            self.params_stack.setCurrentIndex(8)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "system":
            self.params_stack.setCurrentIndex(9)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "play_audio":
            self.params_stack.setCurrentIndex(10)
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        elif action_key == "stop_audio":
            self.params_stack.setCurrentIndex(6)
            self.subform_no_params.lbl_hint.setText(t("deck.editor.inspector.hints.stop_audio_hint"))
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))
        else:
            self.params_stack.setCurrentIndex(6)
            self.subform_no_params.lbl_hint.setText(t("deck.editor.inspector.hints.no_params_required"))
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))

    def _show_font_popover(self) -> None:
        """Открывает всплывающее меню кастомизации типографики (FontCustomizationPopover)."""
        if self._font_popover is None:
            self._font_popover = FontCustomizationPopover(parent=self.window())
            self._font_popover.font_changed.connect(self._on_font_changed)

        self._font_popover.set_state(
            font_size=self._current_font_size,
            font_color=self._current_font_color,
            text_alignment=self._current_text_alignment,
            hide_title=self._current_hide_title,
        )
        self._font_popover.show_at_widget(self.btn_font)

    def _on_font_changed(self, data: dict) -> None:
        """Обрабатывает изменение настроек шрифта из поповера и эмитит свойства."""
        if "font_size" in data:
            self._current_font_size = int(data["font_size"])
            self.property_changed.emit("font_size", self._current_font_size)
        if "font_color" in data:
            self._current_font_color = str(data["font_color"])
            self.property_changed.emit("font_color", self._current_font_color)
        if "text_alignment" in data:
            self._current_text_alignment = str(data["text_alignment"])
            self.property_changed.emit("text_alignment", self._current_text_alignment)
        if "hide_title" in data:
            self._current_hide_title = bool(data["hide_title"])
            self.property_changed.emit("hide_title", self._current_hide_title)

    def _on_status_source_changed(self, index: int) -> None:
        """Обрабатывает выбор источника динамического статуса."""
        source_key = self.combo_status_source.itemData(index) or "none"
        self.property_changed.emit("status_source", source_key)

    def _on_click_sound_changed(self, index: int) -> None:
        """Обрабатывает переключение режима звука клика (sound_override)."""
        mode = self.combo_click_sound.itemData(index)
        if mode == "muted":
            self.btn_click_sound_browse.setVisible(False)
            self.btn_click_sound_preview.setVisible(False)
            self.property_changed.emit("sound_override", "muted")
        elif mode == "custom":
            self.btn_click_sound_browse.setVisible(True)
            self.btn_click_sound_preview.setVisible(True)
            val = self._sound_override_path if self._sound_override_path else ""
            self.property_changed.emit("sound_override", val)
        else:
            self.btn_click_sound_browse.setVisible(False)
            self.btn_click_sound_preview.setVisible(False)
            self.property_changed.emit("sound_override", None)

    def _on_click_sound_browse_clicked(self) -> None:
        """Открывает диалог выбора кастомного аудиофайла для клика кнопки."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.window(),
            t("deck.editor.inspector.fields.sound_file"),
            "",
            "Audio Files (*.wav *.mp3 *.ogg);;All Files (*.*)",
        )
        if file_path:
            self._sound_override_path = file_path
            self.property_changed.emit("sound_override", file_path)

    def _on_click_sound_preview_clicked(self) -> None:
        """Воспроизводит предварительный щелчок звука кнопки."""
        from modules.deck.sound_engine import DeckSoundEngine

        target = self._sound_override_path
        if target and os.path.exists(target):
            DeckSoundEngine.preview_sound(target, 1.0)
        else:
            DeckSoundEngine.play_tap()

    def _on_action_type_changed(self, index: int) -> None:
        """Обработчик пользовательского выбора типа действия в комбобоксе."""
        preset_key = self.combo_actions.itemData(index)
        value_to_emit = preset_key if preset_key is not None else self.combo_actions.currentText()
        self._update_subform_visibility(preset_key)
        self.property_changed.emit("action_type", value_to_emit)

    def _on_color_accent_changed(self, hex_color: str) -> None:
        """Обрабатывает выбор цвета в палитре и эмитит сигнал изменения."""
        self.property_changed.emit("color_accent", hex_color)

    def _open_icon_library_dialog(self) -> None:
        """Открывает модальный диалог IconLibraryDialog для выбора иконки из каталога."""
        from modules.deck.editor.widgets.icon_library_dialog import IconLibraryDialog

        dialog = IconLibraryDialog(parent=self.window(), current_icon=self.preview_tile.get_icon())
        if dialog.exec() == QDialog.Accepted:
            selected_icon = dialog.get_selected_icon()
            if selected_icon is not None:
                self.preview_tile.set_icon(selected_icon)
                self.property_changed.emit("icon", selected_icon)

    def _on_icon_selected_directly(self, icon_str_or_path: str) -> None:
        """Обрабатывает прямой выбор иконки из файла или сброс из контекстного меню."""
        self.preview_tile.set_icon(icon_str_or_path)
        self.property_changed.emit("icon", icon_str_or_path)


__all__ = [
    "ACCENT_COLORS",
    "ACTION_PRESET_KEYS",
    "STATUS_SOURCE_KEYS",
    "CLICK_SOUND_KEYS",
    "MEDIA_COMMAND_KEYS",
    "VOLUME_TARGET_KEYS",
    "VOLUME_ACTION_KEYS",
    "AUDIO_MODE_KEYS",
    "SCREENSHOT_TARGET_KEYS",
    "SYSTEM_COMMAND_KEYS",
    "ColorAccentPicker",
    "HotkeySubform",
    "HotkeySwitchSubform",
    "PathUrlSubform",
    "MultimediaSubform",
    "TextMacroSubform",
    "VolumeSubform",
    "NoParamsSubform",
    "AudioDeviceSubform",
    "ScreenshotSubform",
    "SystemSubform",
    "SoundboardSubform",
    "ButtonPropertyForm",
]
