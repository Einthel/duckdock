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

from core.i18n import I18nManager
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
