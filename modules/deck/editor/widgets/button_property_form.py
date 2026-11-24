"""
Форма инспектора свойств кнопки (ButtonPropertyForm).
Включает шапку с категорией, кнопками тестирования ▶ и очистки 🗑️, плитку превью иконки (84x84 px),
палитру акцентных цветов ColorAccentPicker (5 неоновых свотчей), поля Title, Actions (8 примитивов)
и динамический стек из 8 чистых подформ параметров QStackedLayout + UnconfiguredSubform.
Строго соблюдает бюджет высоты INSPECTOR_HEIGHT (260 px), Qt.NoFocus и In-place Retranslate.
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

# Ровно 8 базовых ортогональных примитивов DuckDeck
ACTION_PRIMITIVE_KEYS = [
    "hotkey",
    "launch",
    "audio",
    "media",
    "text",
    "system",
    "deck_nav",
    "macro",
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

# Режимы хоткея
HOTKEY_MODE_KEYS = [
    "press",
    "toggle",
]

# Типы запуска Launch
LAUNCH_KIND_KEYS = [
    "app",
    "file",
    "url",
]

# Категории аудиоподсистемы
AUDIO_CATEGORY_KEYS = [
    "volume",
    "device",
]

# Цели регулировки громкости
VOLUME_TARGET_KEYS = [
    "focus_app",
    "master",
    "mic",
]

# Действия со звуком
VOLUME_ACTION_KEYS = [
    "toggle_mute",
    "volume_up",
    "volume_down",
]

# Режимы аудиоустройства
AUDIO_DEVICE_MODE_KEYS = [
    "toggle",
    "set",
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

# Системные команды (все 5 команд SystemActionParams)
SYSTEM_COMMAND_KEYS = [
    "toggle_dimmer",
    "screenshot",
    "lock_workstation",
    "sleep_display",
    "close_window",
]

# Цели скриншота
SCREENSHOT_TARGET_KEYS = [
    "primary",
    "active_window",
]


def _parse_keys_list(hotkey_str: str) -> list[str]:
    """Парсит строку 'Ctrl + Shift + D' в ['ctrl', 'shift', 'd']."""
    if not hotkey_str or not hotkey_str.strip():
        return []
    return [k.strip().lower() for k in hotkey_str.split("+") if k.strip()]


def _format_keys_list(keys: Any) -> str:
    """Форматирует список клавиш ['ctrl', 'd'] в 'Ctrl + D'."""
    if not isinstance(keys, list):
        return str(keys) if keys else ""
    parts: list[str] = []
    for k in keys:
        lk = str(k).strip().lower()
        if not lk:
            continue
        if lk == "ctrl":
            parts.append("Ctrl")
        elif lk == "alt":
            parts.append("Alt")
        elif lk == "shift":
            parts.append("Shift")
        elif lk in ("win", "cmd", "meta"):
            parts.append("Win")
        elif lk.startswith("f") and lk[1:].isdigit():
            parts.append(lk.upper())
        elif len(lk) == 1:
            parts.append(lk.upper())
        else:
            parts.append(lk.capitalize())
    return " + ".join(parts)


class ColorAccentPicker(QWidget):
    """Горизонтальный стрип выбора акцентного цвета кнопки из 5 круглых свотчей."""

    color_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("colorAccentPicker")
        self.setFixedSize(82, 22)

        self._current_color: str = ACCENT_COLORS[0]
        self._buttons: list[QPushButton] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        for col in ACCENT_COLORS:
            btn = QPushButton(self)
            btn.setProperty("class", "ColorAccentSwatch")
            btn.setFixedSize(14, 14)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setStyleSheet(
                f"background-color: {col}; border-radius: 7px; border: 1px solid {BORDER_SURFACE_2};"
            )
            btn.clicked.connect(lambda checked=False, c=col: self._on_color_clicked(c))
            layout.addWidget(btn)
            self._buttons.append(btn)

        self.set_color(self._current_color)

    def get_color(self) -> str:
        return self._current_color

    def set_color(self, hex_color: str) -> None:
        target = hex_color.lower().strip() if hex_color else ACCENT_COLORS[0]
        self._current_color = hex_color or ACCENT_COLORS[0]
        matched = False
        for btn, col in zip(self._buttons, ACCENT_COLORS):
            is_active = col.lower() == target
            if is_active:
                matched = True
                self._current_color = col
                btn.setProperty("selected", "true")
                btn.setStyleSheet(f"background-color: {col}; border-radius: 7px; border: 2px solid #ffffff;")
            else:
                btn.setProperty("selected", "false")
                btn.setStyleSheet(f"background-color: {col}; border-radius: 7px; border: 1px solid {BORDER_SURFACE_2};")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if not matched and self._buttons:
            self._current_color = hex_color or ACCENT_COLORS[0]

    def _on_color_clicked(self, hex_color: str) -> None:
        self.set_color(hex_color)
        self.color_selected.emit(self._current_color)


class HotkeySubform(QWidget):
    """Подформа 0: Одиночный хоткей или двухпозиционный тумблер (28 px)."""

    params_changed = Signal(dict)
    hotkey_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.combo_mode = QComboBox(self)
        self.combo_mode.setFixedHeight(INPUT_HEIGHT)
        self.combo_mode.setFixedWidth(104)
        self.combo_mode.setCursor(Qt.PointingHandCursor)
        self.combo_mode.setFocusPolicy(Qt.NoFocus)
        for key in HOTKEY_MODE_KEYS:
            self.combo_mode.addItem(t(f"deck.editor.inspector.hotkey_modes.{key}"), key)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)

        self.btn_hotkey = HotkeyCaptureButton(self)
        self.btn_hotkey.setFocusPolicy(Qt.NoFocus)
        self.btn_hotkey.hotkey_changed.connect(self._on_primary_hotkey_changed)

        self.lbl_arrow = QLabel("⇄", self)
        self.lbl_arrow.setProperty("class", "InspectorFieldLabel")
        self.lbl_arrow.setAlignment(Qt.AlignCenter)
        self.lbl_arrow.setVisible(False)

        self.btn_toggle_hotkey = HotkeyCaptureButton(self)
        self.btn_toggle_hotkey.setFocusPolicy(Qt.NoFocus)
        self.btn_toggle_hotkey.hotkey_changed.connect(self._on_toggle_hotkey_changed)
        self.btn_toggle_hotkey.setVisible(False)

        layout.addWidget(self.combo_mode)
        layout.addWidget(self.btn_hotkey, 1)
        layout.addWidget(self.lbl_arrow)
        layout.addWidget(self.btn_toggle_hotkey, 1)

        self.retranslate_ui()

    def _on_mode_changed(self, _index: int) -> None:
        mode = self.combo_mode.currentData() or "press"
        is_toggle = mode == "toggle"
        self.lbl_arrow.setVisible(is_toggle)
        self.btn_toggle_hotkey.setVisible(is_toggle)
        self._emit_params()

    def _on_primary_hotkey_changed(self, hk: str) -> None:
        self.hotkey_changed.emit(hk)
        self._emit_params()

    def _on_toggle_hotkey_changed(self, _hk: str) -> None:
        self._emit_params()

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_hotkey(self) -> str:
        return self.btn_hotkey.get_hotkey()

    def set_hotkey(self, hotkey: str) -> None:
        self.btn_hotkey.blockSignals(True)
        try:
            self.btn_hotkey.set_hotkey(hotkey)
        finally:
            self.btn_hotkey.blockSignals(False)

    def get_params(self) -> dict[str, Any]:
        mode = self.combo_mode.currentData() or "press"
        keys = _parse_keys_list(self.btn_hotkey.get_hotkey())
        toggle_keys = _parse_keys_list(self.btn_toggle_hotkey.get_hotkey()) if mode == "toggle" else []
        return {
            "mode": mode,
            "keys": keys,
            "toggle_keys": toggle_keys,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        mode = str(params.get("mode", "press"))
        if mode not in HOTKEY_MODE_KEYS:
            mode = "press"
        keys = params.get("keys", [])
        toggle_keys = params.get("toggle_keys", [])

        self.combo_mode.blockSignals(True)
        self.btn_hotkey.blockSignals(True)
        self.btn_toggle_hotkey.blockSignals(True)
        try:
            idx = self.combo_mode.findData(mode)
            self.combo_mode.setCurrentIndex(idx if idx >= 0 else 0)
            is_toggle = mode == "toggle"
            self.lbl_arrow.setVisible(is_toggle)
            self.btn_toggle_hotkey.setVisible(is_toggle)
            self.btn_hotkey.set_hotkey(_format_keys_list(keys))
            self.btn_toggle_hotkey.set_hotkey(_format_keys_list(toggle_keys))
        finally:
            self.combo_mode.blockSignals(False)
            self.btn_hotkey.blockSignals(False)
            self.btn_toggle_hotkey.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.combo_mode.blockSignals(True)
        try:
            for i in range(self.combo_mode.count()):
                key = self.combo_mode.itemData(i)
                if key:
                    self.combo_mode.setItemText(i, t(f"deck.editor.inspector.hotkey_modes.{key}"))
        finally:
            self.combo_mode.blockSignals(False)
        self.btn_hotkey.retranslate_ui()
        self.btn_toggle_hotkey.retranslate_ui()


class LaunchSubform(QWidget):
    """Подформа 1: Запуск приложения, файла/папки или веб-ссылки (28 px)."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.combo_kind = QComboBox(self)
        self.combo_kind.setFixedHeight(INPUT_HEIGHT)
        self.combo_kind.setFixedWidth(120)
        self.combo_kind.setCursor(Qt.PointingHandCursor)
        self.combo_kind.setFocusPolicy(Qt.NoFocus)
        for key in LAUNCH_KIND_KEYS:
            self.combo_kind.addItem(t(f"deck.editor.inspector.launch_kinds.{key}"), key)
        self.combo_kind.currentIndexChanged.connect(self._on_kind_changed)

        self.edit_target = QLineEdit(self)
        self.edit_target.setProperty("class", "InspectorLineEdit")
        self.edit_target.setFixedHeight(INPUT_HEIGHT)
        self.edit_target.textEdited.connect(self._emit_params)
        self.edit_input = self.edit_target
        self.edit_path = self.edit_target

        self.btn_browse = QPushButton(self)
        self.btn_browse.setProperty("class", "InspectorBrowseButton")
        self.btn_browse.setFixedSize(INPUT_HEIGHT, INPUT_HEIGHT)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setFocusPolicy(Qt.NoFocus)
        self.btn_browse.clicked.connect(self._on_browse_clicked)

        layout.addWidget(self.combo_kind)
        layout.addWidget(self.edit_target, 1)
        layout.addWidget(self.btn_browse)

        self._sync_kind_ui("app")
        self.retranslate_ui()

    def _sync_kind_ui(self, kind: str) -> None:
        if kind == "url":
            self.edit_target.setPlaceholderText("https://...")
            self.btn_browse.setVisible(False)
        elif kind == "file":
            self.edit_target.setPlaceholderText("C:\\Folder\\Document.pdf")
            self.btn_browse.setVisible(True)
        else:
            self.edit_target.setPlaceholderText("C:\\Program Files\\...")
            self.btn_browse.setVisible(True)

    def _on_kind_changed(self, _index: int) -> None:
        kind = self.combo_kind.currentData() or "app"
        self._sync_kind_ui(kind)
        self._emit_params()

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def _on_browse_clicked(self) -> None:
        kind = self.combo_kind.currentData() or "app"
        if kind == "app":
            file_path, _ = QFileDialog.getOpenFileName(
                self.window(),
                t("deck.editor.inspector.fields.executable"),
                os.path.expandvars("%ProgramFiles%"),
                "Executable (*.exe *.bat *.cmd);;All Files (*.*)",
            )
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self.window(),
                t("deck.editor.inspector.fields.path"),
                os.path.expanduser("~"),
                "All Files (*.*)",
            )
        if file_path:
            self.edit_target.setText(file_path)
            self._emit_params()

    def get_params(self) -> dict[str, Any]:
        kind = self.combo_kind.currentData() or "app"
        return {
            "kind": kind,
            "target": self.edit_target.text().strip(),
        }

    def set_params(self, params: dict[str, Any]) -> None:
        kind = str(params.get("kind") or "app")
        target_val = str(
            params.get("target")
            or params.get("url")
            or params.get("path")
            or params.get("executable")
            or ""
        )
        if kind not in LAUNCH_KIND_KEYS:
            kind = "url" if target_val.startswith(("http://", "https://")) else "app"

        self.combo_kind.blockSignals(True)
        self.edit_target.blockSignals(True)
        try:
            idx = self.combo_kind.findData(kind)
            self.combo_kind.setCurrentIndex(idx if idx >= 0 else 0)
            self._sync_kind_ui(kind)
            self.edit_target.setText(target_val)
        finally:
            self.combo_kind.blockSignals(False)
            self.edit_target.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.combo_kind.blockSignals(True)
        try:
            for i in range(self.combo_kind.count()):
                key = self.combo_kind.itemData(i)
                if key:
                    self.combo_kind.setItemText(i, t(f"deck.editor.inspector.launch_kinds.{key}"))
        finally:
            self.combo_kind.blockSignals(False)
        self.btn_browse.setText(t("deck.editor.inspector.fields.browse"))


