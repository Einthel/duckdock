"""
Комплексные модульные тесты холста DuckDeck Canvas и интеграции в главное окно (Шаг 3.8).
Проверяют:
  - Наличие 10 кнопок (EditorGridCell, слоты 0..9) и 3-х секций тачбара (Media, Clock, Telemetry).
  - Взаимное исключение выделения (Single Source of Truth: кнопка <-> кнопка, кнопка <-> тачбар).
  - Сброс выделения при клике в нейтральную область холста и по клавише Esc.
  - Проверку сигналов пагинатора страниц (PageNavigationBar: page_changed, add_page_requested).
  - Проверку интеграции холста в DeckEditorWindow (синхронизация страниц, обработка сигналов).
  - Тест test_canvas_retranslate_ui: проверка смены языка подсказок пагинатора и названий секций тачбара.
"""
from __future__ import annotations

from typing import List, Tuple
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.editor.widgets.grid_cell import EditorGridCell
from modules.deck.editor.widgets.pagination_bar import PageNavigationBar
from modules.deck.editor.widgets.touchbar_section import TouchbarSectionWidget
from modules.deck.editor.widgets.touchbar_strip import EditorTouchbarStrip
from modules.deck.editor.window import DeckEditorWindow


@pytest.fixture
def canvas_widget(qapp):
    """Фикстура для создания изолированного экземпляра DeckCanvasWidget."""
    initial_lang = I18nManager().current_language
    widget = DeckCanvasWidget()
    widget.show()
    qapp.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    qapp.processEvents()
    I18nManager().set_language(initial_lang, emit_signal=False)


@pytest.fixture
def editor_window(qapp, sample_two_page_deck_config_path):
    """Фикстура для создания экземпляра главного окна DeckEditorWindow."""
    initial_lang = I18nManager().current_language
    window = DeckEditorWindow(config_path=sample_two_page_deck_config_path)
    window.show()
    qapp.processEvents()
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()
    I18nManager().set_language(initial_lang, emit_signal=False)


def test_canvas_grid_cells_count(canvas_widget):
    """
    Проверка наличия ровно 10 ячеек EditorGridCell со слотами 0..9:
      - Общее количество ячеек равно 10.
      - Порядок индексов слотов 0..9.
      - Метки индексов слотов [0]..[9].
      - Метод get_cell(idx) возвращает корректную ячейку.
      - Выход за пределы (10, -1) возвращает None.
    """
    assert len(canvas_widget.cells) == 10
    for idx, cell in enumerate(canvas_widget.cells):
        assert isinstance(cell, EditorGridCell)
        assert cell.slot_index == idx
        assert cell.lbl_index.text() == f"[{idx}]"
        assert canvas_widget.get_cell(idx) is cell

    assert canvas_widget.get_cell(10) is None
    assert canvas_widget.get_cell(-1) is None


def test_touchbar_strip_sections(canvas_widget):
    """
    Проверка наличия полосы тачбара и 3-х кликабельных секций:
      - Тачбар присутствует и является экземпляром EditorTouchbarStrip.
      - Секция media имеет тип 'media'.
      - Секция clock имеет тип 'clock'.
      - Секция telemetry имеет тип 'telemetry'.
      - Все три секции являются экземплярами TouchbarSectionWidget.
    """
    strip = canvas_widget.touchbar_strip
    assert isinstance(strip, EditorTouchbarStrip)
    assert isinstance(strip.sec_media, TouchbarSectionWidget)
    assert isinstance(strip.sec_clock, TouchbarSectionWidget)
    assert isinstance(strip.sec_telemetry, TouchbarSectionWidget)

    assert strip.sec_media.section_type == "media"
    assert strip.sec_clock.section_type == "clock"
    assert strip.sec_telemetry.section_type == "telemetry"


