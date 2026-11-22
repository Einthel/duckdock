"""
Модульные тесты динамических подформ инспектора свойств (ButtonPropertyForm) согласно шагу 5.3.
Проверяет:
  - test_property_form_stacked_layout_switching
  - test_property_form_color_accent_picker
  - test_property_form_retranslate_preserves_inputs
"""
from typing import Any
import pytest
from PySide6.QtWidgets import QApplication

from core.i18n import I18nManager, t
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.styles import INSPECTOR_HEIGHT
from modules.deck.editor.widgets.button_property_form import (
    ACCENT_COLORS,
    ButtonPropertyForm,
)


def test_property_form_stacked_layout_switching(qapp: QApplication) -> None:
    """Смена типа действия переключает подформу в QStackedLayout с сохранением высоты 220 px."""
    form = ButtonPropertyForm()

    # По умолчанию: hotkey (индекс 0)
    assert form.params_stack.currentIndex() == 0

    actions_to_check = [
        ("hotkey_switch", 1),
        ("website", 2),
        ("open_app", 2),
        ("multimedia", 3),
        ("text_macro", 4),
        ("volume_control", 5),
    ]

    for action_id, expected_stack_idx in actions_to_check:
        combo_idx = form.combo_actions.findData(action_id)
        assert combo_idx >= 0, f"Действие {action_id} не найдено в комбобоксе"
        form.combo_actions.setCurrentIndex(combo_idx)
        assert form.params_stack.currentIndex() == expected_stack_idx
        assert form.height() == INSPECTOR_HEIGHT == 260


def test_property_form_color_accent_picker(qapp: QApplication) -> None:
    """Выбор цвета в ColorAccentPicker обновляет свойство и эмитирует сигнал."""
    form = ButtonPropertyForm()
    emitted = []
    form.property_changed.connect(lambda k, v: emitted.append((k, v)))

    assert len(ACCENT_COLORS) >= 5
    # Выбираем второй цвет (Emerald)
    target_color = ACCENT_COLORS[1]
    form.accent_picker._on_color_clicked(target_color)

    assert form.accent_picker.get_color() == target_color
    assert ("color_accent", target_color) in emitted


def test_property_form_retranslate_preserves_inputs(qapp: QApplication) -> None:
    """Смена языка интерфейса обновляет надписи подформ без потери введенных данных."""
    form = ButtonPropertyForm()
    mgr = I18nManager()
    orig_lang = mgr.current_language

    try:
        # Настраиваем слот с Website
        dto = ButtonSlotDTO(
            slot_index=0,
            title="My Portal",
            action_type="website",
            action_params={"url": "https://duckdock.dev"},
            color_accent="#38bdf8",
        )
        form.load_slot_data(dto)

        assert form.edit_title.text() == "My Portal"
        assert form.subform_path_url.get_path_or_url() == "https://duckdock.dev"

        # Переключаем язык на русский
        mgr.set_language("ru", emit_signal=False)
        form.retranslate_ui()

        # Данные сохранены
        assert form.edit_title.text() == "My Portal"
        assert form.subform_path_url.get_path_or_url() == "https://duckdock.dev"
        assert form.lbl_title_field.text() == "Название:"

        # Переключаем язык на английский
        mgr.set_language("en", emit_signal=False)
        form.retranslate_ui()

        assert form.edit_title.text() == "My Portal"
        assert form.subform_path_url.get_path_or_url() == "https://duckdock.dev"
        assert form.lbl_title_field.text() == "Title:"
    finally:
        mgr.set_language(orig_lang, emit_signal=False)


def test_path_url_subform_truthy_fallback(qapp: QApplication) -> None:
    """Проверка truthy-выборки параметров в PathUrlSubform: 'path' используется при пустом 'executable'."""
    form = ButtonPropertyForm()
    dto = ButtonSlotDTO(
        slot_index=0,
        title="Notepad",
        action_type="open_app",
        action_params={"executable": "", "path": "notepad.exe"},
    )
    form.load_slot_data(dto)
    assert form.subform_path_url.get_path_or_url() == "notepad.exe"