class AudioSubform(QWidget):
    """
    Подформа 2: Единая панель аудиоподсистемы (28 px).
    Переключатель режима: 'Громкость / Mute' | 'Аудиоустройство'.
    Список аудиоустройств передается через Dependency Injection (set_audio_devices).
    """

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)
        self._audio_devices: list[tuple[str, str]] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.combo_category = QComboBox(self)
        self.combo_category.setFixedHeight(INPUT_HEIGHT)
        self.combo_category.setFixedWidth(130)
        self.combo_category.setCursor(Qt.PointingHandCursor)
        self.combo_category.setFocusPolicy(Qt.NoFocus)
        for key in AUDIO_CATEGORY_KEYS:
            self.combo_category.addItem(t(f"deck.editor.inspector.audio_categories.{key}"), key)
        self.combo_category.currentIndexChanged.connect(self._on_category_changed)

        # Группа громкости / Mute
        self.combo_target = QComboBox(self)
        self.combo_target.setFixedHeight(INPUT_HEIGHT)
        self.combo_target.setCursor(Qt.PointingHandCursor)
        self.combo_target.setFocusPolicy(Qt.NoFocus)
        for key in VOLUME_TARGET_KEYS:
            loc_k = "microphone" if key == "mic" else key
            self.combo_target.addItem(t(f"deck.editor.inspector.volume_targets.{loc_k}"), key)
        self.combo_target.currentIndexChanged.connect(self._emit_params)

        self.combo_action = QComboBox(self)
        self.combo_action.setFixedHeight(INPUT_HEIGHT)
        self.combo_action.setCursor(Qt.PointingHandCursor)
        self.combo_action.setFocusPolicy(Qt.NoFocus)
        for key in VOLUME_ACTION_KEYS:
            self.combo_action.addItem(t(f"deck.editor.inspector.volume_actions.{key}"), key)
        self.combo_action.currentIndexChanged.connect(self._emit_params)

        # Группа переключения / выбора устройства
        self.combo_dev_mode = QComboBox(self)
        self.combo_dev_mode.setFixedHeight(INPUT_HEIGHT)
        self.combo_dev_mode.setCursor(Qt.PointingHandCursor)
        self.combo_dev_mode.setFocusPolicy(Qt.NoFocus)
        for key in AUDIO_DEVICE_MODE_KEYS:
            loc_k = "specific" if key == "set" else key
            self.combo_dev_mode.addItem(t(f"deck.editor.inspector.audio_modes.{loc_k}"), key)
        self.combo_dev_mode.currentIndexChanged.connect(self._on_dev_mode_changed)

        self.combo_device = QComboBox(self)
        self.combo_device.setFixedHeight(INPUT_HEIGHT)
        self.combo_device.setCursor(Qt.PointingHandCursor)
        self.combo_device.setFocusPolicy(Qt.NoFocus)
        self.combo_device.currentIndexChanged.connect(self._emit_params)

        layout.addWidget(self.combo_category)
        layout.addWidget(self.combo_target, 1)
        layout.addWidget(self.combo_action, 1)
        layout.addWidget(self.combo_dev_mode, 1)
        layout.addWidget(self.combo_device, 1)

        self._sync_visibility()
        self.retranslate_ui()

    def set_audio_devices(self, devices: list[tuple[str, str]]) -> None:
        """DI-метод передачи списка доступных устройств [(device_id, name)]."""
        self._audio_devices = list(devices) if devices else []
        current_id = self.combo_device.currentData()
        self.combo_device.blockSignals(True)
        try:
            self.combo_device.clear()
            if not self._audio_devices:
                self.combo_device.addItem(t("deck.editor.inspector.fields.select_device"), "")
            else:
                for dev_id, dev_name in self._audio_devices:
                    self.combo_device.addItem(dev_name, dev_id)
                if current_id:
                    idx = self.combo_device.findData(current_id)
                    if idx >= 0:
                        self.combo_device.setCurrentIndex(idx)
        finally:
            self.combo_device.blockSignals(False)

    def _sync_visibility(self) -> None:
        cat = self.combo_category.currentData() or "volume"
        is_vol = cat == "volume"
        self.combo_target.setVisible(is_vol)
        self.combo_action.setVisible(is_vol)
        self.combo_dev_mode.setVisible(not is_vol)
        dev_mode = self.combo_dev_mode.currentData() or "toggle"
        self.combo_device.setVisible((not is_vol) and (dev_mode == "set"))

    def _on_category_changed(self, _index: int) -> None:
        self._sync_visibility()
        self._emit_params()

    def _on_dev_mode_changed(self, _index: int) -> None:
        self._sync_visibility()
        self._emit_params()

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, Any]:
        cat = self.combo_category.currentData() or "volume"
        if cat == "device":
            mode = self.combo_dev_mode.currentData() or "toggle"
            if mode == "set":
                return {
                    "target": "device",
                    "command": "set_device",
                    "mode": "set",
                    "target_device_id": self.combo_device.currentData() or None,
                }
            return {
                "target": "device",
                "command": "toggle_device",
                "mode": "toggle",
                "devices": ["Наушники", "Динамики"],
            }
        target = self.combo_target.currentData() or "master"
        cmd = self.combo_action.currentData() or "toggle_mute"
        return {
            "target": target,
            "command": cmd,
            "step_percent": 5,
        }

    def set_params(self, params: dict[str, Any]) -> None:
        raw_target = str(params.get("target") or "master")
        if raw_target == "microphone":
            raw_target = "mic"
        raw_cmd = str(params.get("command") or "toggle_mute")
        if raw_cmd == "step":
            step = int(params.get("step_percent", 5))
            raw_cmd = "volume_up" if step >= 0 else "volume_down"

        is_device = raw_target == "device" or raw_cmd in ("toggle_device", "set_device")
        cat = "device" if is_device else "volume"

        self.combo_category.blockSignals(True)
        self.combo_target.blockSignals(True)
        self.combo_action.blockSignals(True)
        self.combo_dev_mode.blockSignals(True)
        self.combo_device.blockSignals(True)
        try:
            cat_idx = self.combo_category.findData(cat)
            self.combo_category.setCurrentIndex(cat_idx if cat_idx >= 0 else 0)

            if is_device:
                dev_mode = "set" if (params.get("mode") == "set" or raw_cmd == "set_device") else "toggle"
                m_idx = self.combo_dev_mode.findData(dev_mode)
                self.combo_dev_mode.setCurrentIndex(m_idx if m_idx >= 0 else 0)
                dev_id = params.get("target_device_id")
                if dev_id:
                    d_idx = self.combo_device.findData(dev_id)
                    if d_idx >= 0:
                        self.combo_device.setCurrentIndex(d_idx)
                    else:
                        self.combo_device.addItem(str(dev_id), dev_id)
                        self.combo_device.setCurrentIndex(self.combo_device.count() - 1)
            else:
                t_idx = self.combo_target.findData(raw_target)
                self.combo_target.setCurrentIndex(t_idx if t_idx >= 0 else 1)
                a_idx = self.combo_action.findData(raw_cmd)
                self.combo_action.setCurrentIndex(a_idx if a_idx >= 0 else 0)

            self._sync_visibility()
        finally:
            self.combo_category.blockSignals(False)
            self.combo_target.blockSignals(False)
            self.combo_action.blockSignals(False)
            self.combo_dev_mode.blockSignals(False)
            self.combo_device.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.combo_category.blockSignals(True)
        self.combo_target.blockSignals(True)
        self.combo_action.blockSignals(True)
        self.combo_dev_mode.blockSignals(True)
        try:
            for i in range(self.combo_category.count()):
                k = self.combo_category.itemData(i)
                if k:
                    self.combo_category.setItemText(i, t(f"deck.editor.inspector.audio_categories.{k}"))
            for i in range(self.combo_target.count()):
                k = self.combo_target.itemData(i)
                if k:
                    loc_k = "microphone" if k == "mic" else k
                    self.combo_target.setItemText(i, t(f"deck.editor.inspector.volume_targets.{loc_k}"))
            for i in range(self.combo_action.count()):
                k = self.combo_action.itemData(i)
                if k:
                    self.combo_action.setItemText(i, t(f"deck.editor.inspector.volume_actions.{k}"))
            for i in range(self.combo_dev_mode.count()):
                k = self.combo_dev_mode.itemData(i)
                if k:
                    loc_k = "specific" if k == "set" else k
                    self.combo_dev_mode.setItemText(i, t(f"deck.editor.inspector.audio_modes.{loc_k}"))
        finally:
            self.combo_category.blockSignals(False)
            self.combo_target.blockSignals(False)
            self.combo_action.blockSignals(False)
            self.combo_dev_mode.blockSignals(False)