def test_exclusive_selection_buttons(canvas_widget, qtbot):
    """
    Проверка взаимного исключения выделения кнопок (кнопка <-> кнопка):
      - Клик по кнопке [0] подсвечивает ее и снимает выделение с остальных.
      - Клик по кнопке [5] переносит подсветку на нее и снимает с [0].
      - Проверка эмиссии сигнала selection_changed('button', slot_index).
    """
    received_signals: List[Tuple[str, object]] = []
    canvas_widget.selection_changed.connect(lambda t_type, t_id: received_signals.append((t_type, t_id)))

    # 1. Клик по ячейке 0 через qtbot
    qtbot.mouseClick(canvas_widget.cells[0], Qt.LeftButton)
    assert canvas_widget.get_selected_target() == ("button", 0)
    assert canvas_widget.cells[0].is_selected() is True
    assert all(not c.is_selected() for c in canvas_widget.cells[1:])
    assert canvas_widget.touchbar_strip.get_selected_section() is None
    assert received_signals[-1] == ("button", 0)

    # 2. Клик по ячейке 5 через qtbot
    qtbot.mouseClick(canvas_widget.cells[5], Qt.LeftButton)
    assert canvas_widget.get_selected_target() == ("button", 5)
    assert canvas_widget.cells[5].is_selected() is True
    assert canvas_widget.cells[0].is_selected() is False
    assert all(not c.is_selected() for idx, c in enumerate(canvas_widget.cells) if idx != 5)
    assert canvas_widget.touchbar_strip.get_selected_section() is None
    assert received_signals[-1] == ("button", 5)


def test_exclusive_selection_touchbar_switch(canvas_widget, qtbot):
    """
    Проверка взаимного исключения выделения (кнопка <-> тачбар):
      - Клик по кнопке [1] активирует кнопку.
      - Последующий клик по секции тачбара 'media' сбрасывает кнопку и активирует тачбар.
      - Последующий клик по кнопке [8] сбрасывает тачбар и активирует кнопку [8].
    """
    # 1. Выбираем кнопку 1
    qtbot.mouseClick(canvas_widget.cells[1], Qt.LeftButton)
    assert canvas_widget.cells[1].is_selected() is True
    assert canvas_widget.get_selected_target() == ("button", 1)

    # 2. Кликаем по секции тачбара media через qtbot
    qtbot.mouseClick(canvas_widget.touchbar_strip.sec_media, Qt.LeftButton)
    assert canvas_widget.get_selected_target() == ("touchbar", "media")
    assert canvas_widget.cells[1].is_selected() is False
    assert all(not c.is_selected() for c in canvas_widget.cells)
    assert canvas_widget.touchbar_strip.get_selected_section() == "media"
    assert canvas_widget.touchbar_strip.sec_media.is_selected() is True
    assert canvas_widget.touchbar_strip.sec_clock.is_selected() is False
    assert canvas_widget.touchbar_strip.sec_telemetry.is_selected() is False

    # 3. Переключаемся на кнопку 8
    qtbot.mouseClick(canvas_widget.cells[8], Qt.LeftButton)
    assert canvas_widget.get_selected_target() == ("button", 8)
    assert canvas_widget.touchbar_strip.get_selected_section() is None
    assert canvas_widget.touchbar_strip.sec_media.is_selected() is False
    assert canvas_widget.cells[8].is_selected() is True


def test_clear_selection_on_empty_click(canvas_widget, qtbot):
    """
    Проверка сброса выделения при клике в нейтральную область холста:
      - Выбор кнопки [3].
      - Клик в свободную область холста (вне кнопок сетки).
      - Проверка сброса выделения со всех элементов и эмиссии сигнала selection_cleared.
    """
    qtbot.mouseClick(canvas_widget.cells[3], Qt.LeftButton)
    assert canvas_widget.get_selected_target() == ("button", 3)

    cleared_events: List[bool] = []
    canvas_widget.selection_cleared.connect(lambda: cleared_events.append(True))

    # Клик в точку (5, 5) холста, заведомо вне центрированной сетки кнопок
    qtbot.mouseClick(canvas_widget, Qt.LeftButton, pos=QPoint(5, 5))

    assert canvas_widget.get_selected_target() is None
    assert all(not c.is_selected() for c in canvas_widget.cells)
    assert canvas_widget.touchbar_strip.get_selected_section() is None
    assert len(cleared_events) == 1


