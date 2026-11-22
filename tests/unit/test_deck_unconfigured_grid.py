"""
Тесты отображения всех 10 слотов сетки DuckDeck (включая ненастроенные кнопки)
и автоматической загрузки конфигурации при открытии DeckEditorWindow.
"""
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from modules.deck.editor.adapter import DeckConfigAdapter
from modules.deck.editor.window import DeckEditorWindow
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.models import (
    DeckActionConfig,
    DeckButtonConfig,
    DeckPageConfig,
    DeckRootConfig,
)
from modules.deck.widgets.deck_grid import DeckGrid
from modules.deck.view import DeckView


@pytest.fixture
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_deck_grid_always_renders_ten_buttons(qapp):
    """
    Даже если в page_config настроено только 2 кнопки (как на рис.1),
    DeckGrid обязан создать ровно 10 кнопок (все ячейки 2x5),
    где слоты 2..9 отображаются ненастроенными тайлами.
    """
    grid = DeckGrid()
    page = DeckPageConfig(
        id="test_partial",
        name="Partial Page",
        grid_rows=2,
        grid_cols=5,
        buttons=[
            DeckButtonConfig(
                id="btn_0",
                slot_index=0,
                title="Website 1",
                category="system",
                icon="🌐",
                action=DeckActionConfig(action_type="website", params={"url": "https://google.com"}),
            ),
            DeckButtonConfig(
                id="btn_1",
                slot_index=1,
                title="Website 2",
                category="system",
                icon="🌐",
                action=DeckActionConfig(action_type="website", params={"url": ""}),
            ),
        ],
    )

    grid.load_page(page)

    buttons = grid.get_buttons()
    assert len(buttons) == 10

    # Проверяем настроенные кнопки
    assert "btn_0" in buttons
    assert buttons["btn_0"].lbl_title.text() == "Website 1"
    assert buttons["btn_0"].lbl_icon.text() == "🌐"

    assert "btn_1" in buttons
    assert buttons["btn_1"].lbl_title.text() == "Website 2"
    assert buttons["btn_1"].lbl_icon.text() == "🌐"

    # Проверяем ненастроенные кнопки (слоты 2..9)
    for slot_idx in range(2, 10):
        unconf_id = f"btn_unconfigured_test_partial_{slot_idx}"
        assert unconf_id in buttons
        unconf_btn = buttons[unconf_id]
        assert unconf_btn.lbl_title.text() == ""
        assert unconf_btn.lbl_icon.text() == ""
        assert unconf_btn.button_config.slot_index == slot_idx

    grid.cleanup()


def test_deck_view_unconfigured_button_trigger_stays_idle(qapp, tmp_path: Path):
    """
    При клике на ненастроенную кнопку воспроизводится клик, но состояние остается idle,
    не вызывая сбоев или передачи действий в фоновый поток.
    """
    cfg_file = tmp_path / "deck_partial.json"
    root = DeckRootConfig(
        pages=[
            DeckPageConfig(
                id="default",
                name="Main",
                grid_rows=2,
                grid_cols=5,
                buttons=[
                    DeckButtonConfig(
                        id="btn_slot_0",
                        slot_index=0,
                        title="Website",
                        category="system",
                        icon="🌐",
                        action=DeckActionConfig(action_type="website", params={"url": "https://test.com"}),
                    ),
                ],
            )
        ]
    )
    DeckConfigAdapter.save_deck_config_atomic(root, str(cfg_file))

    view = DeckView(config_path=str(cfg_file))
    unconf_btn = view.grid.get_button("btn_unconfigured_default_1")
    assert unconf_btn is not None

    # Имитируем клик
    view._on_button_triggered(unconf_btn.button_config)
    assert unconf_btn.state == "idle"

    view.cleanup()


def test_deck_editor_window_auto_loads_saved_config_on_init(qapp, tmp_path: Path):
    """
    При инициализации DeckEditorWindow автоматически вызывается load_configuration(),
    поэтому сохраненные кнопки сразу отображаются в ячейках холста и DTO слотов.
    """
    cfg_file = tmp_path / "deck_auto_load.json"
    root = DeckRootConfig(
        pages=[
            DeckPageConfig(
                id="default",
                name="Main",
                grid_rows=2,
                grid_cols=5,
                buttons=[
                    DeckButtonConfig(
                        id="btn_slot_0",
                        slot_index=0,
                        title="Открыть веб-сайт",
                        category="system",
                        icon="🌐",
                        action=DeckActionConfig(action_type="website", params={"url": "https://google.com"}),
                    ),
                    DeckButtonConfig(
                        id="btn_slot_1",
                        slot_index=1,
                        title="Открыть веб-сайт 2",
                        category="system",
                        icon="🌐",
                        action=DeckActionConfig(action_type="website", params={"url": "https://ya.ru"}),
                    ),
                ],
            )
        ]
    )
    DeckConfigAdapter.save_deck_config_atomic(root, str(cfg_file))

    # Создаем окно редактора, привязанное к файлу
    window = DeckEditorWindow(parent=None)
    window.load_configuration(config_path=str(cfg_file), page_id="default")

    # Проверяем, что слоты 0 и 1 заполнены
    assert window._button_slots[0].title == "Открыть веб-сайт"
    assert window._button_slots[0].icon == "🌐"
    assert window._button_slots[1].title == "Открыть веб-сайт 2"
    assert window._button_slots[1].icon == "🌐"

    # Проверяем отображение на холсте
    canvas: DeckCanvasWidget = window.canvas_widget
    cell_0 = canvas.get_cell(0)
    assert cell_0._title == "Открыть веб-сайт"
    assert cell_0._icon == "🌐"

    cell_1 = canvas.get_cell(1)
    assert cell_1._title == "Открыть веб-сайт 2"
    assert cell_1._icon == "🌐"

    # Пустые ячейки (слот 2) очищены
    cell_2 = canvas.get_cell(2)
    assert cell_2._title == ""
    assert cell_2._icon == ""

    window.close()