class MediaSubform(QWidget):
    """Подформа 3: Выбор мультимедийной команды Windows (28 px)."""

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
        self.combo_cmd.setFocusPolicy(Qt.NoFocus)
        for key in MEDIA_COMMAND_KEYS:
            self.combo_cmd.addItem(t(f"deck.editor.inspector.media_commands.{key}"), key)
        self.combo_cmd.currentIndexChanged.connect(self._on_cmd_changed)

        layout.addWidget(self.combo_cmd)
        self.retranslate_ui()

    def _on_cmd_changed(self, index: int) -> None:
        cmd_key = self.combo_cmd.itemData(index) or MEDIA_COMMAND_KEYS[0]
        self.params_changed.emit({"command": cmd_key})

    def get_params(self) -> dict[str, Any]:
        return {"command": self.combo_cmd.currentData() or MEDIA_COMMAND_KEYS[0]}

    def set_params(self, params: dict[str, Any]) -> None:
        cmd = params.get("command", MEDIA_COMMAND_KEYS[0])
        self.combo_cmd.blockSignals(True)
        try:
            idx = self.combo_cmd.findData(cmd)
            if idx >= 0:
                self.combo_cmd.setCurrentIndex(idx)
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


class TextSubform(QWidget):
    """Подформа 4: Поле ввода текстового шаблона + чекбокс Enter (28 px)."""

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
        self.chk_enter.setFocusPolicy(Qt.NoFocus)
        self.chk_enter.stateChanged.connect(self._emit_params)

        layout.addWidget(self.edit_text, 1)
        layout.addWidget(self.chk_enter)

        self.retranslate_ui()

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, Any]:
        return {
            "text": self.edit_text.text(),
            "send_enter": self.chk_enter.isChecked(),
        }

    def set_params(self, params: dict[str, Any]) -> None:
        self.edit_text.blockSignals(True)
        self.chk_enter.blockSignals(True)
        try:
            self.edit_text.setText(str(params.get("text", "")))
            self.chk_enter.setChecked(bool(params.get("send_enter", False)))
        finally:
            self.edit_text.blockSignals(False)
            self.chk_enter.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.chk_enter.setText(t("deck.editor.inspector.fields.send_enter"))


