"""
Модульные тесты формы инспектора свойств кнопки ButtonPropertyForm (v0.6.0).
Проверяет:
  - Соблюдение бюджета высоты (INSPECTOR_HEIGHT == 220 px)
  - Динамическое переключение QStackedLayout для подформ параметров
  - Палитру ColorAccentPicker (5 неоновых свотчей, эмит сигнала)
  - load_slot_data с расширенными действиями
  - In-place Retranslate без потери введенных пользователем данных
"""
from typing import Any
import pytest
from PySide6.QtWidgets import QApplication

from core.i18n import I18nManager, t
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.styles import INSPECTOR_HEIGHT
from modules.deck.editor.widgets.button_property_form import (
    ACCENT_COLORS,
    ACTION_PRIMITIVE_KEYS,
    ButtonPropertyForm,
    DeckNavSubform,
    UnconfiguredSubform,
)


def test_property_form_height_budget(qapp: QApplication) -> None:
    """Проверка строгого бюджета высоты инспектора: ровно 260 px."""
    form = ButtonPropertyForm()
    assert form.height() == INSPECTOR_HEIGHT
    assert form.height() == 260


def test_property_form_color_accent_picker(qapp: QApplication) -> None:
    """Проверка палитры ColorAccentPicker: 5 цветов и эмит сигнала."""
    form = ButtonPropertyForm()
    signals: list[tuple[str, Any]] = []
    form.property_changed.connect(lambda name, val: signals.append((name, val)))

    assert len(ACCENT_COLORS) == 5
    assert form.accent_picker.get_color() == ACCENT_COLORS[0]

    # Клик по цвету Emerald (#10b981)
    form.accent_picker._on_color_clicked(ACCENT_COLORS[1])
    assert form.accent_picker.get_color() == ACCENT_COLORS[1]
    assert ("color_accent", ACCENT_COLORS[1]) in signals


def test_property_form_stacked_layout_switching(qapp: QApplication) -> None:
    """Проверка переключения стэка подформ параметров при выборе действия."""
    form = ButtonPropertyForm()

    # По умолчанию: hotkey (индекс стека 0)
    assert form.params_stack.currentIndex() == 0

    # Выбор hotkey_switch
    idx_switch = form.combo_actions.findData("hotkey_switch")
    assert idx_switch >= 0
    form.combo_actions.setCurrentIndex(idx_switch)
    assert form.params_stack.currentIndex() == 1

    # Выбор website
    idx_web = form.combo_actions.findData("website")
    assert idx_web >= 0
    form.combo_actions.setCurrentIndex(idx_web)
    assert form.params_stack.currentIndex() == 2
    assert form.subform_path_url._mode == "website"

    # Выбор open_app
    idx_app = form.combo_actions.findData("open_app")
    assert idx_app >= 0
    form.combo_actions.setCurrentIndex(idx_app)
    assert form.params_stack.currentIndex() == 2
    assert form.subform_path_url._mode == "open_app"

    # Выбор multimedia
    idx_media = form.combo_actions.findData("multimedia")
    assert idx_media >= 0
    form.combo_actions.setCurrentIndex(idx_media)
    assert form.params_stack.currentIndex() == 3

    # Выбор text_macro
    idx_macro = form.combo_actions.findData("text_macro")
    assert idx_macro >= 0
    form.combo_actions.setCurrentIndex(idx_macro)
    assert form.params_stack.currentIndex() == 4

    # Выбор volume_control
    idx_vol = form.combo_actions.findData("volume_control")
    assert idx_vol >= 0
    form.combo_actions.setCurrentIndex(idx_vol)
    assert form.params_stack.currentIndex() == 5

    # Высота формы при любом переключении остается строго 260 px
    assert form.height() == 260


def test_property_form_load_slot_data_extended(qapp: QApplication) -> None:
    """Проверка загрузки расширенных данных слота (Website, Color Accent)."""
    form = ButtonPropertyForm()

    dto = ButtonSlotDTO(
        slot_index=2,
        title="DuckDuckGo",
        icon="🌐",
        category="System: Website",
        action_type="website",
        color_accent="#f43f5e",
        action_params={"url": "https://duckduckgo.com"},
    )

    form.load_slot_data(dto)

    assert form.edit_title.text() == "DuckDuckGo"
    assert form.preview_tile.get_icon() == "🌐"
    assert form.accent_picker.get_color() == "#f43f5e"
    assert form.combo_actions.currentData() == "website"
    assert form.params_stack.currentIndex() == 2
    assert form.subform_path_url.edit_input.text() == "https://duckduckgo.com"


def test_property_form_subform_emission(qapp: QApplication) -> None:
    """Проверка эмиссии сигналов изменения параметров подформ."""
    form = ButtonPropertyForm()
    signals: list[tuple[str, Any]] = []
    form.property_changed.connect(lambda name, val: signals.append((name, val)))

    # Переключаем на Text Macro
    idx_macro = form.combo_actions.findData("text_macro")
    form.combo_actions.setCurrentIndex(idx_macro)

    form.subform_text_macro.edit_text.setText("test input")
    form.subform_text_macro.chk_enter.setChecked(True)
    form.subform_text_macro._emit_params()

    assert any(name == "action_params" and val.get("text") == "test input" for name, val in signals)
    assert any(name == "action_params" and val.get("send_enter") is True for name, val in signals)


