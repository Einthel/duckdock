"""
Модульные тесты для шагов 5.1, 5.2 и 5.3:
DTO каталога действий, реестра действий, стилей и строки поиска ActionSearchBar.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from core.i18n import I18nManager, t
from modules.deck.editor.actions_registry import get_default_action_catalog
from modules.deck.editor.dto import ActionCategoryDTO, ActionItemDTO
from modules.deck.editor.styles import (
    ACTION_ITEM_HEIGHT,
    BG_ACTION_ITEM_ACTIVE,
    BG_ACTION_ITEM_HOVER,
    BG_SEARCH_INPUT,
    CATEGORY_HEADER_HEIGHT,
    CHEVRON_COLOR,
    DRAWER_PADDING,
    EDITOR_MAIN_QSS,
    SEARCH_BAR_HEIGHT,
    SEARCH_SLOT_HEIGHT,
    SURFACE_2_CARD,
    SURFACE_3_HOVER,
    TEXT_CATEGORY_TITLE,
    TEXT_MUTED_SUBTLE,
    TEXT_PRIMARY_HIGH,
)
from modules.deck.editor.widgets.search_bar import ActionSearchBar


@pytest.fixture(autouse=True)
def reset_locale():
    """Сбрасывает локаль после каждого теста."""
    orig = I18nManager().current_language
    yield
    I18nManager().set_language(orig, emit_signal=False)


def test_action_item_and_category_dto():
    """Проверка структуры ActionItemDTO и ActionCategoryDTO и локализации через get_title()."""
    item = ActionItemDTO(
        id="test_hotkey",
        title_key="deck.editor.drawer.actions.hotkey",
        category_key="deck.editor.drawer.categories.system",
        icon="⌨️",
        keywords=["hotkey", "хоткей"],
    )
    cat = ActionCategoryDTO(
        id="system",
        title_key="deck.editor.drawer.categories.system",
        icon="⚙️",
        items=[item],
        is_expanded=True,
    )

    I18nManager().set_language("en", emit_signal=False)
    assert item.get_title() == "Hotkey"
    assert cat.get_title() == "System"

    I18nManager().set_language("ru", emit_signal=False)
    assert item.get_title() == "Хоткей"
    assert cat.get_title() == "Система"


def test_default_action_catalog_structure():
    """Проверка структуры и наполнения реестра get_default_action_catalog()."""
    catalog = get_default_action_catalog()
    assert len(catalog) == 6

    category_ids = [cat.id for cat in catalog]
    expected_categories = [
        "multi_action",
        "navigation",
        "soundboard",
        "stream_deck",
        "system",
        "volume_controller",
    ]
    assert category_ids == expected_categories

    for cat in catalog:
        assert cat.title_key.startswith("deck.editor.drawer.categories.")
        assert len(cat.items) > 0
        for item in cat.items:
            assert item.title_key.startswith("deck.editor.drawer.actions.")
            assert item.category_key == cat.title_key
            assert bool(item.icon)
            # Двуязычные ключевые слова: проверяем наличие латиницы и кириллицы
            assert len(item.keywords) >= 2
            has_latin = any(k.isascii() for k in item.keywords)
            has_cyrillic = any(any("\u0400" <= ch <= "\u04ff" for ch in k) for k in item.keywords)
            assert has_latin, f"У действия {item.id} отсутствуют английские ключевые слова"
            assert has_cyrillic, f"У действия {item.id} отсутствуют русские ключевые слова"


def test_action_library_styles_and_tokens():
    """Проверка дизайн-токенов и наличия правил QSS для библиотеки действий."""
    assert SEARCH_BAR_HEIGHT == 36
    assert ACTION_ITEM_HEIGHT == 36
    assert CATEGORY_HEADER_HEIGHT == 38
    assert DRAWER_PADDING == 8

    assert BG_SEARCH_INPUT == SURFACE_2_CARD
    assert BG_ACTION_ITEM_HOVER == SURFACE_3_HOVER
    assert BG_ACTION_ITEM_ACTIVE == "#192338"
    assert TEXT_CATEGORY_TITLE == TEXT_PRIMARY_HIGH
    assert CHEVRON_COLOR == TEXT_MUTED_SUBTLE

    # Проверка наличия ключевых селекторов в EDITOR_MAIN_QSS
    assert "ActionSearchInput" in EDITOR_MAIN_QSS
    assert "SearchClearButton" in EDITOR_MAIN_QSS
    assert "ActionViewButton" in EDITOR_MAIN_QSS
    assert "ActionCategoryHeader" in EDITOR_MAIN_QSS
    assert "CategoryChevron" in EDITOR_MAIN_QSS
    assert "CategoryTitle" in EDITOR_MAIN_QSS
    assert "ActionItemCard" in EDITOR_MAIN_QSS
    assert "ActionItemIconBox" in EDITOR_MAIN_QSS
    assert "ActionItemTitle" in EDITOR_MAIN_QSS
    assert "SearchEmptyPlaceholder" in EDITOR_MAIN_QSS


def test_search_bar_initialization(qapp):
    """Проверка инициализации ActionSearchBar: высота 52 px, локализация и начальное состояние."""
    I18nManager().set_language("en", emit_signal=False)
    bar = ActionSearchBar()
    bar.show()
    qapp.processEvents()
    assert bar.height() == SEARCH_SLOT_HEIGHT
    assert bar.search_input.height() == SEARCH_BAR_HEIGHT
    assert bar.search_input.placeholderText() == "Search..."
    assert bar.btn_view_options.toolTip() == "Action display options"
    assert not bar.btn_clear.isVisible()
    assert bar.get_query() == ""


def test_search_bar_interaction_and_signals(qapp):
    """Проверка ввода текста, появления кнопки очистки и эмиссии сигналов."""
    bar = ActionSearchBar()
    bar.show()
    qapp.processEvents()

    emitted_queries = []
    bar.search_changed.connect(emitted_queries.append)

    # Ввод запроса
    bar.search_input.setText("hotkey")
    qapp.processEvents()
    assert bar.btn_clear.isVisible()
    assert bar.get_query() == "hotkey"
    assert "hotkey" in emitted_queries

    # Клик по кнопке очистки
    bar.btn_clear.click()
    qapp.processEvents()
    assert bar.get_query() == ""
    assert not bar.btn_clear.isVisible()
    assert emitted_queries[-1] == ""
    assert bar.search_input.hasFocus()


def test_search_bar_clear_and_focus_api(qapp):
    """Проверка публичных методов clear_query() и set_focus()."""
    bar = ActionSearchBar()
    bar.show()
    qapp.processEvents()

    bar.search_input.setText("volume")
    qapp.processEvents()
    assert bar.btn_clear.isVisible()

    bar.clear_query()
    qapp.processEvents()
    assert bar.get_query() == ""
    assert not bar.btn_clear.isVisible()

    bar.set_focus()
    assert bar.search_input.hasFocus()


def test_search_bar_view_options_signal(qapp):
    """Проверка эмиссии сигнала view_options_clicked при клике на ☰."""
    bar = ActionSearchBar()
    bar.show()
    qapp.processEvents()

    clicked = []
    bar.view_options_clicked.connect(lambda: clicked.append(True))

    bar.btn_view_options.click()
    assert len(clicked) == 1


def test_search_bar_retranslate_ui(qapp):
    """Проверка метода retranslate_ui() при смене локали."""
    bar = ActionSearchBar()
    bar.show()
    qapp.processEvents()

    I18nManager().set_language("ru", emit_signal=False)
    bar.retranslate_ui()
    assert bar.search_input.placeholderText() == "Поиск..."
    assert bar.btn_view_options.toolTip() == "Параметры отображения действий"

    I18nManager().set_language("en", emit_signal=False)
    bar.retranslate_ui()
    assert bar.search_input.placeholderText() == "Search..."
    assert bar.btn_view_options.toolTip() == "Action display options"
