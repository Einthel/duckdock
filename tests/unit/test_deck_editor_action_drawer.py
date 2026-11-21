"""
Комплексные модульные и интеграционные тесты библиотеки действий DuckDeck (Action Library Drawer)
согласно шагу 5.7 из .md/deck/edit_but.md.

Проверяют:
1. test_action_catalog_registry:
   - Проверка структуры и корректности наполнения get_default_action_catalog()
     (наличие всех 6 категорий, обязательных действий, двуязычных тегов keywords).
2. test_search_bar_interaction:
   - Интерактивность строки поиска (ввод текста, эмиссия search_changed,
     клик по кнопке ✕ -> очистка поля, скрытие кнопки и возврат фокуса, кнопка вида ☰).
3. test_action_accordion_collapse_expand:
   - Сворачивание и разворачивание секций аккордеона по клику на заголовок,
     состояние шеврона (› / ⌄), видимость body_widget, эмиссия expanded_changed.
4. test_action_search_bilingual:
   - Полноценный двуязычный поиск:
     * Английское ключевое слово ("hotkey") -> секция System раскрыта, действие Hotkey отображается.
     * Русское ключевое слово ("хоткей") -> секция System раскрыта, действие Hotkey отображается благодаря keywords.
     * Поиск по слову "папка" / "folder" -> раскрыта категория Navigation с действием Create Folder.
     * Поиск несуществующего слова ("abracadabra") -> все категории скрыты, отображается
       локализованный плейсхолдер с подстановкой {query} (deck.editor.drawer.no_results).
     * Очистка поисковой строки -> восстановление исходной видимости категорий.
5. test_action_drawer_retranslate_ui:
   - Динамическая смена языка каталога: обновление плейсхолдера поиска, подсказки кнопки вида,
     заголовков категорий и карточек без схлопывания раскрытых веток.
6. test_action_item_selection:
   - Клик по карточке действия -> эмиссия сигнала action_picked в ActionLibraryDrawer
     и item_clicked в ActionItemWidget с корректным ActionItemDTO.
7. test_action_drawer_window_integration:
   - Интеграционный тест внутри DeckEditorWindow: выбор ячейки слота 0 на холсте ->
     клик по действию "Website" в каталоге -> проверка обновления DTO кнопки,
     названия в инспекторе и превью на холсте.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.deck.editor.actions_registry import get_default_action_catalog
from modules.deck.editor.dto import ActionCategoryDTO, ActionItemDTO, ButtonSlotDTO
from modules.deck.editor.widgets.action_category import ActionCategorySection
from modules.deck.editor.widgets.action_drawer import (
    ActionAccordionWidget,
    ActionLibraryDrawer,
)
from modules.deck.editor.widgets.action_item import ActionItemWidget
from modules.deck.editor.widgets.property_inspector import KeyPropertyInspector
from modules.deck.editor.widgets.search_bar import ActionSearchBar
from modules.deck.editor.window import DeckEditorWindow


@pytest.fixture(autouse=True)
def reset_i18n_language():
    """Гарантирует сброс языка локализации к исходному после каждого теста."""
    initial_lang = I18nManager().current_language
    yield
    I18nManager().set_language(initial_lang, emit_signal=False)


@pytest.fixture
def action_catalog() -> list[ActionCategoryDTO]:
    """Возвращает стандартный каталог библиотеки действий."""
    return get_default_action_catalog()


# ==============================================================================
# 1. Реестр действий и структура DTO
# ==============================================================================


def test_action_catalog_registry(action_catalog):
    """
    Проверка статического реестра действий get_default_action_catalog():
    - Ровно 6 обязательных категорий (multi_action, navigation, soundboard,
      stream_deck, system, volume_controller).
    - Каждая категория содержит валидные id, title_key, иконку и непустой список items.
    - Проверка наличия ключевых действий в категориях:
      * multi_action: multi_action, multi_action_switch
      * navigation: create_folder, switch_profile, prev_page, next_page, goto_page, page_indicator
      * soundboard: play_audio, stop_audio
      * stream_deck: brightness, sleep_display
      * system: hotkey, open_app, open_website, text_macro
      * volume_controller: mute_audio, volume_up, volume_down, toggle_device
    - Проверка наличия двуязычных ключевых слов (RU и EN) у действий.
    """
    expected_categories = [
        "multi_action",
        "navigation",
        "soundboard",
        "stream_deck",
        "system",
        "volume_controller",
    ]
    catalog_category_ids = [cat.id for cat in action_catalog]
    assert catalog_category_ids == expected_categories

    for cat in action_catalog:
        assert cat.id, "Category ID must not be empty"
        assert cat.title_key.startswith("deck.editor.drawer.categories."), (
            f"Invalid title_key: {cat.title_key}"
        )
        assert cat.get_title(), f"Localized title missing for category {cat.id}"
        assert len(cat.items) > 0, f"Category {cat.id} must contain action items"

        for item in cat.items:
            assert item.id, f"Item ID must not be empty in category {cat.id}"
            assert item.title_key.startswith("deck.editor.drawer.actions."), (
                f"Invalid title_key: {item.title_key}"
            )
            assert item.category_key == cat.title_key
            assert item.icon, f"Icon must not be empty for action {item.id}"
            assert item.get_title(), f"Localized title missing for action {item.id}"
            assert len(item.keywords) > 0, f"Keywords must not be empty for action {item.id}"

            # Проверка двуязычности keywords (наличие латиницы и кириллицы)
            has_latin = any(any("a" <= char <= "z" for char in kw.lower()) for kw in item.keywords)
            has_cyrillic = any(
                any("а" <= char <= "я" for char in kw.lower()) for kw in item.keywords
            )
            assert has_latin, f"Action {item.id} must have English keywords"
            assert has_cyrillic, f"Action {item.id} must have Russian keywords"

    # Точечная проверка обязательных идентификаторов действий
    actions_map = {cat.id: [it.id for it in cat.items] for cat in action_catalog}
    assert "multi_action" in actions_map["multi_action"]
    assert "multi_action_switch" in actions_map["multi_action"]
    assert "create_folder" in actions_map["navigation"]
    assert "switch_profile" in actions_map["navigation"]
    assert "prev_page" in actions_map["navigation"]
    assert "next_page" in actions_map["navigation"]
    assert "play_audio" in actions_map["soundboard"]
    assert "stop_audio" in actions_map["soundboard"]
    assert "brightness" in actions_map["stream_deck"]
    assert "sleep_display" in actions_map["stream_deck"]
    assert "hotkey" in actions_map["system"]
    assert "open_app" in actions_map["system"]
    assert "open_website" in actions_map["system"]
    assert "text_macro" in actions_map["system"]
    assert "mute_audio" in actions_map["volume_controller"]
    assert "volume_up" in actions_map["volume_controller"]
    assert "volume_down" in actions_map["volume_controller"]
    assert "toggle_device" in actions_map["volume_controller"]


# ==============================================================================
# 2. Интерактивность строки поиска (ActionSearchBar)
# ==============================================================================


def test_search_bar_interaction(qapp, qtbot):
    """
    Проверка интерактивности строки поиска ActionSearchBar:
    - Начальное состояние: пустое поле ввода, кнопка ✕ скрыта.
    - Ввод текста: генерация сигнала search_changed, кнопка ✕ становится видимой.
    - Клик по кнопке ✕: сброс поисковой строки, скрытие кнопки ✕, клавиатурный фокус возвращается в поле ввода.
    - Клик по кнопке вида ☰: генерация сигнала view_options_clicked.
    """
    search_bar = ActionSearchBar()
    search_bar.show()
    qtbot.addWidget(search_bar)

    assert search_bar.get_query() == ""
    assert not search_bar.btn_clear.isVisible()

    # 1. Ввод текста
    with qtbot.waitSignal(search_bar.search_changed, timeout=1000) as blocker:
        search_bar.search_input.setText("macro")
    assert blocker.args == ["macro"]
    assert search_bar.get_query() == "macro"
    assert search_bar.btn_clear.isVisible()

    # 2. Клик по кнопке очистки ✕
    qtbot.mouseClick(search_bar.btn_clear, Qt.LeftButton)
    assert search_bar.get_query() == ""
    assert not search_bar.btn_clear.isVisible()
    assert search_bar.search_input.hasFocus()

    # 3. Клик по кнопке опций вида ☰
    with qtbot.waitSignal(search_bar.view_options_clicked, timeout=1000):
        qtbot.mouseClick(search_bar.btn_view_options, Qt.LeftButton)


# ==============================================================================
# 3. Сворачивание и разворачивание секций аккордеона
# ==============================================================================


def test_action_accordion_collapse_expand(qapp, qtbot, action_catalog):
    """
    Проверка сворачивания и разворачивания секций аккордеона по клику на заголовок:
    - Все категории изначально свернуты (is_expanded=False, тело скрыто, шеврон '›').
    - Клик по заголовку первой категории (Multi Action):
      * Секция разворачивается (is_expanded=True, тело visible, шеврон '⌄').
      * Эмитируется сигнал expanded_changed("multi_action", True).
    - Повторный клик по заголовку:
      * Секция сворачивается (is_expanded=False, тело hidden, шеврон '›').
      * Эмитируется сигнал expanded_changed("multi_action", False).
    """
    accordion = ActionAccordionWidget()
    accordion.show()
    qtbot.addWidget(accordion)

    accordion.load_categories(action_catalog)
    assert len(accordion.sections) == 6

    # Проверка начального состояния всех секций
    for sec in accordion.sections:
        assert not sec.is_expanded
        assert not sec.body_widget.isVisible()
        assert sec.header.lbl_chevron.text() == "›"

    sec0 = accordion.sections[0]

    # Клик 1: Разворачивание секции
    with qtbot.waitSignal(sec0.expanded_changed, timeout=1000) as blocker:
        qtbot.mouseClick(sec0.header, Qt.LeftButton)
    assert blocker.args == [sec0.category_dto.id, True]
    assert sec0.is_expanded
    assert sec0.body_widget.isVisible()
    assert sec0.header.lbl_chevron.text() == "⌄"

    # Клик 2: Сворачивание секции
    with qtbot.waitSignal(sec0.expanded_changed, timeout=1000) as blocker:
        qtbot.mouseClick(sec0.header, Qt.LeftButton)
    assert blocker.args == [sec0.category_dto.id, False]
    assert not sec0.is_expanded
    assert not sec0.body_widget.isVisible()
    assert sec0.header.lbl_chevron.text() == "›"


# ==============================================================================
# 4. Двуязычный поиск и фильтрация (Bilingual Search)
# ==============================================================================


def test_action_search_bilingual(qapp, qtbot, action_catalog):
    """
    Тест двуязычной фильтрации каталога:
    - Поиск по-английски 'hotkey':
      * Категория System раскрыта, действие Hotkey отображается.
      * Остальные категории скрыты.
    - Поиск по-русски 'хоткей':
      * Категория System раскрыта, действие Hotkey отображается благодаря тегам keywords.
    - Поиск по слову 'папка' / 'folder':
      * Раскрыта категория Navigation с действием Create Folder.
    - Поиск несуществующего слова 'abracadabra':
      * Все категории скрыты, отображается локализованный плейсхолдер с подстановкой
        запроса из deck.editor.drawer.no_results.
    - Очистка поисковой строки:
      * Восстановление исходной видимости категорий (все категории видны, но свернуты).
    """
    drawer = ActionLibraryDrawer(categories=action_catalog)
    drawer.show()
    qtbot.addWidget(drawer)

    # 1. Поиск по-английски "hotkey"
    drawer.search_bar.search_input.setText("hotkey")
    system_sec = next(s for s in drawer.accordion.sections if s.category_dto.id == "system")
    assert system_sec.isVisible()
    assert system_sec.is_expanded
    assert system_sec.body_widget.isVisible()

    hotkey_w = next(w for w in system_sec.item_widgets if w.item_dto.id == "hotkey")
    assert hotkey_w.isVisible()
    # Другие категории скрыты
    other_sections = [s for s in drawer.accordion.sections if s.category_dto.id != "system"]
    assert all(not s.isVisible() for s in other_sections)
    assert not drawer.accordion.lbl_empty.isVisible()

    # 2. Поиск по-русски "хоткей"
    drawer.search_bar.search_input.setText("хоткей")
    assert system_sec.isVisible()
    assert system_sec.is_expanded
    assert hotkey_w.isVisible()
    assert all(not s.isVisible() for s in other_sections)
    assert not drawer.accordion.lbl_empty.isVisible()

    # 3. Поиск по слову "папка"
    drawer.search_bar.search_input.setText("папка")
    nav_sec = next(s for s in drawer.accordion.sections if s.category_dto.id == "navigation")
    assert nav_sec.isVisible()
    assert nav_sec.is_expanded
    folder_w = next(w for w in nav_sec.item_widgets if w.item_dto.id == "create_folder")
    assert folder_w.isVisible()

    # Поиск по слову "folder"
    drawer.search_bar.search_input.setText("folder")
    assert nav_sec.isVisible()
    assert nav_sec.is_expanded
    assert folder_w.isVisible()

    # 4. Поиск несуществующего слова "abracadabra"
    drawer.search_bar.search_input.setText("abracadabra")
    assert all(not s.isVisible() for s in drawer.accordion.sections)
    assert drawer.accordion.lbl_empty.isVisible()
    expected_empty_text = t("deck.editor.drawer.no_results", query="abracadabra")
    assert drawer.accordion.lbl_empty.text() == expected_empty_text

    # 5. Очистка поисковой строки
    drawer.search_bar.btn_clear.click()
    assert drawer.search_bar.get_query() == ""
    assert not drawer.accordion.lbl_empty.isVisible()
    # Все секции снова видны, но их тело свернуто в исходное состояние
    assert all(s.isVisible() for s in drawer.accordion.sections)
    assert all(not s.is_expanded for s in drawer.accordion.sections)


# ==============================================================================
# 5. Динамическая смена языка (retranslate_ui)
# ==============================================================================


def test_action_drawer_retranslate_ui(qapp, qtbot, action_catalog):
    """
    Тест динамической смены языка каталога (retranslate_ui):
    - Разворачиваем одну из секций (System).
    - Переключаем язык на RU:
      * Плейсхолдер строки поиска обновляется на русский.
      * Подсказка кнопки вида ☰ обновляется на русский.
      * Заголовки категорий и названия действий переводятся на русский.
      * Развернутая ветка System остается развернутой (is_expanded=True).
    - Переключаем язык на EN:
      * Все тексты возвращаются на английский.
      * Ветка System по-прежнему остается развернутой.
    - Проверка локализации пустого плейсхолдера при смене языка.
    """
    drawer = ActionLibraryDrawer(categories=action_catalog)
    drawer.show()
    qtbot.addWidget(drawer)

    system_sec = next(s for s in drawer.accordion.sections if s.category_dto.id == "system")
    system_sec.set_expanded(True)
    assert system_sec.is_expanded

    # 1. Переключение на RU
    I18nManager().set_language("ru", emit_signal=False)
    drawer.retranslate_ui()

    assert drawer.search_bar.search_input.placeholderText() == t(
        "deck.editor.drawer.search_placeholder"
    )
    assert drawer.search_bar.btn_view_options.toolTip() == t(
        "deck.editor.drawer.view_options_tooltip"
    )
    assert system_sec.header.lbl_title.text() == t("deck.editor.drawer.categories.system")
    hotkey_w = next(w for w in system_sec.item_widgets if w.item_dto.id == "hotkey")
    assert hotkey_w.lbl_title.text() == t("deck.editor.drawer.actions.hotkey")
    assert system_sec.is_expanded, "Expanded state must be preserved after retranslate_ui"

    # 2. Переключение на EN
    I18nManager().set_language("en", emit_signal=False)
    drawer.retranslate_ui()

    assert drawer.search_bar.search_input.placeholderText() == t(
        "deck.editor.drawer.search_placeholder"
    )
    assert drawer.search_bar.btn_view_options.toolTip() == t(
        "deck.editor.drawer.view_options_tooltip"
    )
    assert system_sec.header.lbl_title.text() == t("deck.editor.drawer.categories.system")
    assert hotkey_w.lbl_title.text() == t("deck.editor.drawer.actions.hotkey")
    assert system_sec.is_expanded, "Expanded state must be preserved after retranslate_ui"

    # 3. Проверка перевода плейсхолдера пустого поиска
    drawer.search_bar.search_input.setText("xyz_empty_query")
    assert drawer.accordion.lbl_empty.isVisible()
    assert drawer.accordion.lbl_empty.text() == t(
        "deck.editor.drawer.no_results", query="xyz_empty_query"
    )

    I18nManager().set_language("ru", emit_signal=False)
    drawer.retranslate_ui()
    assert drawer.accordion.lbl_empty.text() == t(
        "deck.editor.drawer.no_results", query="xyz_empty_query"
    )


# ==============================================================================
# 6. Эмиссия сигнала выбора действия (ActionItemDTO)
# ==============================================================================


def test_action_item_selection(qapp, qtbot, action_catalog):
    """
    Проверка выбора действия и цепочки сигналов:
    - Клик по ActionItemWidget эмитирует сигнал item_clicked(ActionItemDTO).
    - Сигнал каскадно передается через ActionAccordionWidget (action_selected)
      в ActionLibraryDrawer (action_picked).
    - Переданный объект в аргументе сигнала полностью совпадает с целевым ActionItemDTO.
    """
    drawer = ActionLibraryDrawer(categories=action_catalog)
    drawer.show()
    qtbot.addWidget(drawer)

    system_sec = next(s for s in drawer.accordion.sections if s.category_dto.id == "system")
    system_sec.set_expanded(True)
    hotkey_item = next(w for w in system_sec.item_widgets if w.item_dto.id == "hotkey")

    with qtbot.waitSignal(drawer.action_picked, timeout=1000) as blocker:
        qtbot.mouseClick(hotkey_item, Qt.LeftButton)

    picked_dto = blocker.args[0]
    assert isinstance(picked_dto, ActionItemDTO)
    assert picked_dto.id == "hotkey"
    assert picked_dto.icon == "⌨️"
    assert picked_dto.category_key == "deck.editor.drawer.categories.system"


# ==============================================================================
# 7. Интеграционный тест: назначение действия на слот холста в DeckEditorWindow
# ==============================================================================


def test_action_drawer_window_integration(qapp, qtbot):
    """
    Сквозной интеграционный тест взаимодействия ActionLibraryDrawer с холстом DeckCanvasWidget
    и инспектором KeyPropertyInspector внутри главного окна DeckEditorWindow:
    1. Открытие DeckEditorWindow.
    2. Выбор кнопки слота 0 на холсте (клик или select_button(0)).
    3. Поиск и клик по действию 'Website' (open_website) в ActionLibraryDrawer.
    4. Проверка назначения выбранного действия на слот 0:
       - Внутренний словарь _button_slots[0] обновлен (action_type, title, icon, category).
       - Превью ячейки на холсте (cell 0) обновлено (title, icon).
       - Форма инспектора свойств переключена в режим кнопки и отображает новое название и иконку.
    """
    window = DeckEditorWindow()
    window.show()
    qtbot.addWidget(window)

    # 1. Выделяем кнопку 0 на холсте
    window.canvas_widget.select_button(0)
    assert window.canvas_widget.get_selected_target() == ("button", 0)

    # 2. Находим действие Open Website в каталоге
    system_sec = next(
        s for s in window.action_drawer.accordion.sections if s.category_dto.id == "system"
    )
    system_sec.set_expanded(True)
    website_item = next(w for w in system_sec.item_widgets if w.item_dto.id == "open_website")

    # 3. Кликаем по карточке действия
    qtbot.mouseClick(website_item, Qt.LeftButton)

    # 4. Проверяем обновление DTO слота 0
    dto: ButtonSlotDTO = window._button_slots[0]
    assert dto.action_type == "open_website"
    assert dto.icon == "🌐"
    assert dto.title == website_item.item_dto.get_title()

    # 5. Проверяем ячейку на холсте
    cell0 = window.canvas_widget.get_cell(0)
    cell_data = cell0.get_button_data()
    assert cell_data["title"] == website_item.item_dto.get_title()
    assert cell_data["icon"] == "🌐"

    # 6. Проверяем инспектор свойств
    assert isinstance(window.inspector, KeyPropertyInspector)
    assert window.inspector.current_mode == "button"
    assert window.inspector.current_slot_index == 0
    assert window.inspector.button_form.edit_title.text() == website_item.item_dto.get_title()
    assert window.inspector.button_form.preview_tile.get_icon() == "🌐"

    window.close()