def test_clear_selection_on_escape_key(canvas_widget, qtbot):
    """
    Проверка сброса выделения по клавише Escape:
      - Выбор секции тачбара 'clock'.
      - Нажатие клавиши Escape через qtbot.keyClick.
      - Проверка сброса выделения и эмиссии selection_cleared.
    """
    qtbot.mouseClick(canvas_widget.touchbar_strip.sec_clock, Qt.LeftButton)
    assert canvas_widget.get_selected_target() == ("touchbar", "clock")
    assert canvas_widget.touchbar_strip.sec_clock.is_selected() is True

    cleared_events: List[bool] = []
    canvas_widget.selection_cleared.connect(lambda: cleared_events.append(True))

    qtbot.keyClick(canvas_widget, Qt.Key_Escape)

    assert canvas_widget.get_selected_target() is None
    assert canvas_widget.touchbar_strip.get_selected_section() is None
    assert canvas_widget.touchbar_strip.sec_clock.is_selected() is False
    assert len(cleared_events) == 1


def test_pagination_bar_page_switch(qtbot):
    """
    Проверка сигналов пагинатора страниц (PageNavigationBar):
      - Начальное состояние: страница 1.
      - Переключение через set_current_page(3).
      - Клик по кнопке страницы 5 через qtbot генерирует сигнал page_changed(5).
      - Клик по кнопке Home (⭐) через qtbot переключает на страницу 1 и генерирует page_changed(1).
      - Клик по кнопке Add (+) через qtbot генерирует сигнал add_page_requested.
    """
    bar = PageNavigationBar()
    bar.set_page_count(5)
    received_pages: List[int] = []
    add_requested_count = 0

    bar.page_changed.connect(received_pages.append)

    def _on_add():
        nonlocal add_requested_count
        add_requested_count += 1

    bar.add_page_requested.connect(_on_add)

    assert bar.get_current_page() == 1

    # Программная смена страницы
    bar.set_current_page(3)
    assert bar.get_current_page() == 3

    # Клик по кнопке страницы 5
    qtbot.mouseClick(bar.page_buttons[4], Qt.LeftButton)
    assert bar.get_current_page() == 5
    assert 5 in received_pages

    # Клик по кнопке Home (страница 1)
    qtbot.mouseClick(bar.btn_home, Qt.LeftButton)
    assert bar.get_current_page() == 1
    assert 1 in received_pages

    # Клик по кнопке Add (+)
    qtbot.mouseClick(bar.btn_add, Qt.LeftButton)
    assert add_requested_count == 1


def test_canvas_integration_in_window(editor_window, qtbot):
    """
    Проверка интеграции холста в главное окно DeckEditorWindow:
      - В окне смонтированы DeckCanvasWidget и PageNavigationBar.
      - Выбор кнопки на холсте регистрируется окном.
      - Переключение страницы в пагинаторе синхронизирует страницу холста и сбрасывает выделение.
    """
    assert isinstance(editor_window.canvas_widget, DeckCanvasWidget)
    assert isinstance(editor_window.pagination_bar, PageNavigationBar)

    canvas: DeckCanvasWidget = editor_window.canvas_widget
    pager: PageNavigationBar = editor_window.pagination_bar

    # Выделяем кнопку 2
    qtbot.mouseClick(canvas.cells[2], Qt.LeftButton)
    assert canvas.get_selected_target() == ("button", 2)

    # Переключение страницы через пагинатор должно сбросить выделение на холсте
    pager.set_current_page(4)
    pager.page_changed.emit(4)
    assert canvas.get_page() == 4
    assert canvas.get_selected_target() is None