class SystemSubform(QWidget):
    """Подформа 5: Все 5 системных команд + опции скриншота при command='screenshot' (28 px)."""

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
        self.combo_cmd.setFocusPolicy(Qt.NoFocus)
        for key in SYSTEM_COMMAND_KEYS:
            self.combo_cmd.addItem(t(f"deck.editor.inspector.system_commands.{key}"), key)
        self.combo_cmd.currentIndexChanged.connect(self._on_cmd_changed)

        self.combo_screenshot_target = QComboBox(self)
        self.combo_screenshot_target.setFixedHeight(INPUT_HEIGHT)
        self.combo_screenshot_target.setCursor(Qt.PointingHandCursor)
        self.combo_screenshot_target.setFocusPolicy(Qt.NoFocus)
        for key in SCREENSHOT_TARGET_KEYS:
            loc_k = "primary_screen" if key == "primary" else key
            self.combo_screenshot_target.addItem(t(f"deck.editor.inspector.screenshot_targets.{loc_k}"), key)
        self.combo_screenshot_target.currentIndexChanged.connect(self._emit_params)

        self.chk_clipboard = QCheckBox(self)
        self.chk_clipboard.setCursor(Qt.PointingHandCursor)
        self.chk_clipboard.setFocusPolicy(Qt.NoFocus)
        self.chk_clipboard.setChecked(True)
        self.chk_clipboard.stateChanged.connect(self._emit_params)

        layout.addWidget(self.combo_cmd, 1)
        layout.addWidget(self.combo_screenshot_target, 1)
        layout.addWidget(self.chk_clipboard)

        self._sync_screenshot_visibility("toggle_dimmer")
        self.retranslate_ui()

    def _sync_screenshot_visibility(self, cmd: str) -> None:
        is_shot = cmd == "screenshot"
        self.combo_screenshot_target.setVisible(is_shot)
        self.chk_clipboard.setVisible(is_shot)

    def _on_cmd_changed(self, index: int) -> None:
        cmd_key = self.combo_cmd.itemData(index) or SYSTEM_COMMAND_KEYS[0]
        self._sync_screenshot_visibility(cmd_key)
        self._emit_params()

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, Any]:
        cmd = self.combo_cmd.currentData() or SYSTEM_COMMAND_KEYS[0]
        if cmd == "screenshot":
            return {
                "command": "screenshot",
                "screenshot_target": self.combo_screenshot_target.currentData() or "primary",
                "clipboard": self.chk_clipboard.isChecked(),
            }
        return {"command": cmd}

    def set_params(self, params: dict[str, Any]) -> None:
        cmd = str(params.get("command") or SYSTEM_COMMAND_KEYS[0])
        cmd_aliases = {
            "dimmer": "toggle_dimmer",
            "lock_pc": "lock_workstation",
        }
        cmd = cmd_aliases.get(cmd, cmd)
        if cmd not in SYSTEM_COMMAND_KEYS:
            cmd = SYSTEM_COMMAND_KEYS[0]

        shot_target = str(params.get("screenshot_target") or params.get("target") or "primary")
        if shot_target == "primary_screen":
            shot_target = "primary"
        if shot_target not in SCREENSHOT_TARGET_KEYS:
            shot_target = "primary"
        clipboard = bool(params.get("clipboard", True))

        self.combo_cmd.blockSignals(True)
        self.combo_screenshot_target.blockSignals(True)
        self.chk_clipboard.blockSignals(True)
        try:
            c_idx = self.combo_cmd.findData(cmd)
            self.combo_cmd.setCurrentIndex(c_idx if c_idx >= 0 else 0)
            s_idx = self.combo_screenshot_target.findData(shot_target)
            self.combo_screenshot_target.setCurrentIndex(s_idx if s_idx >= 0 else 0)
            self.chk_clipboard.setChecked(clipboard)
            self._sync_screenshot_visibility(cmd)
        finally:
            self.combo_cmd.blockSignals(False)
            self.combo_screenshot_target.blockSignals(False)
            self.chk_clipboard.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.combo_cmd.blockSignals(True)
        self.combo_screenshot_target.blockSignals(True)
        try:
            for i in range(self.combo_cmd.count()):
                key = self.combo_cmd.itemData(i)
                if key:
                    self.combo_cmd.setItemText(i, t(f"deck.editor.inspector.system_commands.{key}"))
            for i in range(self.combo_screenshot_target.count()):
                key = self.combo_screenshot_target.itemData(i)
                if key:
                    loc_k = "primary_screen" if key == "primary" else key
                    self.combo_screenshot_target.setItemText(i, t(f"deck.editor.inspector.screenshot_targets.{loc_k}"))
        finally:
            self.combo_cmd.blockSignals(False)
            self.combo_screenshot_target.blockSignals(False)
        self.chk_clipboard.setText(t("deck.editor.inspector.fields.copy_to_clipboard"))


class DeckNavSubform(QWidget):
    """Подформа 6: Навигация DuckDeck (28 px)."""

    params_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.combo_target = QComboBox(self)
        self.combo_target.setFixedHeight(INPUT_HEIGHT)
        self.combo_target.setCursor(Qt.PointingHandCursor)
        self.combo_target.setFocusPolicy(Qt.NoFocus)

        self.NAV_COMMANDS = [
            ("next_page", "deck.editor.inspector.nav_commands.next_page"),
            ("prev_page", "deck.editor.inspector.nav_commands.prev_page"),
            ("goto_page", "deck.editor.inspector.nav_commands.goto_page"),
            ("folder_back", "deck.editor.inspector.nav_commands.folder_back"),
            ("switch_profile", "deck.editor.inspector.nav_commands.switch_profile"),
        ]

        model = self.combo_target.model()
        for idx, (cmd, loc_key) in enumerate(self.NAV_COMMANDS):
            self.combo_target.addItem(t(loc_key), cmd)
            if cmd == "switch_profile" and hasattr(model, "item"):
                item = model.item(idx)
                if item is not None:
                    item.setEnabled(False)

        self.combo_target.currentIndexChanged.connect(self._on_cmd_changed)

        self.edit_page = QLineEdit(self)
        self.edit_page.setProperty("class", "InspectorLineEdit")
        self.edit_page.setFixedHeight(INPUT_HEIGHT)
        self.edit_page.setPlaceholderText(t("deck.editor.inspector.fields.page_id"))
        self.edit_page.textEdited.connect(self._emit_params)
        self.edit_page.setVisible(False)

        layout.addWidget(self.combo_target, 1)
        layout.addWidget(self.edit_page, 1)

    def _on_cmd_changed(self, index: int) -> None:
        cmd = self.combo_target.itemData(index) or "next_page"
        self.edit_page.setVisible(cmd == "goto_page")
        self._emit_params()

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def set_params(self, params: dict[str, Any]) -> None:
        target = params.get("target", "next_page")
        page_id = params.get("page_id") or ""
        self.combo_target.blockSignals(True)
        self.edit_page.blockSignals(True)
        try:
            idx = self.combo_target.findData(target)
            if idx >= 0:
                self.combo_target.setCurrentIndex(idx)
            self.edit_page.setText(str(page_id))
            self.edit_page.setVisible(target == "goto_page")
        finally:
            self.combo_target.blockSignals(False)
            self.edit_page.blockSignals(False)

    def get_params(self) -> dict[str, Any]:
        cmd = self.combo_target.currentData() or "next_page"
        res: dict[str, Any] = {"target": cmd}
        if cmd == "goto_page":
            res["page_id"] = self.edit_page.text().strip()
        return res

    def retranslate_ui(self) -> None:
        self.combo_target.blockSignals(True)
        try:
            for i, (_cmd, loc_key) in enumerate(self.NAV_COMMANDS):
                self.combo_target.setItemText(i, t(loc_key))
        finally:
            self.combo_target.blockSignals(False)
        self.edit_page.setPlaceholderText(t("deck.editor.inspector.fields.page_id"))


