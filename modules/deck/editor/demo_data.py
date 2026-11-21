"""
Генератор эталонных демонстрационных данных DuckDeck Editor (Рис. 1).
Поставляет DTO слотов кнопок и секций тачбара для интерактивного прототипа,
а также функцию загрузки профиля в главное окно конфигуратора (DeckEditorWindow).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Tuple

from modules.deck.editor.actions_registry import get_default_action_catalog
from modules.deck.editor.dto import (
    ButtonSlotDTO,
    TouchbarClockDTO,
    TouchbarMediaDTO,
    TouchbarTelemetryDTO,
)

if TYPE_CHECKING:
    from modules.deck.editor.window import DeckEditorWindow

logger = logging.getLogger("duckdock.deck.editor.demo_data")


def get_demo_editor_profile() -> Tuple[
    list[ButtonSlotDTO],
    TouchbarMediaDTO,
    TouchbarClockDTO,
    TouchbarTelemetryDTO,
]:
    """
    Возвращает эталонный набор демонстрационных данных по раскладке Рис. 1:
    - Слот 0: "Open Discord", иконка "🖲️", категория "System: Hotkey", hotkey "Ctrl+Shift+D"
    - Слот 1: "Launch App", иконка "🚀", категория "System: Open Application", action_type "Open Application"
    - Слот 8: "Brightness", иконка "☀️", категория "Stream Deck: Brightness", action_type "Brightness"
    - Слоты 2..7, 9: пустые ячейки ButtonSlotDTO
    - Секция Media: player "YouTube Music", marquee_enabled True, marquee_speed 50
    - Секция Clock: is_24h True, show_date True, swipe_sensitivity 3
    - Секция Telemetry: show_cpu True, show_gpu True, refresh_interval_s 2
    """
    slots: list[ButtonSlotDTO] = []
    for i in range(10):
        if i == 0:
            slots.append(
                ButtonSlotDTO(
                    slot_index=0,
                    title="Open Discord",
                    icon="🖲️",
                    category="System: Hotkey",
                    action_type="Hotkey",
                    hotkey="Ctrl+Shift+D",
                )
            )
        elif i == 1:
            slots.append(
                ButtonSlotDTO(
                    slot_index=1,
                    title="Launch App",
                    icon="🚀",
                    category="System: Open Application",
                    action_type="Open Application",
                    hotkey="",
                )
            )
        elif i == 8:
            slots.append(
                ButtonSlotDTO(
                    slot_index=8,
                    title="Brightness",
                    icon="☀️",
                    category="Stream Deck: Brightness",
                    action_type="Brightness",
                    hotkey="",
                )
            )
        else:
            slots.append(
                ButtonSlotDTO(
                    slot_index=i,
                    title="",
                    icon="",
                    category="",
                    action_type="",
                    hotkey="",
                )
            )

    media = TouchbarMediaDTO(
        player="YouTube Music",
        marquee_enabled=True,
        marquee_speed=50,
    )
    clock = TouchbarClockDTO(
        is_24h=True,
        show_date=True,
        swipe_sensitivity=3,
    )
    telemetry = TouchbarTelemetryDTO(
        show_cpu=True,
        show_gpu=True,
        refresh_interval_s=2,
    )

    return slots, media, clock, telemetry


def load_demo_profile_into_window(window: DeckEditorWindow) -> None:
    """
    Загружает эталонный демонстрационный профиль в окно DeckEditorWindow:
    - Заполняет внутренние DTO окна (_button_slots, _touchbar_media, _touchbar_clock, _touchbar_telemetry);
    - Заполняет превью ячеек холста (DeckCanvasWidget);
    - Сбрасывает выделение на холсте и переводит инспектор в плейсхолдер (Рис. 1);
    - Заполняет каталог действий (ActionLibraryDrawer) стандартным реестром.
    """
    slots, media, clock, telemetry = get_demo_editor_profile()

    # Сохраняем DTO в модель окна
    window._button_slots = {s.slot_index: s for s in slots}
    window._touchbar_media = media
    window._touchbar_clock = clock
    window._touchbar_telemetry = telemetry

    # Обновляем визуальное отображение ячеек на холсте
    canvas = getattr(window, "canvas_widget", None)
    if canvas is not None:
        for s in slots:
            if s.title or s.icon:
                if hasattr(canvas, "update_cell_preview"):
                    canvas.update_cell_preview(s.slot_index, "title", s.title)
                    canvas.update_cell_preview(s.slot_index, "icon", s.icon)
                    canvas.update_cell_preview(s.slot_index, "category", s.category)
                    canvas.update_cell_preview(s.slot_index, "hotkey", s.hotkey)
            else:
                if hasattr(canvas, "clear_cell"):
                    canvas.clear_cell(s.slot_index)

        if hasattr(canvas, "clear_selection"):
            canvas.clear_selection()

    # Инициализация инспектора в состоянии нейтрального плейсхолдера (Рис. 1)
    inspector = getattr(window, "inspector", None)
    if inspector is not None and hasattr(inspector, "show_placeholder"):
        inspector.show_placeholder()

    # Наполнение каталога библиотеки действий
    drawer = getattr(window, "action_drawer", None)
    if drawer is not None and hasattr(drawer, "populate_actions"):
        drawer.populate_actions(get_default_action_catalog())

    logger.info("Demo profile successfully loaded into DeckEditorWindow")