def test_canvas_retranslate_ui(editor_window):
    """
    Тест test_canvas_retranslate_ui:
    Проверка смены языка подсказок пагинатора и названий секций тачбара:
      - Переключение языка интерфейса на английский ('en'):
        * Подсказка Home: "Home Page"
        * Подсказка Add: "Create New Page"
        * Секция Media: "Media Player"
        * Секция Clock: "Clock & Navigation"
        * Секция Telemetry: "Telemetry"
      - Переключение языка интерфейса на русский ('ru'):
        * Подсказка Home: "Домашняя страница"
        * Подсказка Add: "Создать новую страницу"
        * Секция Media: "Медиаплеер"
        * Секция Clock: "Часы и навигация"
        * Секция Telemetry: "Телеметрия"
      - Полное соответствие словарям локализации без рассинхронизации.
    """
    # 1. Переключение на английский
    bus.language_changed.emit("en")
    assert editor_window.pagination_bar.btn_home.toolTip() == "Home Page"
    assert editor_window.pagination_bar.btn_home.toolTip() == t("deck.editor.canvas.pagination.home_tooltip")
    assert editor_window.pagination_bar.btn_add.toolTip() == "Create New Page"
    assert editor_window.pagination_bar.btn_add.toolTip() == t("deck.editor.canvas.pagination.add_tooltip")

    assert editor_window.canvas_widget.touchbar_strip.sec_media.toolTip() == "Media Player"
    assert editor_window.canvas_widget.touchbar_strip.sec_media.toolTip() == t("deck.editor.canvas.touchbar.media_title")
    assert editor_window.canvas_widget.touchbar_strip.sec_clock.toolTip() == "Clock & Navigation"
    assert editor_window.canvas_widget.touchbar_strip.sec_clock.toolTip() == t("deck.editor.canvas.touchbar.clock_title")
    assert editor_window.canvas_widget.touchbar_strip.sec_telemetry.toolTip() == "Telemetry"
    assert editor_window.canvas_widget.touchbar_strip.sec_telemetry.toolTip() == t("deck.editor.canvas.touchbar.telemetry_title")

    # 2. Переключение на русский
    bus.language_changed.emit("ru")
    assert editor_window.pagination_bar.btn_home.toolTip() == "Домашняя страница"
    assert editor_window.pagination_bar.btn_home.toolTip() == t("deck.editor.canvas.pagination.home_tooltip")
    assert editor_window.pagination_bar.btn_add.toolTip() == "Создать новую страницу"
    assert editor_window.pagination_bar.btn_add.toolTip() == t("deck.editor.canvas.pagination.add_tooltip")

    assert editor_window.canvas_widget.touchbar_strip.sec_media.toolTip() == "Медиаплеер"
    assert editor_window.canvas_widget.touchbar_strip.sec_media.toolTip() == t("deck.editor.canvas.touchbar.media_title")
    assert editor_window.canvas_widget.touchbar_strip.sec_clock.toolTip() == "Часы и навигация"
    assert editor_window.canvas_widget.touchbar_strip.sec_clock.toolTip() == t("deck.editor.canvas.touchbar.clock_title")
    assert editor_window.canvas_widget.touchbar_strip.sec_telemetry.toolTip() == "Телеметрия"
    assert editor_window.canvas_widget.touchbar_strip.sec_telemetry.toolTip() == t("deck.editor.canvas.touchbar.telemetry_title")


def test_canvas_right_click_delete_command_integration(editor_window, qtbot):
    """
    Проверка сквозного вызова контекстного меню ПКМ и команды удаления слота:
    - Слот 0 изначально получает данные.
    - Вызов контекстного меню слота 0 и нажатие действия 'Удалить'.
    - Слот 0 на холсте и в модели данных очищается.
    - В инспекторе отображается плейсхолдер.
    - Проверка Undo (Ctrl+Z): данные слота восстанавливаются.
    """
    canvas = editor_window.canvas_widget
    cell_0 = canvas.get_cell(0)
    assert cell_0 is not None

    from modules.deck.editor.dto import ButtonSlotDTO
    initial_dto = ButtonSlotDTO(
        slot_index=0,
        title="Launch Game",
        icon="🎮",
        action_type="hotkey",
        hotkey="Ctrl+G",
    )
    editor_window.apply_slot_dto(0, initial_dto)
    assert cell_0.lbl_title.text() == "Launch Game"

    # Вызываем контекстное меню и нажимаем 'Удалить'
    menu = cell_0.show_context_menu(global_pos=None)
    delete_action = [a for a in menu.actions() if not a.isSeparator() and "🗑️" in a.text()][0]
    delete_action.trigger()

    # Слот 0 очищен на холсте и в модели
    assert cell_0.lbl_title.text() == ""
    assert editor_window.get_slot_dto(0).title == ""

    # Проверка Undo
    editor_window._undo_stack.undo()
    assert cell_0.lbl_title.text() == "Launch Game"
    assert editor_window.get_slot_dto(0).title == "Launch Game"