class MacroSubform(QWidget):
    """Подформа 7: Заготовка-заглушка будущего редактора макро-цепочек (28 px)."""

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

        self.lbl_icon = QLabel("🔀", self.banner)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(self.lbl_icon)

        self.lbl_hint = QLabel(self.banner)
        self.lbl_hint.setObjectName("lblInspectorNoParamsHint")
        self.lbl_hint.setProperty("class", "InspectorFieldHint")
        banner_layout.addWidget(self.lbl_hint, 1)

        layout.addWidget(self.banner)
        self.retranslate_ui()

    def set_params(self, _params: dict[str, Any]) -> None:
        pass

    def retranslate_ui(self) -> None:
        self.lbl_hint.setText(t("deck.editor.inspector.hints.macro_wip"))


class UnconfiguredSubform(QWidget):
    """Подформа 8: Нейтральное состояние неконфигурированного слота (28 px)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(INPUT_HEIGHT)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.lbl_hint = QLabel(self)
        self.lbl_hint.setObjectName("lblUnconfiguredHint")
        self.lbl_hint.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
        self.lbl_hint.setText(t("deck.editor.inspector.unconfigured_hint"))
        self.lbl_hint.setFocusPolicy(Qt.NoFocus)

        layout.addWidget(self.lbl_hint, 1)

    def retranslate_ui(self) -> None:
        self.lbl_hint.setText(t("deck.editor.inspector.unconfigured_hint"))


# Семантические псевдонимы
PathUrlSubform = LaunchSubform
MultimediaSubform = MediaSubform
TextMacroSubform = TextSubform
NoParamsSubform = MacroSubform


class ButtonPropertyForm(QWidget):
    """
    Форма редактирования свойств кнопки сетки DuckDeck (0..9).
    Содержит 8 чистых подформ под 8 базовых примитивов + UnconfiguredSubform (index 8).
    """

    property_changed = Signal(str, object)
    delete_requested = Signal()
    test_action_requested = Signal(int)
    save_to_library_requested = Signal()
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
        self._is_unconfigured: bool = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 14)
        root_layout.setSpacing(8)

        # 1. Шапка формы
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_category = QLabel(self._current_category_raw, self)
        self.lbl_category.setObjectName("lblInspectorCategory")
        self.lbl_category.setProperty("class", "InspectorCategoryLabel")

        self.btn_save_to_library = QPushButton("⭐", self)
        self.btn_save_to_library.setObjectName("btnSaveToLibrary")
        self.btn_save_to_library.setProperty("class", "InspectorSaveToLibraryButton")
        self.btn_save_to_library.setFixedSize(28, 28)
        self.btn_save_to_library.setCursor(Qt.PointingHandCursor)
        self.btn_save_to_library.setFocusPolicy(Qt.NoFocus)
        self.btn_save_to_library.clicked.connect(self.save_to_library_requested.emit)

        self.btn_test = QPushButton("▶", self)
        self.btn_test.setObjectName("btnInspectorTest")
        self.btn_test.setProperty("class", "InspectorTestButton")
        self.btn_test.setFixedSize(28, 28)
        self.btn_test.setCursor(Qt.PointingHandCursor)
        self.btn_test.setFocusPolicy(Qt.NoFocus)
        self.btn_test.clicked.connect(lambda: self.test_action_requested.emit(self._slot_index))

        self.btn_delete = QPushButton("🗑️", self)
        self.btn_delete.setObjectName("btnInspectorDelete")
        self.btn_delete.setProperty("class", "InspectorDeleteButton")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFocusPolicy(Qt.NoFocus)
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        header_layout.addWidget(self.lbl_category)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_save_to_library)
        header_layout.addWidget(self.btn_test)
        header_layout.addWidget(self.btn_delete)
        root_layout.addLayout(header_layout)

        # Разделитель HLine
        separator = QFrame(self)
        separator.setObjectName("formSeparator")
        separator.setProperty("class", "FormSeparator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setFixedHeight(1)
        root_layout.addWidget(separator)

        # 2. Содержимое формы
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 2, 0, 2)
        content_layout.setSpacing(12)

        # Левая колонка: Превью-плитка + Стрип цвета акцента
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

        # Вертикальный разделитель между колонкой превью и сеткой параметров
        self.vertical_separator = QFrame(self)
        self.vertical_separator.setObjectName("formVerticalSeparator")
        self.vertical_separator.setFrameShape(QFrame.VLine)
        self.vertical_separator.setFrameShadow(QFrame.Plain)
        self.vertical_separator.setFixedWidth(1)
        content_layout.addWidget(self.vertical_separator)

        # Справа: сетка параметров (Title, Actions, Params Stack, Live Status & Sound)
        fields_grid = QGridLayout()
        fields_grid.setContentsMargins(0, 0, 0, 0)
        fields_grid.setVerticalSpacing(6)
        fields_grid.setHorizontalSpacing(8)
        fields_grid.setColumnMinimumWidth(0, FORM_LABEL_WIDTH)

        # Строка 0: Title
        self.lbl_title_field = QLabel(self)
        self.lbl_title_field.setObjectName("lblTitleField")
        self.lbl_title_field.setProperty("class", "InspectorFieldLabel")

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
        self.btn_font.setFocusPolicy(Qt.NoFocus)
        self.btn_font.clicked.connect(self._show_font_popover)

        fields_grid.addWidget(self.lbl_title_field, 0, 0, Qt.AlignVCenter)
        fields_grid.addWidget(self.edit_title, 0, 1)
        fields_grid.addWidget(self.btn_font, 0, 2)

        # Строка 1: Actions (ровно 8 чистых примитивов)
        self.lbl_actions_field = QLabel(self)
        self.lbl_actions_field.setObjectName("lblActionsField")
        self.lbl_actions_field.setProperty("class", "InspectorFieldLabel")

        self.combo_actions = QComboBox(self)
        self.combo_actions.setObjectName("comboActions")
        self.combo_actions.setFixedHeight(INPUT_HEIGHT)
        self.combo_actions.setCursor(Qt.PointingHandCursor)
        self.combo_actions.setFocusPolicy(Qt.NoFocus)
        for key in ACTION_PRIMITIVE_KEYS:
            self.combo_actions.addItem(t(f"deck.editor.primitives.{key}"), key)
        self.combo_actions.currentIndexChanged.connect(self._on_action_type_changed)

        fields_grid.addWidget(self.lbl_actions_field, 1, 0, Qt.AlignVCenter)
        fields_grid.addWidget(self.combo_actions, 1, 1, 1, 2)

        # Строка 2: Params (8 подформ 0..7 + UnconfiguredSubform на индексе 8)
        self.lbl_params_field = QLabel(self)
        self.lbl_params_field.setObjectName("lblParamsField")
        self.lbl_params_field.setProperty("class", "InspectorFieldLabel")
        self.lbl_hotkey_field = self.lbl_params_field

        params_container = QWidget(self)
        params_container.setFixedHeight(INPUT_HEIGHT)
        self.params_stack = QStackedLayout(params_container)
        self.params_stack.setContentsMargins(0, 0, 0, 0)

        self.subform_hotkey = HotkeySubform(params_container)
        self.subform_launch = LaunchSubform(params_container)
        self.subform_audio = AudioSubform(params_container)
        self.subform_media = MediaSubform(params_container)
        self.subform_text = TextSubform(params_container)
        self.subform_system = SystemSubform(params_container)
        self.subform_deck_nav = DeckNavSubform(params_container)
        self.subform_macro = MacroSubform(params_container)
        self.subform_unconfigured = UnconfiguredSubform(params_container)

        self.subform_hotkey.hotkey_changed.connect(
            lambda hk: self.property_changed.emit("hotkey", hk)
        )
        self.subform_hotkey.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_launch.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_audio.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_media.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_text.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_system.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )
        self.subform_deck_nav.params_changed.connect(
            lambda p: self.property_changed.emit("action_params", p)
        )

        self.params_stack.addWidget(self.subform_hotkey)        # Index 0
        self.params_stack.addWidget(self.subform_launch)        # Index 1
        self.params_stack.addWidget(self.subform_audio)         # Index 2
        self.params_stack.addWidget(self.subform_media)         # Index 3
        self.params_stack.addWidget(self.subform_text)          # Index 4
        self.params_stack.addWidget(self.subform_system)        # Index 5
        self.params_stack.addWidget(self.subform_deck_nav)      # Index 6
        self.params_stack.addWidget(self.subform_macro)         # Index 7
        self.params_stack.addWidget(self.subform_unconfigured)  # Index 8

        fields_grid.addWidget(self.lbl_params_field, 2, 0, Qt.AlignVCenter)
        fields_grid.addWidget(params_container, 2, 1, 1, 2)

        # Горизонтальный суб-разделитель перед строкой обратной связи
        self.feedback_separator = QFrame(self)
        self.feedback_separator.setObjectName("feedbackSeparator")
        self.feedback_separator.setFrameShape(QFrame.HLine)
        self.feedback_separator.setFrameShadow(QFrame.Plain)
        self.feedback_separator.setFixedHeight(1)
        fields_grid.addWidget(self.feedback_separator, 3, 0, 1, 3)

        # Строка 3 (row=4 в grid): Живой статус (Live Status) & Звук клика (sound_override)
        self.lbl_status_field = QLabel(self)
        self.lbl_status_field.setObjectName("lblStatusField")
        self.lbl_status_field.setProperty("class", "InspectorFieldLabel")

        row3_container = QWidget(self)
        row3_container.setFixedHeight(INPUT_HEIGHT)
        row3_layout = QHBoxLayout(row3_container)
        row3_layout.setContentsMargins(0, 0, 0, 0)
        row3_layout.setSpacing(16)

        # Левая половина: Живой статус
        self.status_subgroup = QWidget(row3_container)
        status_sub_layout = QHBoxLayout(self.status_subgroup)
        status_sub_layout.setContentsMargins(0, 0, 0, 0)
        status_sub_layout.setSpacing(6)

        self.combo_status_source = QComboBox(self.status_subgroup)
        self.combo_status_source.setFixedHeight(INPUT_HEIGHT)
        self.combo_status_source.setCursor(Qt.PointingHandCursor)
        self.combo_status_source.setFocusPolicy(Qt.NoFocus)
        for key in STATUS_SOURCE_KEYS:
            self.combo_status_source.addItem(
                t(f"deck.editor.inspector.status_sources.{key}"), key
            )
        self.combo_status_source.currentIndexChanged.connect(self._on_status_source_changed)
        status_sub_layout.addWidget(self.combo_status_source, 1)

        # Правая половина: Звук клика + фиксированные кнопки 28x28
        self.sound_group_container = QWidget(row3_container)
        sound_sub_layout = QHBoxLayout(self.sound_group_container)
        sound_sub_layout.setContentsMargins(0, 0, 0, 0)
        sound_sub_layout.setSpacing(6)

        self.lbl_click_sound_field = QLabel(self.sound_group_container)
        self.lbl_click_sound_field.setObjectName("lblClickSoundField")
        self.lbl_click_sound_field.setProperty("class", "InspectorFieldLabel")

        self.combo_click_sound = QComboBox(self.sound_group_container)
        self.combo_click_sound.setFixedHeight(INPUT_HEIGHT)
        self.combo_click_sound.setCursor(Qt.PointingHandCursor)
        self.combo_click_sound.setFocusPolicy(Qt.NoFocus)
        for key in CLICK_SOUND_KEYS:
            self.combo_click_sound.addItem(
                t(f"deck.editor.inspector.fields.click_sound_{key}"), key
            )
        self.combo_click_sound.currentIndexChanged.connect(self._on_click_sound_changed)

        self.btn_click_sound_browse = QPushButton("📁", self.sound_group_container)
        self.btn_click_sound_browse.setFixedSize(28, 28)
        self.btn_click_sound_browse.setCursor(Qt.PointingHandCursor)
        self.btn_click_sound_browse.setFocusPolicy(Qt.NoFocus)
        self.btn_click_sound_browse.clicked.connect(self._on_click_sound_browse_clicked)
        self.btn_click_sound_browse.setVisible(False)

        self.btn_click_sound_preview = QPushButton("▶", self.sound_group_container)
        self.btn_click_sound_preview.setProperty("class", "InspectorTestButton")
        self.btn_click_sound_preview.setFixedSize(28, 28)
        self.btn_click_sound_preview.setCursor(Qt.PointingHandCursor)
        self.btn_click_sound_preview.setFocusPolicy(Qt.NoFocus)
        self.btn_click_sound_preview.clicked.connect(self._on_click_sound_preview_clicked)
        self.btn_click_sound_preview.setVisible(False)

        sound_sub_layout.addWidget(self.lbl_click_sound_field)
        sound_sub_layout.addWidget(self.combo_click_sound, 1)
        sound_sub_layout.addWidget(self.btn_click_sound_browse)
        sound_sub_layout.addWidget(self.btn_click_sound_preview)

        row3_layout.addWidget(self.status_subgroup, 1)
        row3_layout.addWidget(self.sound_group_container, 1)

        fields_grid.addWidget(self.lbl_status_field, 4, 0, Qt.AlignVCenter)
        fields_grid.addWidget(row3_container, 4, 1, 1, 2)

        content_layout.addLayout(fields_grid)
        root_layout.addLayout(content_layout)
        root_layout.addStretch(1)

        # Совместимость для тестов, обращающихся к btn_hotkey
        self.btn_hotkey = self.subform_hotkey.btn_hotkey

        self.retranslate_ui()

    def set_audio_devices(self, devices: list[tuple[str, str]]) -> None:
        """DI-метод передачи списка доступных аудиоустройств в AudioSubform."""
        self.subform_audio.set_audio_devices(devices)

    def set_category(self, category: str) -> None:
        self._current_category_raw = category
        self.lbl_category.setText(category)

    def get_category(self) -> str:
        return self._current_category_raw

    @staticmethod
    def resolve_subform_route(
        action_type: str, params: Optional[dict[str, Any]] = None
    ) -> tuple[int, str, dict[str, Any]]:
        """
        Прямая детерминированная маршрутизация подформ инспектора (0..7 для 8 примитивов, 8 для unconfigured).
        """
        raw = (action_type or "").strip().lower().replace(" ", "_")
        p: dict[str, Any] = dict(params) if params else {}

        if raw in ("unconfigured", "none", ""):
            return 8, "unconfigured", p

        if raw in ("hotkey", "shortcut", "hotkey_switch"):
            if raw == "hotkey_switch":
                p.setdefault("mode", "toggle")
            return 0, "hotkey", p

        if raw in ("launch", "website", "open_website", "web", "url", "open_app", "open_application", "open_path", "http_request"):
            if raw in ("website", "open_website", "web", "url", "http_request"):
                p.setdefault("kind", "url")
                if "url" in p and "target" not in p:
                    p["target"] = p["url"]
            elif raw == "open_path":
                p.setdefault("kind", "file")
                if "path" in p and "target" not in p:
                    p["target"] = p["path"]
            elif raw in ("open_app", "open_application"):
                p.setdefault("kind", "app")
                if "executable" in p and "target" not in p:
                    p["target"] = p["executable"]
            return 1, "launch", p

        if raw in (
            "audio",
            "volume_control",
            "audio_device",
            "auto_software_vol",
            "master_volume_control",
            "mic_mute_control",
            "mute_audio",
            "volume_up",
            "volume_down",
            "output_device_toggle",
            "toggle_device",
        ):
            if raw in ("output_device_toggle", "toggle_device", "audio_device"):
                p.setdefault("target", "device")
                p.setdefault("command", "toggle_device")
                p.setdefault("mode", "toggle")
            elif raw == "auto_software_vol":
                p.setdefault("target", "focus_app")
                p.setdefault("command", "toggle_mute")
            elif raw in ("master_volume_control", "mute_audio"):
                p.setdefault("target", "master")
                p.setdefault("command", "toggle_mute")
            elif raw == "mic_mute_control":
                p.setdefault("target", "mic")
                p.setdefault("command", "toggle_mute")
            elif raw == "volume_up":
                p.setdefault("target", "master")
                p.setdefault("command", "volume_up")
            elif raw == "volume_down":
                p.setdefault("target", "master")
                p.setdefault("command", "volume_down")
            return 2, "audio", p

        if raw in ("media", "multimedia", "media_control"):
            return 3, "media", p

        if raw in ("text", "text_macro", "macro_text", "paste_text"):
            return 4, "text", p

        if raw in (
            "system",
            "system_command",
            "screenshot",
            "close_window",
            "dimmer",
            "toggle_dimmer",
            "lock_pc",
            "lock_workstation",
            "sleep_display",
        ):
            if raw == "screenshot":
                p.setdefault("command", "screenshot")
            elif raw == "close_window":
                p.setdefault("command", "close_window")
            elif raw in ("dimmer", "toggle_dimmer"):
                p.setdefault("command", "toggle_dimmer")
            elif raw in ("lock_pc", "lock_workstation"):
                p.setdefault("command", "lock_workstation")
            elif raw == "sleep_display":
                p.setdefault("command", "sleep_display")
            return 5, "system", p

        if raw in ("deck_nav", "navigation", "prev_page", "next_page", "goto_page", "folder_back"):
            if raw in ("prev_page", "next_page", "goto_page", "folder_back"):
                p.setdefault("target", raw)
            return 6, "deck_nav", p

        if raw in ("macro", "multi_action", "multi_action_switch"):
            return 7, "macro", p

        return 8, "unconfigured", p

    @staticmethod
    def _default_params_for_type(action_key: Optional[str]) -> dict[str, Any]:
        """Возвращает эталонные дефолтные параметры для 8 базовых примитивов."""
        key = (action_key or "").strip().lower()
        if key == "hotkey":
            return {"mode": "press", "keys": [], "toggle_keys": []}
        if key == "launch":
            return {"kind": "app", "target": ""}
        if key == "audio":
            return {"target": "master", "command": "toggle_mute", "step_percent": 5}
        if key == "media":
            return {"command": "play_pause"}
        if key == "text":
            return {"text": "", "send_enter": False}
        if key == "system":
            return {"command": "toggle_dimmer"}
        if key == "deck_nav":
            return {"target": "next_page"}
        if key == "macro":
            return {"steps": [], "delay_ms": 50}
        return {}

    def _reset_inactive_subforms(self, active_stack_idx: int) -> None:
        subforms = (
            (0, self.subform_hotkey),
            (1, self.subform_launch),
            (2, self.subform_audio),
            (3, self.subform_media),
            (4, self.subform_text),
            (5, self.subform_system),
            (6, self.subform_deck_nav),
            (7, self.subform_macro),
        )
        for idx, subform in subforms:
            if idx != active_stack_idx:
                subform.set_params({})

    def _apply_params_to_subform(
        self, stack_idx: int, params: dict[str, Any], hotkey: str = ""
    ) -> None:
        if stack_idx == 0:
            merged = dict(params)
            if not merged.get("keys") and hotkey:
                merged["keys"] = _parse_keys_list(hotkey)
            self.subform_hotkey.set_params(merged)
            if hotkey and merged.get("mode", "press") == "press":
                self.subform_hotkey.set_hotkey(hotkey)
        elif stack_idx == 1:
            self.subform_launch.set_params(params)
        elif stack_idx == 2:
            self.subform_audio.set_params(params)
        elif stack_idx == 3:
            self.subform_media.set_params(params)
        elif stack_idx == 4:
            self.subform_text.set_params(params)
        elif stack_idx == 5:
            self.subform_system.set_params(params)
        elif stack_idx == 6:
            self.subform_deck_nav.set_params(params)
        elif stack_idx == 7:
            self.subform_macro.set_params(params)

    def get_slot_index(self) -> int:
        return self._slot_index

    def load_slot_data(self, dto: ButtonSlotDTO) -> None:
        self._slot_index = dto.slot_index

        self.edit_title.blockSignals(True)
        self.combo_actions.blockSignals(True)
        self.btn_hotkey.blockSignals(True)
        try:
            is_empty = (
                not dto.title
                and (not dto.action_type or dto.action_type.lower() in ("none", "unconfigured", ""))
                and not dto.hotkey
            )
            self._is_unconfigured = is_empty
            if is_empty:
                self.set_category(t("deck.editor.inspector.unconfigured_title"))
                self.edit_title.setText("")
                self.edit_title.setPlaceholderText(t("deck.editor.inspector.unconfigured_placeholder"))
                self.preview_tile.set_icon("➕")
                self.btn_save_to_library.setEnabled(False)
                self.btn_test.setEnabled(False)
                self.btn_delete.setEnabled(False)
                self._update_subform_visibility("unconfigured")
                return

            self.btn_save_to_library.setEnabled(True)
            self.btn_test.setEnabled(True)
            self.btn_delete.setEnabled(True)

            category_text = dto.category if dto.category else "System: Hotkey"
            self.set_category(category_text)
            self.edit_title.setText(dto.title)

            self._current_font_size = dto.font_size if hasattr(dto, "font_size") else 11
            self._current_font_color = dto.font_color if hasattr(dto, "font_color") else "#d4d4d8"
            self._current_text_alignment = dto.text_alignment if hasattr(dto, "text_alignment") else "bottom"
            self._current_hide_title = bool(dto.hide_title) if hasattr(dto, "hide_title") else False

            accent_col = dto.color_accent or ACCENT_COLORS[0]
            self.accent_picker.set_color(accent_col)

            src_val = dto.status_source or "none"
            self.combo_status_source.blockSignals(True)
            try:
                idx_s = self.combo_status_source.findData(src_val)
                self.combo_status_source.setCurrentIndex(idx_s if idx_s >= 0 else 0)
            finally:
                self.combo_status_source.blockSignals(False)

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

                idx_snd = self.combo_click_sound.findData(target_mode)
                if idx_snd >= 0:
                    self.combo_click_sound.setCurrentIndex(idx_snd)
            finally:
                self.combo_click_sound.blockSignals(False)

            stack_idx, prim_type, mapped_params = self.resolve_subform_route(
                dto.action_type, dto.action_params
            )

            target_idx = self.combo_actions.findData(prim_type)
            self.combo_actions.setCurrentIndex(target_idx if target_idx >= 0 else 0)
            self.params_stack.setCurrentIndex(stack_idx)
            if stack_idx == 0:
                self.lbl_params_field.setText(t("deck.editor.inspector.fields.hotkey"))
            else:
                self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))

            self._reset_inactive_subforms(stack_idx)
            self._apply_params_to_subform(stack_idx, mapped_params, hotkey=dto.hotkey)
            self.preview_tile.set_icon(dto.icon)
        finally:
            self.edit_title.blockSignals(False)
            self.combo_actions.blockSignals(False)
            self.btn_hotkey.blockSignals(False)

    def retranslate_ui(self) -> None:
        self.btn_save_to_library.setToolTip(t("deck.editor.inspector.save_to_library_tooltip"))
        self.btn_delete.setToolTip(t("deck.editor.inspector.tooltips.delete_action"))
        self.btn_test.setToolTip(t("deck.editor.inspector.tooltips.test_action"))

        self.lbl_title_field.setText(t("deck.editor.inspector.fields.title"))
        self.lbl_actions_field.setText(t("deck.editor.inspector.fields.actions"))
        self.lbl_status_field.setText(t("deck.editor.inspector.fields.status_source"))
        self.lbl_click_sound_field.setText(t("deck.editor.inspector.fields.click_sound"))
        self.btn_font.setToolTip(t("deck.editor.font_popover.title"))
        self.btn_click_sound_browse.setToolTip(t("deck.editor.inspector.fields.sound_file"))
        self.btn_click_sound_preview.setToolTip(t("deck.editor.inspector.tooltips.test_action"))

        curr_action = self.combo_actions.currentData()
        if curr_action == "hotkey":
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.hotkey"))
        else:
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))

        if getattr(self, "_is_unconfigured", False):
            self.lbl_category.setText(t("deck.editor.inspector.unconfigured_title"))
            self.edit_title.setPlaceholderText(t("deck.editor.inspector.unconfigured_placeholder"))

        self.combo_actions.blockSignals(True)
        try:
            for i in range(self.combo_actions.count()):
                key = self.combo_actions.itemData(i)
                if key:
                    self.combo_actions.setItemText(i, t(f"deck.editor.primitives.{key}"))
        finally:
            self.combo_actions.blockSignals(False)

        self.combo_status_source.blockSignals(True)
        try:
            for i in range(self.combo_status_source.count()):
                key = self.combo_status_source.itemData(i)
                if key:
                    self.combo_status_source.setItemText(i, t(f"deck.editor.inspector.status_sources.{key}"))
        finally:
            self.combo_status_source.blockSignals(False)

        self.combo_click_sound.blockSignals(True)
        try:
            for i in range(self.combo_click_sound.count()):
                key = self.combo_click_sound.itemData(i)
                if key:
                    self.combo_click_sound.setItemText(i, t(f"deck.editor.inspector.fields.click_sound_{key}"))
        finally:
            self.combo_click_sound.blockSignals(False)

        self.preview_tile.retranslate_ui()
        self.subform_hotkey.retranslate_ui()
        self.subform_launch.retranslate_ui()
        self.subform_audio.retranslate_ui()
        self.subform_media.retranslate_ui()
        self.subform_text.retranslate_ui()
        self.subform_system.retranslate_ui()
        self.subform_deck_nav.retranslate_ui()
        self.subform_macro.retranslate_ui()
        self.subform_unconfigured.retranslate_ui()
        if self._font_popover is not None:
            self._font_popover.retranslate_ui()

    def _update_subform_visibility(self, action_key: Optional[str]) -> None:
        stack_idx, _prim, _p = self.resolve_subform_route(action_key or "unconfigured")
        self.params_stack.setCurrentIndex(stack_idx)
        if stack_idx == 0:
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.hotkey"))
        else:
            self.lbl_params_field.setText(t("deck.editor.inspector.fields.params"))

    def is_unconfigured(self) -> bool:
        return getattr(self, "_is_unconfigured", False)

    def _on_delete_clicked(self) -> None:
        self._is_unconfigured = True
        self.set_category(t("deck.editor.inspector.unconfigured_title"))
        self.edit_title.setText("")
        self.edit_title.setPlaceholderText(t("deck.editor.inspector.unconfigured_placeholder"))
        self.preview_tile.set_icon("➕")
        self.btn_save_to_library.setEnabled(False)
        self.btn_test.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self._update_subform_visibility("unconfigured")
        self.delete_requested.emit()

    def _show_font_popover(self) -> None:
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
        source_key = self.combo_status_source.itemData(index) or "none"
        self.property_changed.emit("status_source", source_key)

    def _on_click_sound_changed(self, index: int) -> None:
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
        from modules.deck.sound_engine import DeckSoundEngine

        target = self._sound_override_path
        if target and os.path.exists(target):
            DeckSoundEngine.preview_sound(target, 1.0)
        else:
            DeckSoundEngine.play_tap()

    def _on_action_type_changed(self, index: int) -> None:
        prim_key = str(self.combo_actions.itemData(index) or ACTION_PRIMITIVE_KEYS[0])
        default_params = self._default_params_for_type(prim_key)

        self._update_subform_visibility(prim_key)
        stack_idx = self.params_stack.currentIndex()
        self._reset_inactive_subforms(stack_idx)
        self._apply_params_to_subform(stack_idx, default_params)

        if prim_key != "hotkey":
            self.subform_hotkey.set_hotkey("")
            self.property_changed.emit("hotkey", "")
        self.property_changed.emit("action_type", prim_key)
        self.property_changed.emit("action_params", default_params)

    def _on_color_accent_changed(self, hex_color: str) -> None:
        self.property_changed.emit("color_accent", hex_color)

    def _open_icon_library_dialog(self) -> None:
        from modules.deck.editor.widgets.icon_library_dialog import IconLibraryDialog

        dialog = IconLibraryDialog(parent=self.window(), current_icon=self.preview_tile.get_icon())
        if dialog.exec() == QDialog.Accepted:
            selected_icon = dialog.get_selected_icon()
            if selected_icon is not None:
                self.preview_tile.set_icon(selected_icon)
                self.property_changed.emit("icon", selected_icon)

    def _on_icon_selected_directly(self, icon_str_or_path: str) -> None:
        self.preview_tile.set_icon(icon_str_or_path)
        self.property_changed.emit("icon", icon_str_or_path)


__all__ = [
    "ACCENT_COLORS",
    "ACTION_PRIMITIVE_KEYS",
    "STATUS_SOURCE_KEYS",
    "CLICK_SOUND_KEYS",
    "HOTKEY_MODE_KEYS",
    "LAUNCH_KIND_KEYS",
    "AUDIO_CATEGORY_KEYS",
    "MEDIA_COMMAND_KEYS",
    "VOLUME_TARGET_KEYS",
    "VOLUME_ACTION_KEYS",
    "AUDIO_DEVICE_MODE_KEYS",
    "SCREENSHOT_TARGET_KEYS",
    "SYSTEM_COMMAND_KEYS",
    "ColorAccentPicker",
    "HotkeySubform",
    "LaunchSubform",
    "PathUrlSubform",
    "AudioSubform",
    "MediaSubform",
    "MultimediaSubform",
    "TextSubform",
    "TextMacroSubform",
    "SystemSubform",
    "DeckNavSubform",
    "MacroSubform",
    "NoParamsSubform",
    "UnconfiguredSubform",
    "ButtonPropertyForm",
]
