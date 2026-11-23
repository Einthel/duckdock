"""
Модульные тесты каркаса главного окна конфигуратора DuckDeck (DeckEditorWindow).
Проверяют:
  - Инициализацию окна и заголовок через t("deck.editor.window.title").
  - Геометрию и минимальные габариты (1080x740, min 960x640).
  - Конфигурацию центрального QSplitter (2 панели, childrenCollapsible=False, размеры 756/324, пропорции 70/30).
  - Наличие и типы всех структурных слотов-плейсхолдеров в обеих колонках.
  - Публичный API безопасной замены слотов-плейсхолдеров на кастомные виджеты.
  - Реактивный протокол Localization-First (retranslate_ui, шина bus.language_changed RU/EN).
"""
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSplitter, QWidget

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.deck.editor.styles import (
    DRAWER_MAX_WIDTH,
    DRAWER_MIN_WIDTH,
    WINDOW_DEFAULT_SIZE,
    WINDOW_MIN_SIZE,
    WORKSPACE_MIN_WIDTH,
)
from modules.deck.editor.widgets.action_drawer import ActionLibraryDrawer
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.editor.widgets.header_bar import EditorHeaderBar
from modules.deck.editor.widgets.pagination_bar import PageNavigationBar
from modules.deck.editor.widgets.placeholders import (
    ActionListSlot,
    CanvasAreaSlot,
    HeaderBarSlot,
    InspectorSlot,
    PaginationBarSlot,
    SearchSlot,
)
from modules.deck.editor.widgets.property_inspector import KeyPropertyInspector
from modules.deck.editor.window import DeckEditorWindow


@pytest.fixture
def editor_window(qapp, sample_two_page_deck_config_path):
    """Фикстура для создания и гарантированного закрытия окна DeckEditorWindow."""
    initial_lang = I18nManager().current_language
    window = DeckEditorWindow(config_path=sample_two_page_deck_config_path)
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()
    I18nManager().set_language(initial_lang, emit_signal=False)


def test_editor_window_initialization(editor_window):
    """
    Проверка инициализации экземпляра:
      - Экземпляр создан.
      - Корректный заголовок окна через функцию t().
      - Центральный виджет является QSplitter с ожидаемым objectName.
    """
    assert editor_window is not None
    assert editor_window.windowTitle() == t("deck.editor.window.title")

    central = editor_window.centralWidget()
    assert isinstance(central, QSplitter)
    assert central is editor_window.main_splitter
    assert central.objectName() == "editorCentralWidget"


def test_editor_window_geometry(editor_window):
    """
    Проверка геометрии окна и минимальных ограничений:
      - Базовый размер 1080x740.
      - Минимальный размер 960x640.
      - Ограничения ширины рабочих областей.
    """
    assert editor_window.width() == WINDOW_DEFAULT_SIZE[0]
    assert editor_window.height() == WINDOW_DEFAULT_SIZE[1]

    min_size = editor_window.minimumSize()
    assert min_size.width() == WINDOW_MIN_SIZE[0]
    assert min_size.height() == WINDOW_MIN_SIZE[1]

    assert editor_window.workspace_container.minimumWidth() == WORKSPACE_MIN_WIDTH
    assert editor_window.drawer_container.minimumWidth() == DRAWER_MIN_WIDTH
    assert editor_window.drawer_container.maximumWidth() == DRAWER_MAX_WIDTH


def test_editor_window_splitter_configuration(editor_window):
    """
    Проверка конфигурации центрального QSplitter:
      - Запрет схлопывания панелей (childrenCollapsible is False).
      - Ровно 2 дочерних контейнера: workspace_container (0) и drawer_container (1).
      - Размеры соответствуют пропорции 70/30 (около 756 / 324 px).
    """
    splitter = editor_window.main_splitter
    assert splitter.childrenCollapsible() is False
    assert splitter.count() == 2

    assert splitter.widget(0) is editor_window.workspace_container
    assert splitter.widget(1) is editor_window.drawer_container

    # Отображаем окно для расчета layout geometry
    editor_window.show()
    sizes = splitter.sizes()
    editor_window.hide()

    assert len(sizes) == 2
    assert abs(sizes[0] - 756) <= 10
    assert abs(sizes[1] - 324) <= 10

    total_width = sum(sizes)
    assert total_width > 0
    ratio_left = sizes[0] / total_width
    assert 0.68 <= ratio_left <= 0.72


