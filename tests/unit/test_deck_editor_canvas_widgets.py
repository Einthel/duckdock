"""
Модульные тесты для интерактивных компонентов холста DuckDeck Editor:
- EditorGridCell (ячейка кнопки 96x96, выделение, данные, клик)
- TouchbarSectionWidget (секция тачбара, прозрачность детей, локализация, клик)
- EditorTouchbarStrip (интерактивная полоса 528x68, 3 секции, переключение выделения, сигналы, локализация)
- PageNavigationBar (панель пагинации 36px, кнопки Home, 1..8, Add, локализация тултипов)
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.deck.editor.styles import (
    GRID_CELL_SIZE,
    PAGINATION_SLOT_HEIGHT,
    TOUCHBAR_HEIGHT,
    TOUCHBAR_WIDTH,
)
from modules.deck.editor.widgets.grid_cell import EditorGridCell
from modules.deck.editor.widgets.pagination_bar import PageNavigationBar
from modules.deck.editor.widgets.touchbar_section import TouchbarSectionWidget
from modules.deck.editor.widgets.touchbar_strip import EditorTouchbarStrip


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_grid_cell_initialization(qapp):
    cell = EditorGridCell(slot_index=3)
    assert cell.slot_index == 3
    assert cell.width() == GRID_CELL_SIZE
    assert cell.height() == GRID_CELL_SIZE
    assert cell.lbl_index.text() == "[3]"
    assert cell.is_selected() is False
    assert cell.property("selected") == "false"
    assert cell.lbl_icon.text() == ""
    assert cell.lbl_title.text() == ""
    # Проверка инвариантов Obsidian v2 и Stealth Focus
    assert cell.focusPolicy() == Qt.NoFocus
    assert cell.lbl_index.property("class") == "CellIndexLabel"
    assert cell.lbl_icon.property("class") == "CellIconLabel"
    assert cell.lbl_title.property("class") == "CellTitleLabel"
    # Проверка отсутствия инлайн-стилей
    assert cell.lbl_index.styleSheet() == ""
    assert cell.lbl_icon.styleSheet() == ""
    assert cell.lbl_title.styleSheet() == ""


def test_grid_cell_selection_toggle(qapp):
    cell = EditorGridCell(slot_index=0)
    assert not cell.is_selected()

    cell.set_selected(True)
    assert cell.is_selected() is True
    assert cell.property("selected") == "true"

    cell.set_selected(False)
    assert cell.is_selected() is False
    assert cell.property("selected") == "false"


def test_grid_cell_set_and_clear_data(qapp):
    cell = EditorGridCell(slot_index=5)
    cell.set_button_data(
        title="Open Discord",
        icon="🚀",
        category="system",
        hotkey="Ctrl+Shift+D",
    )
    data = cell.get_button_data()
    assert data["title"] == "Open Discord"
    assert data["icon"] == "🚀"
    assert data["category"] == "system"
    assert data["hotkey"] == "Ctrl+Shift+D"
    assert cell.lbl_icon.text() == "🚀"
    assert "Open Discord" in cell.lbl_title.text()
    assert "Ctrl+Shift+D" in cell.toolTip()

    cell.clear_button_data()
    empty_data = cell.get_button_data()
    assert empty_data["title"] == ""
    assert empty_data["icon"] == ""
    assert cell.lbl_icon.text() == ""
    assert cell.lbl_title.text() == ""


def test_grid_cell_click_signal(qapp):
    cell = EditorGridCell(slot_index=7)
    emitted_slot = []

    cell.cell_clicked.connect(lambda idx: emitted_slot.append(idx))

    # Симулируем нажатие ЛКМ
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(10, 10),
        QPoint(10, 10),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    cell.mousePressEvent(event)

    assert emitted_slot == [7]


def test_touchbar_section_initialization_and_children_transparency(qapp):
    for sec_type, title_key in [
        ("media", "deck.editor.canvas.touchbar.media_title"),
        ("clock", "deck.editor.canvas.touchbar.clock_title"),
        ("telemetry", "deck.editor.canvas.touchbar.telemetry_title"),
    ]:
        section = TouchbarSectionWidget(section_type=sec_type, title_key=title_key)
        assert section.section_type == sec_type
        assert section.title_key == title_key
        assert section.is_selected() is False
        assert section.property("selected") == "false"
        assert section.focusPolicy() == Qt.NoFocus

        # Инвариант: все дочерние элементы получают WA_TransparentForMouseEvents = True
        # и очищены от инлайн-стилей (отсутствие жестких цветов)
        children = section.findChildren(object)
        for child in children:
            if hasattr(child, "testAttribute"):
                assert child.testAttribute(Qt.WA_TransparentForMouseEvents) is True
            if hasattr(child, "styleSheet"):
                assert child.styleSheet() == ""


def test_touchbar_section_selection_toggle(qapp):
    section = TouchbarSectionWidget("media", "deck.editor.canvas.touchbar.media_title")
    assert not section.is_selected()

    section.set_selected(True)
    assert section.is_selected() is True
    assert section.property("selected") == "true"

    section.set_selected(False)
    assert section.is_selected() is False
    assert section.property("selected") == "false"


def test_touchbar_section_retranslate_ui(qapp):
    section = TouchbarSectionWidget("clock", "deck.editor.canvas.touchbar.clock_title")

    I18nManager().set_language("en", emit_signal=False)
    section.retranslate_ui()
    assert section.toolTip() == t("deck.editor.canvas.touchbar.clock_title")
    assert section.toolTip() == "Clock & Navigation"

    I18nManager().set_language("ru", emit_signal=False)
    section.retranslate_ui()
    assert section.toolTip() == t("deck.editor.canvas.touchbar.clock_title")
    assert section.toolTip() == "Часы и навигация"

    # Возвращаем английский по умолчанию
    I18nManager().set_language("en", emit_signal=False)


def test_touchbar_section_click_signal(qapp):
    section = TouchbarSectionWidget("telemetry", "deck.editor.canvas.touchbar.telemetry_title")
    emitted_types = []

    section.section_clicked.connect(lambda st: emitted_types.append(st))

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(20, 20),
        QPoint(20, 20),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    section.mousePressEvent(event)

    assert emitted_types == ["telemetry"]


# ==============================================================================
# Тесты для EditorTouchbarStrip (Шаг 3.4)
# ==============================================================================


def test_touchbar_strip_initialization_and_geometry(qapp):
    strip = EditorTouchbarStrip()
    assert strip.width() == TOUCHBAR_WIDTH
    assert strip.height() == TOUCHBAR_HEIGHT
    assert strip.width() == 528
    assert strip.height() == 68
    assert strip.focusPolicy() == Qt.NoFocus
    assert strip.sec_media is not None
    assert strip.sec_clock is not None
    assert strip.sec_telemetry is not None
    assert strip.get_selected_section() is None
    assert not strip.sec_media.is_selected()
    assert not strip.sec_clock.is_selected()
    assert not strip.sec_telemetry.is_selected()

    # Проверка отсутствия инлайн-стилей у разделителей полосы
    for child in strip.findChildren(object):
        if hasattr(child, "property") and child.property("class") == "TouchbarDivider":
            assert child.styleSheet() == ""


def test_touchbar_strip_selection_and_signals(qapp):
    strip = EditorTouchbarStrip()
    selected_events = []
    strip.section_selected.connect(lambda st: selected_events.append(st))

    # Ручной выбор секции 'media'
    strip.select_section("media")
    assert strip.get_selected_section() == "media"
    assert strip.sec_media.is_selected() is True
    assert strip.sec_clock.is_selected() is False
    assert strip.sec_telemetry.is_selected() is False

    # Переключение на 'clock'
    strip.select_section("clock")
    assert strip.get_selected_section() == "clock"
    assert strip.sec_media.is_selected() is False
    assert strip.sec_clock.is_selected() is True
    assert strip.sec_telemetry.is_selected() is False

    # Очистка выделения
    strip.clear_selection()
    assert strip.get_selected_section() is None
    assert not strip.sec_media.is_selected()
    assert not strip.sec_clock.is_selected()
    assert not strip.sec_telemetry.is_selected()

    # Клик по секции telemetry через симуляцию section_clicked
    strip.sec_telemetry.section_clicked.emit("telemetry")
    assert selected_events == ["telemetry"]
    assert strip.get_selected_section() == "telemetry"
    assert strip.sec_telemetry.is_selected() is True


def test_touchbar_strip_retranslate_ui(qapp):
    strip = EditorTouchbarStrip()

    I18nManager().set_language("en", emit_signal=False)
    strip.retranslate_ui()
    assert strip.sec_media.toolTip() == "Media Player"
    assert strip.sec_clock.toolTip() == "Clock & Navigation"
    assert strip.sec_telemetry.toolTip() == "Telemetry"

    I18nManager().set_language("ru", emit_signal=False)
    strip.retranslate_ui()
    assert strip.sec_media.toolTip() == "Медиаплеер"
    assert strip.sec_clock.toolTip() == "Часы и навигация"
    assert strip.sec_telemetry.toolTip() == "Телеметрия"

    I18nManager().set_language("en", emit_signal=False)


# ==============================================================================
# Тесты для PageNavigationBar (Шаг 3.5)
# ==============================================================================


def test_pagination_bar_initialization_and_geometry(qapp):
    bar = PageNavigationBar()
    assert bar.height() == PAGINATION_SLOT_HEIGHT
    assert bar.height() == 36
    assert bar.btn_home.text() == "⭐"
    # По умолчанию создается ровно 1 страница
    assert len(bar.page_buttons) == 1
    assert bar.btn_add.text() == "+"
    assert bar.get_current_page() == 1

    # Первая страница активна по умолчанию
    assert bar.page_buttons[0].property("active") == "true"

    # Динамическое увеличение числа страниц
    bar.set_page_count(8)
    assert len(bar.page_buttons) == 8
    for btn in bar.page_buttons[1:]:
        assert btn.property("active") == "false"


def test_pagination_bar_page_change_and_signals(qapp):
    bar = PageNavigationBar()
    bar.set_page_count(8)
    emitted_pages = []
    bar.page_changed.connect(lambda p: emitted_pages.append(p))

    # Клик по странице 4
    bar.page_buttons[3].click()
    assert emitted_pages == [4]
    assert bar.get_current_page() == 4
    assert bar.page_buttons[3].property("active") == "true"
    assert bar.page_buttons[0].property("active") == "false"

    # Клик по Home -> переход на 1
    bar.btn_home.click()
    assert emitted_pages == [4, 1]
    assert bar.get_current_page() == 1
    assert bar.page_buttons[0].property("active") == "true"
    assert bar.page_buttons[3].property("active") == "false"

    # Программный set_current_page(7)
    bar.set_current_page(7)
    assert bar.get_current_page() == 7
    assert bar.page_buttons[6].property("active") == "true"
    assert bar.page_buttons[0].property("active") == "false"


def test_pagination_bar_add_page_signal(qapp):
    bar = PageNavigationBar()
    add_requested = []
    bar.add_page_requested.connect(lambda: add_requested.append(True))

    bar.btn_add.click()
    assert add_requested == [True]


def test_pagination_bar_retranslate_ui(qapp):
    bar = PageNavigationBar()

    I18nManager().set_language("en", emit_signal=False)
    bar.retranslate_ui()
    assert bar.btn_home.toolTip() == "Home Page"
    assert bar.btn_add.toolTip() == "Create New Page"

    I18nManager().set_language("ru", emit_signal=False)
    bar.retranslate_ui()
    assert bar.btn_home.toolTip() == "Домашняя страница"
    assert bar.btn_add.toolTip() == "Создать новую страницу"

    I18nManager().set_language("en", emit_signal=False)
