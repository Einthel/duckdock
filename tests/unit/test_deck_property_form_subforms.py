"""
Модульные тесты 8 чистых подформ инспектора свойств (ButtonPropertyForm) — Фаза 2.
Проверяет:
  - Прямую маршрутизацию resolve_subform_route (0..7 и 8 unconfigured)
  - Все 8 подформ (HotkeySubform, LaunchSubform, AudioSubform, MediaSubform, TextSubform, SystemSubform, DeckNavSubform, MacroSubform)
  - DI аудиоустройств в AudioSubform
  - Защиту от утечки параметров в DeckConfigAdapter и ButtonPropertyForm
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.i18n import I18nManager, t
from modules.deck.editor.adapter import DeckConfigAdapter
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.styles import INPUT_HEIGHT, INSPECTOR_HEIGHT
from modules.deck.editor.widgets.button_property_form import (
    ACCENT_COLORS,
    ACTION_PRIMITIVE_KEYS,
    AudioSubform,
    ButtonPropertyForm,
    DeckNavSubform,
    HotkeySubform,
    LaunchSubform,
    MacroSubform,
    MediaSubform,
    SystemSubform,
    TextSubform,
    UnconfiguredSubform,
)


def test_resolve_subform_route_matrix() -> None:
    """Проверка прямой маршрутизации resolve_subform_route для 8 примитивов (0..7) и unconfigured (8)."""
    assert ButtonPropertyForm.resolve_subform_route("hotkey", {"keys": ["ctrl", "c"]})[:2] == (0, "hotkey")
    assert ButtonPropertyForm.resolve_subform_route("hotkey", {"mode": "toggle", "keys": ["f1"], "toggle_keys": ["f2"]})[:2] == (0, "hotkey")
    assert ButtonPropertyForm.resolve_subform_route("launch", {"target": "https://google.com", "kind": "url"})[:2] == (1, "launch")
    assert ButtonPropertyForm.resolve_subform_route("audio", {"target": "master", "command": "toggle_mute"})[:2] == (2, "audio")
    assert ButtonPropertyForm.resolve_subform_route("audio", {"target": "device", "command": "toggle_device"})[:2] == (2, "audio")
    assert ButtonPropertyForm.resolve_subform_route("media", {"command": "play_pause"})[:2] == (3, "media")
    assert ButtonPropertyForm.resolve_subform_route("text", {"text": "hi"})[:2] == (4, "text")
    assert ButtonPropertyForm.resolve_subform_route("system", {"command": "toggle_dimmer"})[:2] == (5, "system")
    assert ButtonPropertyForm.resolve_subform_route("system", {"command": "screenshot"})[:2] == (5, "system")
    assert ButtonPropertyForm.resolve_subform_route("system", {"command": "close_window"})[:2] == (5, "system")
    assert ButtonPropertyForm.resolve_subform_route("deck_nav", {"target": "next_page"})[:2] == (6, "deck_nav")
    assert ButtonPropertyForm.resolve_subform_route("macro", {"steps": []})[:2] == (7, "macro")
    assert ButtonPropertyForm.resolve_subform_route("unconfigured", {})[:2] == (8, "unconfigured")


def test_hotkey_subform_press_and_toggle(qapp: QApplication) -> None:
    """Проверка HotkeySubform в режимах press и toggle в рамках 28 px."""
    sub = HotkeySubform()
    assert sub.height() == INPUT_HEIGHT
    assert sub.combo_mode.focusPolicy() == Qt.NoFocus

    sub.set_params({"mode": "toggle", "keys": ["ctrl", "m"], "toggle_keys": ["ctrl", "u"]})
    assert sub.combo_mode.currentData() == "toggle"
    assert sub.lbl_arrow.isHidden() is False
    assert sub.btn_toggle_hotkey.isHidden() is False
    p = sub.get_params()
    assert p == {"mode": "toggle", "keys": ["ctrl", "m"], "toggle_keys": ["ctrl", "u"]}

    # Переключение в press скрывает второй хоткей
    idx_press = sub.combo_mode.findData("press")
    sub.combo_mode.setCurrentIndex(idx_press)
    assert sub.btn_toggle_hotkey.isHidden() is True
    assert sub.get_params()["mode"] == "press"


def test_launch_subform_kinds_and_browse_visibility(qapp: QApplication) -> None:
    """Проверка LaunchSubform: 3 типа (app, file, url) и скрытие кнопки обзора для url."""
    sub = LaunchSubform()
    assert sub.height() == INPUT_HEIGHT
    assert sub.combo_kind.focusPolicy() == Qt.NoFocus
    assert sub.btn_browse.focusPolicy() == Qt.NoFocus

    sub.set_params({"kind": "url", "target": "https://duckdock.dev"})
    assert sub.combo_kind.currentData() == "url"
    assert sub.btn_browse.isHidden() is True
    assert sub.get_params() == {"kind": "url", "target": "https://duckdock.dev"}

    sub.set_params({"kind": "app", "target": "wt.exe"})
    assert sub.combo_kind.currentData() == "app"
    assert sub.btn_browse.isHidden() is False
    assert sub.get_params() == {"kind": "app", "target": "wt.exe"}


def test_audio_subform_volume_and_device_di(qapp: QApplication) -> None:
    """Проверка AudioSubform: переключение volume/device и DI списка устройств."""
    sub = AudioSubform()
    sub.set_audio_devices([("id_hp", "Headphones"), ("id_spk", "Speakers")])
    assert sub.height() == INPUT_HEIGHT

    # Режим volume
    sub.set_params({"target": "focus_app", "command": "volume_up", "step_percent": 5})
    assert sub.combo_category.currentData() == "volume"
    assert sub.combo_target.currentData() == "focus_app"
    assert sub.combo_action.currentData() == "volume_up"
    assert sub.combo_device.isHidden() is True

    # Режим device -> set
    sub.set_params({"target": "device", "command": "set_device", "mode": "set", "target_device_id": "id_spk"})
    assert sub.combo_category.currentData() == "device"
    assert sub.combo_dev_mode.currentData() == "set"
    assert sub.combo_device.isHidden() is False
    assert sub.combo_device.currentData() == "id_spk"
    assert sub.get_params() == {
        "target": "device",
        "command": "set_device",
        "mode": "set",
        "target_device_id": "id_spk",
    }


def test_system_subform_5_commands_and_screenshot_options(qapp: QApplication) -> None:
    """Проверка SystemSubform: все 5 команд и показ опций скриншота только для screenshot."""
    sub = SystemSubform()
    assert sub.combo_cmd.count() == 5

    sub.set_params({"command": "toggle_dimmer"})
    assert sub.combo_screenshot_target.isHidden() is True
    assert sub.chk_clipboard.isHidden() is True

    sub.set_params({"command": "screenshot", "screenshot_target": "active_window", "clipboard": False})
    assert sub.combo_screenshot_target.isHidden() is False
    assert sub.chk_clipboard.isHidden() is False
    assert sub.get_params() == {
        "command": "screenshot",
        "screenshot_target": "active_window",
        "clipboard": False,
    }


def test_deck_nav_subform_lifecycle_and_signals(qapp: QApplication) -> None:
    """Проверка подформы навигации DeckNavSubform: команды, ввод page_id и Qt.NoFocus."""
    subform = DeckNavSubform()
    subform.show()
    assert subform.height() <= 56
    assert subform.combo_target.focusPolicy() == Qt.NoFocus
    assert subform.edit_page.isHidden() is True

    emitted_params = []
    subform.params_changed.connect(lambda p: emitted_params.append(p))

    idx_goto = subform.combo_target.findData("goto_page")
    subform.combo_target.setCurrentIndex(idx_goto)
    assert subform.edit_page.isHidden() is False

    subform.edit_page.setText("page_3")
    subform.edit_page.textEdited.emit("page_3")
    assert emitted_params[-1] == {"target": "goto_page", "page_id": "page_3"}

    idx_switch = subform.combo_target.findData("switch_profile")
    assert idx_switch >= 0
    assert subform.combo_target.model().item(idx_switch).isEnabled() is False


def test_unconfigured_subform_and_macro_subform(qapp: QApplication) -> None:
    """Проверка UnconfiguredSubform (без кнопки шаблонов) и MacroSubform."""
    unconf = UnconfiguredSubform()
    assert not hasattr(unconf, "btn_pick_preset")
    assert unconf.lbl_hint.text() == t("deck.editor.inspector.unconfigured_hint")

    macro = MacroSubform()
    assert macro.lbl_hint.text() == t("deck.editor.inspector.hints.macro_wip")


def test_btn_test_action_requested(qapp: QApplication) -> None:
    """Клик по кнопке '▶' эмиттирует test_action_requested с текущим slot_index."""
    form = ButtonPropertyForm()
    dto = ButtonSlotDTO(slot_index=3, title="Test Button", action_type="system", action_params={"command": "toggle_dimmer"})
    form.load_slot_data(dto)
    emitted = []
    form.test_action_requested.connect(lambda idx: emitted.append(idx))
    form.btn_test.click()
    assert emitted == [3]


def test_adapter_hotkey_toggle_preserved(qapp: QApplication) -> None:
    """Проверка сохранения mode='toggle' и toggle_keys у hotkey при конвертации dto_to_slot <-> slot_to_dto."""
    dto = ButtonSlotDTO(
        slot_index=0,
        title="Toggle HK",
        action_type="hotkey",
        hotkey="Ctrl + M",
        action_params={"mode": "toggle", "keys": ["ctrl", "m"], "toggle_keys": ["ctrl", "u"]},
    )
    btn = DeckConfigAdapter.dto_to_slot(dto)
    assert btn.action.action_type == "hotkey"
    assert btn.action.params["mode"] == "toggle"
    assert btn.action.params["keys"] == ["ctrl", "m"]
    assert btn.action.params["toggle_keys"] == ["ctrl", "u"]

    dto_back = DeckConfigAdapter.slot_to_dto(btn)
    assert dto_back.action_params["mode"] == "toggle"
    assert dto_back.action_params["toggle_keys"] == ["ctrl", "u"]


def test_subform_params_not_leaked_on_type_switch(qapp: QApplication) -> None:
    """Переключение с audio на system или launch не оставляет посторонних ключей."""
    form = ButtonPropertyForm()
    emitted: list[tuple[str, object]] = []
    form.property_changed.connect(lambda k, v: emitted.append((k, v)))

    form.load_slot_data(
        ButtonSlotDTO(
            slot_index=0,
            title="Mute",
            action_type="audio",
            action_params={"target": "master", "command": "toggle_mute", "step_percent": 5},
        )
    )
    emitted.clear()

    idx_sys = form.combo_actions.findData("system")
    form.combo_actions.setCurrentIndex(idx_sys)
    last_params = [v for k, v in emitted if k == "action_params"][-1]
    assert last_params == {"command": "toggle_dimmer"}

    orig_btn = DeckConfigAdapter.dto_to_slot(
        ButtonSlotDTO(
            slot_index=1,
            title="Audio",
            action_type="audio",
            action_params={"target": "master", "command": "toggle_mute", "step_percent": 5},
        )
    )
    dirty_dto = ButtonSlotDTO(
        slot_index=1,
        title="Launch",
        action_type="launch",
        action_params={"target": "master", "step_percent": 5},
        original_config=orig_btn,
    )
    res_btn = DeckConfigAdapter.dto_to_slot(dirty_dto)
    assert res_btn.action.action_type == "launch"
    assert res_btn.action.params.get("target") == ""