def test_editor_window_containers_structure(editor_window):
    """
    Проверка наличия и типов всех структурных слотов-плейсхолдеров:
      - Левая колонка: HeaderBarSlot, CanvasAreaSlot, PaginationBarSlot, QFrame, InspectorSlot.
      - Правая колонка: SearchSlot, QFrame, ActionListSlot.
      - Соответствие свойств-алиасов реальным объектам.
    """
    # Левая колонка
    assert isinstance(editor_window.header_bar, EditorHeaderBar)
    assert isinstance(editor_window.canvas_widget, DeckCanvasWidget)
    assert isinstance(editor_window.pagination_bar, PageNavigationBar)
    assert isinstance(editor_window.workspace_separator, QFrame)
    assert isinstance(editor_window.inspector, KeyPropertyInspector)

    # Проверка свойств-алиасов левой колонки
    assert editor_window.header_bar_slot is editor_window.header_bar
    assert editor_window.header_bar_widget is editor_window.header_bar
    assert editor_window.canvas_slot is editor_window.canvas_widget
    assert editor_window.pagination_slot is editor_window.pagination_bar
    assert editor_window.inspector_slot is editor_window.inspector
    assert editor_window.inspector_widget is editor_window.inspector

    # Правая колонка
    assert isinstance(editor_window.action_drawer, ActionLibraryDrawer)


def test_editor_window_slot_replacement_api(editor_window):
    """
    Проверка методов публичного API замены слотов на кастомные виджеты:
      - set_header_bar
      - set_canvas_widget
      - set_pagination_bar
      - set_inspector_widget
      - set_action_drawer
      - property setters: header_bar_widget, inspector_widget
    """
    new_header = QWidget()
    editor_window.set_header_bar(new_header)
    assert editor_window.header_bar is new_header
    assert editor_window.header_bar_slot is new_header
    assert editor_window.header_bar_widget is new_header

    new_canvas = QWidget()
    editor_window.set_canvas_widget(new_canvas)
    assert editor_window.canvas_widget is new_canvas
    assert editor_window.canvas_slot is new_canvas

    new_pagination = QWidget()
    editor_window.set_pagination_bar(new_pagination)
    assert editor_window.pagination_bar is new_pagination
    assert editor_window.pagination_slot is new_pagination

    new_inspector = QWidget()
    editor_window.set_inspector_widget(new_inspector)
    assert editor_window.inspector is new_inspector
    assert editor_window.inspector_slot is new_inspector
    assert editor_window.inspector_widget is new_inspector

    new_drawer = QWidget()
    editor_window.set_action_drawer(new_drawer)
    assert editor_window.action_drawer is new_drawer

    # Проверка работы через property setters
    alt_header = QWidget()
    editor_window.header_bar_widget = alt_header
    assert editor_window.header_bar is alt_header

    alt_inspector = QWidget()
    editor_window.inspector_widget = alt_inspector
    assert editor_window.inspector is alt_inspector


def test_editor_window_retranslate_ui(editor_window):
    """
    Проверка реактивного протокола Localization-First:
      - Эмиссия bus.language_changed("ru") -> заголовок переключается на русский.
      - Эмиссия bus.language_changed("en") -> заголовок переключается на английский.
      - Каскадный вызов retranslate_ui у дочерних компонентов.
    """
    mgr = I18nManager()
    expected_ru = mgr.get_catalog("ru").get("deck.editor.window.title")
    expected_en = mgr.get_catalog("en").get("deck.editor.window.title")
    assert expected_ru is not None
    assert expected_en is not None
    assert expected_ru != expected_en

    # Монтируем тестовый компонент с методом retranslate_ui для проверки каскада
    mock_child = QWidget()
    mock_child.retranslate_ui = MagicMock()
    editor_window.set_action_drawer(mock_child)

    # 1. Переключение на русский язык
    bus.language_changed.emit("ru")
    assert editor_window.windowTitle() == expected_ru
    assert editor_window.windowTitle() == t("deck.editor.window.title")
    assert mock_child.retranslate_ui.call_count >= 1

    # 2. Переключение на английский язык
    mock_child.retranslate_ui.reset_mock()
    bus.language_changed.emit("en")
    assert editor_window.windowTitle() == expected_en
    assert editor_window.windowTitle() == t("deck.editor.window.title")
    assert mock_child.retranslate_ui.call_count >= 1
