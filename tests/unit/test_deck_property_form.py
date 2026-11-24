"""
Модульные тесты формы инспектора свойств кнопки ButtonPropertyForm (Фаза 2).
Проверяет:
  - Соблюдение бюджета высоты (INSPECTOR_HEIGHT == 260 px)
  - Динамическое переключение QStackedLayout для 8 чистых подформ (0..7) + Unconfigured (8)
  - Палитру ColorAccentPicker (5 неоновых свотчей, эмит сигнала)
  - load_slot_data с примитивами и DI аудиоустройств
  - In-place Retranslate без потери введенных пользователем данных
"""
from typing import Any
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.i18n import I18nManager, t
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.styles import INSPECTOR_HEIGHT
from modules.deck.editor.widgets.button_property_form import (
    ACCENT_COLORS,
    ACTION_PRIMITIVE_KEYS,
    ButtonPropertyForm,
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

    form.accent_picker._on_color_clicked(ACCENT_COLORS[1])
    assert form.accent_picker.get_color() == ACCENT_COLORS[1]
    assert ("color_accent", ACCENT_COLORS[1]) in signals


def test_property_form_stacked_layout_switching(qapp: QApplication) -> None:
    """Проверка переключения стэка 8 чистых подформ параметров (индексы 0..7)."""
    form = ButtonPropertyForm()

    assert form.combo_actions.count() == 8
    assert form.params_stack.currentIndex() == 0

    for expected_idx, prim in enumerate(ACTION_PRIMITIVE_KEYS):
        idx = form.combo_actions.findData(prim)
        assert idx >= 0
        form.combo_actions.setCurrentIndex(idx)
        assert form.params_stack.currentIndex() == expected_idx
        assert form.height() == 260


def test_property_form_load_slot_data_extended(qapp: QApplication) -> None:
    """Проверка загрузки расширенных данных слота (Launch URL, Color Accent)."""
    form = ButtonPropertyForm()

    dto = ButtonSlotDTO(
        slot_index=2,
        title="DuckDuckGo",
        icon="🌐",
        category="System: Website",
        action_type="launch",
        color_accent="#f43f5e",
        action_params={"kind": "url", "target": "https://duckduckgo.com"},
    )

    form.load_slot_data(dto)

    assert form.edit_title.text() == "DuckDuckGo"
    assert form.preview_tile.get_icon() == "🌐"
    assert form.accent_picker.get_color() == "#f43f5e"
    assert form.combo_actions.currentData() == "launch"
    assert form.params_stack.currentIndex() == 1
    assert form.subform_launch.combo_kind.currentData() == "url"
    assert form.subform_launch.edit_target.text() == "https://duckduckgo.com"


def test_property_form_subform_emission(qapp: QApplication) -> None:
    """Проверка эмиссии сигналов изменения параметров подформ."""
    form = ButtonPropertyForm()
    signals: list[tuple[str, Any]] = []
    form.property_changed.connect(lambda name, val: signals.append((name, val)))

    idx_text = form.combo_actions.findData("text")
    form.combo_actions.setCurrentIndex(idx_text)

    form.subform_text.edit_text.setText("test input")
    form.subform_text.chk_enter.setChecked(True)
    form.subform_text._emit_params()

    assert any(name == "action_params" and val.get("text") == "test input" for name, val in signals)
    assert any(name == "action_params" and val.get("send_enter") is True for name, val in signals)


def test_property_form_retranslate_preserves_extended_inputs(qapp: QApplication) -> None:
    """Проверка сохранения данных всех подформ при динамическом переключении языков."""
    mgr = I18nManager()
    mgr.set_language("ru")

    form = ButtonPropertyForm()
    form.edit_title.setText("Название")
    idx_audio = form.combo_actions.findData("audio")
    form.combo_actions.setCurrentIndex(idx_audio)

    assert form.lbl_title_field.text() == "Название:"
    assert form.lbl_params_field.text() == "Параметры:"

    mgr.set_language("en")
    form.retranslate_ui()

    assert form.lbl_title_field.text() == "Title:"
    assert form.lbl_params_field.text() == "Params:"
    assert form.edit_title.text() == "Название"
    assert form.combo_actions.currentIndex() == idx_audio

    mgr.set_language("ru")
    form.retranslate_ui()
    assert form.lbl_title_field.text() == "Название:"
    assert form.lbl_params_field.text() == "Параметры:"
    assert form.edit_title.text() == "Название"


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

    form.combo_actions.setCurrentIndex(1)
    signals.clear()

    for prim in expected_primitives:
        idx = form.combo_actions.findData(prim)
        assert idx >= 0, f"Primitive {prim} must be in combo_actions"
        form.combo_actions.setCurrentIndex(idx)
        assert ("action_type", prim) in signals
        assert form.height() == 260


def test_property_form_unconfigured_state_on_empty_slot(qapp: QApplication) -> None:
    """При пустом слоте форма переходит в нейтральное UnconfiguredSubform (index 8)."""
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
    assert form.params_stack.currentIndex() == 8
    assert isinstance(form.params_stack.currentWidget(), UnconfiguredSubform)
    assert form.lbl_category.text() == t("deck.editor.inspector.unconfigured_title")
    assert form.edit_title.placeholderText() == t("deck.editor.inspector.unconfigured_placeholder")
    assert form.btn_test.isEnabled() is False
    assert not hasattr(form, "btn_presets_menu")


def test_property_form_delete_resets_to_unconfigured(qapp: QApplication) -> None:
    """Клик по кнопке корзины сбрасывает кнопку в неконфигурированное состояние."""
    form = ButtonPropertyForm()
    delete_fired = False

    def on_delete() -> None:
        nonlocal delete_fired
        delete_fired = True

    form.delete_requested.connect(on_delete)

    dto = ButtonSlotDTO(slot_index=1, title="Test Button", action_type="launch", icon="🚀")
    form.load_slot_data(dto)
    assert form._is_unconfigured is False

    form.btn_delete.click()
    assert delete_fired is True
    assert form._is_unconfigured is True
    assert isinstance(form.params_stack.currentWidget(), UnconfiguredSubform)
    assert form.edit_title.text() == ""
    assert form.preview_tile.get_icon() in ("", "➕")


def test_property_form_di_audio_devices_and_no_focus(qapp: QApplication) -> None:
    """Проверка DI передачи аудиоустройств и соблюдения Qt.NoFocus."""
    form = ButtonPropertyForm()
    form.set_audio_devices([("dev_1", "Headphones"), ("dev_2", "Speakers")])

    assert form.combo_actions.focusPolicy() == Qt.NoFocus
    assert form.btn_delete.focusPolicy() == Qt.NoFocus
    assert form.btn_test.focusPolicy() == Qt.NoFocus
    assert form.subform_audio.combo_device.count() == 2
    assert form.subform_audio.combo_device.itemData(0) == "dev_1"
    assert form.subform_audio.combo_device.itemText(1) == "Speakers"


def test_property_form_no_vertical_clipping_with_qss(qapp: QApplication) -> None:
    """
    Регрессионный тест: дочерние QComboBox и поля ввода внутри контейнеров
    ButtonPropertyForm не должны превышать высоту контейнеров (INPUT_HEIGHT == 30)
    при применении EDITOR_MAIN_QSS, чтобы нижние границы не обрезались.
    """
    from PySide6.QtWidgets import QComboBox, QLineEdit

    from modules.deck.editor.styles import INPUT_HEIGHT, apply_editor_theme

    form = ButtonPropertyForm()
    apply_editor_theme(form)
    form.load_slot_data(
        ButtonSlotDTO(
            slot_index=0,
            title="Test",
            action_type="deck_nav",
            action_params={"target": "next_page"},
        )
    )
    form.resize(760, INSPECTOR_HEIGHT)
    form.show()
    qapp.processEvents()

    row3_container = form.status_subgroup.parentWidget()
    assert row3_container is not None
    assert row3_container.height() == INPUT_HEIGHT
    assert form.combo_status_source.height() <= row3_container.height()
    assert form.combo_click_sound.height() <= row3_container.height()
    assert form.combo_status_source.minimumSizeHint().height() <= row3_container.height()
    assert form.combo_click_sound.minimumSizeHint().height() <= row3_container.height()

    params_container = form.subform_deck_nav.parentWidget()
    assert params_container is not None
    assert params_container.height() == INPUT_HEIGHT
    for i in range(form.params_stack.count()):
        sub = form.params_stack.widget(i)
        assert sub.minimumSizeHint().height() <= INPUT_HEIGHT
        for child in [*sub.findChildren(QComboBox), *sub.findChildren(QLineEdit)]:
            assert child.minimumSizeHint().height() <= INPUT_HEIGHT