def test_no_params_subform_display(qapp: QApplication) -> None:
    """Для close_window отображается NoParamsSubform с подсказкой о ненадобности параметров."""
    form = ButtonPropertyForm()
    dto = ButtonSlotDTO(
        slot_index=0,
        title="Close App",
        action_type="close_window",
        action_params={},
    )
    form.load_slot_data(dto)
    assert form.params_stack.currentIndex() == 6
    assert form.subform_no_params.lbl_banner.text() == t("deck.editor.inspector.hints.no_params_required")


def test_volume_action_auto_mapping(qapp: QApplication) -> None:
    """Авто-маппинг всех 7 звуковых действий каталога в volume_control и audio_device."""
    form = ButtonPropertyForm()
    volume_actions = [
        ("auto_software_vol", "volume_control", {"target": "focus_app", "command": "toggle_mute"}),
        ("master_volume_control", "volume_control", {"target": "master", "command": "toggle_mute"}),
        ("mic_mute_control", "volume_control", {"target": "microphone", "command": "toggle_mute"}),
        ("mute_audio", "volume_control", {"target": "master", "command": "toggle_mute"}),
        ("volume_up", "volume_control", {"target": "master", "command": "volume_up"}),
        ("volume_down", "volume_control", {"target": "master", "command": "volume_down"}),
        ("toggle_device", "audio_device", {"mode": "toggle"}),
    ]
    for raw_action, expected_type, expected_params in volume_actions:
        dto = ButtonSlotDTO(
            slot_index=0,
            title="Vol Test",
            action_type=raw_action,
            action_params={},
        )
        form.load_slot_data(dto)
        assert form.combo_actions.currentData() == expected_type
        if expected_type == "volume_control":
            p = form.subform_volume.get_params()
            assert p["target"] == expected_params["target"]
            if "command" in expected_params:
                assert p["command"] == expected_params["command"]
        elif expected_type == "audio_device":
            assert form.subform_audio_device.get_params()["mode"] == expected_params["mode"]


def test_audio_device_screenshot_system_subforms(qapp: QApplication) -> None:
    """Проверка переключения и установки параметров для подформ audio_device, screenshot и system."""
    form = ButtonPropertyForm()

    # Audio device
    dto_audio = ButtonSlotDTO(slot_index=0, action_type="audio_device", action_params={"mode": "specific", "device": "Headphones"})
    form.load_slot_data(dto_audio)
    assert form.params_stack.currentIndex() == 7
    assert form.subform_audio_device.get_params()["mode"] == "specific"

    # Screenshot
    dto_sc = ButtonSlotDTO(slot_index=0, action_type="screenshot", action_params={"target": "active_window", "clipboard": True})
    form.load_slot_data(dto_sc)
    assert form.params_stack.currentIndex() == 8
    p = form.subform_screenshot.get_params()
    assert p["target"] == "active_window"
    assert p["clipboard"] is True

    # System
    dto_sys = ButtonSlotDTO(slot_index=0, action_type="system", action_params={"command": "lock_workstation"})
    form.load_slot_data(dto_sys)
    assert form.params_stack.currentIndex() == 9
    assert form.subform_system.get_params()["command"] == "lock_workstation"


def test_btn_test_action_requested(qapp: QApplication) -> None:
    """Клик по кнопке '▶ Тест' эмиттирует test_action_requested с текущим slot_index."""
    form = ButtonPropertyForm()
    dto = ButtonSlotDTO(slot_index=3, title="Test Button", action_type="toggle_dimmer")
    form.load_slot_data(dto)
    emitted = []
    form.test_action_requested.connect(lambda idx: emitted.append(idx))
    assert form.btn_test.toolTip() == t("deck.editor.inspector.tooltips.test_action")
    form.btn_test.click()
    assert emitted == [3]

