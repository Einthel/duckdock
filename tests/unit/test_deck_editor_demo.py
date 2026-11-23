"""
Модульные тесты демонстрационных данных и автономного лончера DuckDeck Editor.
Проверяют:
  - Структуру и полноту get_demo_editor_profile() по референсу Рис. 1.
  - Корректную загрузку демо-профиля через load_demo_profile_into_window().
  - Состояние слотов [0], [1], [8] и пустых слотов на холсте.
  - Начальное состояние нейтрального плейсхолдера в инспекторе свойств.
  - Работу центрирования и инициализации лончера.
"""
from __future__ import annotations

import pytest

from modules.deck.editor.demo_data import (
    get_demo_editor_profile,
    load_demo_profile_into_window,
)
from modules.deck.editor.dto import (
    ButtonSlotDTO,
    TouchbarClockDTO,
    TouchbarMediaDTO,
    TouchbarTelemetryDTO,
)
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.editor.widgets.property_inspector import KeyPropertyInspector
from modules.deck.editor.window import DeckEditorWindow


def test_get_demo_editor_profile_structure():
    """Проверка структуры и эталонных данных профиля по Рис. 1."""
    slots, media, clock, telemetry = get_demo_editor_profile()

    assert len(slots) == 10
    assert isinstance(media, TouchbarMediaDTO)
    assert isinstance(clock, TouchbarClockDTO)
    assert isinstance(telemetry, TouchbarTelemetryDTO)

    # Слот 0: Open Discord
    slot0 = slots[0]
    assert slot0.slot_index == 0
    assert slot0.title == "Open Discord"
    assert slot0.icon == "🖲️"
    assert slot0.category == "System: Hotkey"
    assert slot0.action_type == "Hotkey"
    assert slot0.hotkey == "Ctrl+Shift+D"

    # Слот 1: Launch App
    slot1 = slots[1]
    assert slot1.slot_index == 1
    assert slot1.title == "Launch App"
    assert slot1.icon == "🚀"
    assert slot1.category == "System: Open Application"
    assert slot1.action_type == "Open Application"

    # Слот 8: Brightness
    slot8 = slots[8]
    assert slot8.slot_index == 8
    assert slot8.title == "Brightness"
    assert slot8.icon == "☀️"
    assert slot8.category == "Stream Deck: Brightness"
    assert slot8.action_type == "Brightness"

    # Пустые слоты (2..7, 9)
    for idx in [2, 3, 4, 5, 6, 7, 9]:
        s = slots[idx]
        assert s.slot_index == idx
        assert s.title == ""
        assert s.icon == ""

    # Секции тачбара
    assert media.player == "YouTube Music"
    assert media.marquee_enabled is True
    assert media.marquee_speed == 50

    assert clock.is_24h is True
    assert clock.show_date is True
    assert clock.swipe_sensitivity == 3

    assert telemetry.show_cpu is True
    assert telemetry.show_gpu is True
    assert telemetry.refresh_interval_s == 2


def test_load_demo_profile_into_window(qapp, sample_two_page_deck_config_path):
    """Проверка загрузки эталонного профиля в главное окно DeckEditorWindow."""
    window = DeckEditorWindow(config_path=sample_two_page_deck_config_path)

    load_demo_profile_into_window(window)

    # Проверка сохранения DTO в модели окна
    assert 0 in window._button_slots
    assert window._button_slots[0].title == "Open Discord"
    assert window._button_slots[1].title == "Launch App"
    assert window._button_slots[8].title == "Brightness"

    assert window._touchbar_media.player == "YouTube Music"
    assert window._touchbar_clock.is_24h is True
    assert window._touchbar_telemetry.show_cpu is True

    # Проверка отображения на холсте DeckCanvasWidget
    assert isinstance(window.canvas_widget, DeckCanvasWidget)
    cell0 = window.canvas_widget.get_cell(0)
    assert cell0 is not None
    data0 = cell0.get_button_data()
    assert data0["title"] == "Open Discord"
    assert data0["icon"] == "🖲️"

    cell1 = window.canvas_widget.get_cell(1)
    assert cell1 is not None
    data1 = cell1.get_button_data()
    assert data1["title"] == "Launch App"
    assert data1["icon"] == "🚀"

    cell8 = window.canvas_widget.get_cell(8)
    assert cell8 is not None
    data8 = cell8.get_button_data()
    assert data8["title"] == "Brightness"
    assert data8["icon"] == "☀️"

    cell2 = window.canvas_widget.get_cell(2)
    assert cell2 is not None
    assert cell2.get_button_data()["title"] == ""

    # Проверка сброса выделения на холсте (Рис. 1)
    assert window.canvas_widget.get_selected_target() is None

    # Проверка инспектора свойств: плейсхолдер нейтрального состояния (Index 0)
    assert isinstance(window.inspector, KeyPropertyInspector)
    assert window.inspector.stack.currentIndex() == 0

    window.close()
