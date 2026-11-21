"""
Модульные тесты для стилей и плейсхолдеров редактора DuckDeck (Шаги 1.1, 1.2, 1.3).
"""
import pytest
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QWidget

from core.i18n import I18nManager, t
from modules.deck.editor.styles import (
    BG_CARD,
    BG_PANEL,
    BG_STRIP,
    BG_WINDOW,
    BORDER_FOCUS,
    BORDER_FOCUS_ACCENT,
    BORDER_SUBTLE,
    CANVAS_SLOT_MIN_HEIGHT,
    EDITOR_MAIN_QSS,
    HEADER_SLOT_HEIGHT,
    INSPECTOR_SLOT_HEIGHT,
    PAGINATION_SLOT_HEIGHT,
    SEARCH_SLOT_HEIGHT,
    TEXT_PLACEHOLDER,
    TEXT_PRIMARY,
    WINDOW_DEFAULT_SIZE,
    WINDOW_MIN_SIZE,
    apply_editor_theme,
    apply_immersive_dark_titlebar,
)
from modules.deck.editor.widgets.placeholders import (
    ActionListSlot,
    CanvasAreaSlot,
    HeaderBarSlot,
    InspectorSlot,
    PaginationBarSlot,
    PlaceholderBox,
    SearchSlot,
)


def test_deck_editor_i18n_keys():
    """Проверка доступности ключевых строк deck.editor.* в RU и EN."""
    i18n = I18nManager()
    i18n.reload()

    i18n.set_language("en", emit_signal=False)
    assert t("deck.editor.window.title") == "DuckDeck Button & Touchbar Editor"
    assert t("deck.editor.inspector.placeholder") == "Select a key to configure its action."
    assert t("deck.editor.drawer.search_placeholder") == "Search..."
    assert t("deck.editor.drawer.no_results", query="test") == 'No actions found matching "test"'

    i18n.set_language("ru", emit_signal=False)
    assert t("deck.editor.window.title") == "Редактор кнопок и тачбара DuckDeck"
    assert t("deck.editor.inspector.placeholder") == "Выберите кнопку для настройки действия."
    assert t("deck.editor.drawer.search_placeholder") == "Поиск..."
    assert t("deck.editor.drawer.no_results", query="тест") == 'Действий по запросу "тест" не найдено'


def test_styles_tokens_and_qss():
    """Проверка дизайн-токенов Dark Obsidian и наличия селекторов в EDITOR_MAIN_QSS."""
    assert BG_WINDOW == "#121214"
    assert BG_PANEL == "#18181b"
    assert BG_CARD == "#222227"
    assert BG_STRIP == "#161b26"
    assert BORDER_SUBTLE == "#2e2e36"
    assert BORDER_FOCUS == "#0078d4"
    assert BORDER_FOCUS_ACCENT == "#38bdf8"
    assert TEXT_PRIMARY == "#f4f4f5"
    assert TEXT_PLACEHOLDER == "#71717a"
    assert WINDOW_DEFAULT_SIZE == (1080, 740)
    assert WINDOW_MIN_SIZE == (960, 640)

    # Проверка селекторов в QSS
    assert "QSplitter::handle:horizontal" in EDITOR_MAIN_QSS
    assert "#38bdf8" in EDITOR_MAIN_QSS
    assert "QScrollBar:vertical" in EDITOR_MAIN_QSS
    assert "width: 6px" in EDITOR_MAIN_QSS
    assert 'placeholderBox="true"' in EDITOR_MAIN_QSS
    assert 'placeholderLabel="true"' in EDITOR_MAIN_QSS


def test_apply_immersive_dark_titlebar_and_theme(qapp):
    """Проверка безопасной функции применения темы и темного заголовка."""
    window = QMainWindow()
    # Функция должна безопасно отрабатывать без исключений
    result = apply_immersive_dark_titlebar(window)
    assert isinstance(result, bool)

    # Тестирование с некорректным объектом (защита от падений)
    assert apply_immersive_dark_titlebar(None) is False
    assert apply_immersive_dark_titlebar(object()) is False

    # Фасадная функция применения темы
    apply_editor_theme(window)
    assert len(window.styleSheet()) > 0
    assert "#121214" in window.styleSheet()


def test_placeholder_box_widget(qapp):
    """Проверка базового виджета PlaceholderBox."""
    box = PlaceholderBox(label="Test Label", min_height=50)
    assert box.property("placeholderBox") == "true"
    assert box.get_label_text() == "Test Label"
    assert box.minimumHeight() == 50

    box.set_label_text("Updated Label")
    assert box.get_label_text() == "Updated Label"

    fixed_box = PlaceholderBox(label="Fixed", fixed_height=80)
    assert fixed_box.maximumHeight() == 80
    assert fixed_box.minimumHeight() == 80


def test_placeholder_slots_dimensions(qapp):
    """Проверка геометрических параметров специализированных слотов-заглушек."""
    header = HeaderBarSlot()
    assert header.height() == HEADER_SLOT_HEIGHT or header.maximumHeight() == HEADER_SLOT_HEIGHT

    canvas = CanvasAreaSlot()
    assert canvas.minimumHeight() == CANVAS_SLOT_MIN_HEIGHT
    assert canvas.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding
    assert canvas.sizePolicy().verticalPolicy() == QSizePolicy.Expanding

    pagination = PaginationBarSlot()
    assert pagination.maximumHeight() == PAGINATION_SLOT_HEIGHT

    inspector = InspectorSlot()
    assert inspector.maximumHeight() == INSPECTOR_SLOT_HEIGHT

    search = SearchSlot()
    assert search.maximumHeight() == SEARCH_SLOT_HEIGHT

    action_list = ActionListSlot()
    assert action_list.minimumHeight() == 100
    assert action_list.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