def test_property_form_retranslate_preserves_extended_inputs(qapp: QApplication) -> None:
    """Проверка сохранения данных всех подформ при динамическом переключении языков."""
    mgr = I18nManager()
    mgr.set_language("ru")

    form = ButtonPropertyForm()
    form.edit_title.setText("Название")
    idx_vol = form.combo_actions.findData("volume_control")
    form.combo_actions.setCurrentIndex(idx_vol)

    assert form.lbl_title_field.text() == "Название:"
    assert form.lbl_params_field.text() == "Параметры:"

    # Переключение на английский
    mgr.set_language("en")
    form.retranslate_ui()

    assert form.lbl_title_field.text() == "Title:"
    assert form.lbl_params_field.text() == "Params:"
    assert form.edit_title.text() == "Название"
    assert form.combo_actions.currentIndex() == idx_vol

    # Возврат на русский
    mgr.set_language("ru")
    form.retranslate_ui()
    assert form.lbl_title_field.text() == "Название:"
    assert form.lbl_params_field.text() == "Параметры:"
    assert form.edit_title.text() == "Название"


# ==============================================================================
# Тесты Шага 3.4 (8 базовых примитивов, Unconfigured State, Presets Menu)
# ==============================================================================


def test_property_form_8_primitives_switching(qapp: QApplication) -> None:
    """Проверка переключения 8 базовых примитивов и эмиссии сигналов."""
    form = ButtonPropertyForm()
    signals: list[tuple[str, Any]] = []
    form.property_changed.connect(lambda name, val: signals.append((name, val)))

    expected_primitives = [
        "hotkey",
        "launch",
        "audio",
        "media",
        "text",
        "system",
        "deck_nav",
        "macro",
    ]
    assert ACTION_PRIMITIVE_KEYS == expected_primitives

    # Переключаем сначала на другой индекс, чтобы при переборе hotkey тоже гарантированно генерировал сигнал
    form.combo_actions.setCurrentIndex(1)
    signals.clear()

    for prim in expected_primitives:
        idx = form.combo_actions.findData(prim)
        assert idx >= 0, f"Primitive {prim} must be in combo_actions"
        form.combo_actions.setCurrentIndex(idx)
        assert ("action_type", prim) in signals
        assert form.height() == 260


def test_property_form_unconfigured_state_on_empty_slot(qapp: QApplication) -> None:
    """При пустом слоте первого запуска форма переходит в нейтральное UnconfiguredSubform."""
    form = ButtonPropertyForm()

    empty_dto = ButtonSlotDTO(
        slot_index=0,
        title="",
        icon="",
        action_type="",
        hotkey="",
    )
    form.load_slot_data(empty_dto)

    assert form._is_unconfigured is True
    assert isinstance(form.params_stack.currentWidget(), UnconfiguredSubform)
    assert form.lbl_category.text() == t("deck.editor.inspector.unconfigured_title")
    assert form.edit_title.placeholderText() == t("deck.editor.inspector.unconfigured_placeholder")
    assert form.btn_test.isEnabled() is False


def test_property_form_apply_preset_and_unconfigured_recovery(qapp: QApplication) -> None:
    """Применение пресета переводит неконфигурированный слот в настроенный со всеми полями."""
    form = ButtonPropertyForm()

    empty_dto = ButtonSlotDTO(slot_index=0, title="", action_type="")
    form.load_slot_data(empty_dto)
    assert form._is_unconfigured is True

    # Применяем пресет Mute микрофона
    form.apply_preset("mic_mute_toggle")

    assert form._is_unconfigured is False
    assert form.btn_test.isEnabled() is True
    assert form.btn_delete.isEnabled() is True
    assert form.preview_tile.get_icon() == "🎙️"
    assert form.edit_title.text() == t("deck.editor.presets.mic_mute_toggle.title")
    assert form.combo_actions.currentData() == "audio"
    assert form.combo_status_source.currentData() == "mic_mute"


def test_property_form_delete_resets_to_unconfigured(qapp: QApplication) -> None:
    """Клик по кнопке корзины сбрасывает кнопку в неконфигурированное состояние."""
    form = ButtonPropertyForm()
    delete_fired = False

    def on_delete() -> None:
        nonlocal delete_fired
        delete_fired = True

    form.delete_requested.connect(on_delete)

    # Загружаем настроенную кнопку
    dto = ButtonSlotDTO(slot_index=1, title="Test Button", action_type="launch", icon="🚀")
    form.load_slot_data(dto)
    assert form._is_unconfigured is False

    # Кликаем корзину
    form.btn_delete.click()
    assert delete_fired is True
    assert form._is_unconfigured is True
    assert isinstance(form.params_stack.currentWidget(), UnconfiguredSubform)
    assert form.edit_title.text() == ""
    assert form.preview_tile.get_icon() in ("", "➕")


def test_property_form_presets_menu_button_stealth_focus(qapp: QApplication) -> None:
    """Кнопка '⚡ Шаблоны...' имеет Qt.NoFocus и корректный текст/тултип."""
    from PySide6.QtCore import Qt

    form = ButtonPropertyForm()
    assert hasattr(form, "btn_presets_menu")
    assert form.btn_presets_menu.focusPolicy() == Qt.NoFocus
    assert "⚡" in form.btn_presets_menu.text()
    assert t("deck.editor.inspector.presets_menu") in form.btn_presets_menu.text()

