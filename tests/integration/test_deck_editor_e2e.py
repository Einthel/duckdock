"""
Комплексный сквозной E2E интеграционный тест пользовательских сценариев и Hot Reload
конфигуратора DuckDeck (DeckEditorWindow) согласно шагу 6.4 из .md/deck/edit_but.md.

Сценарии:
  - Сценарий 1: Начальный плейсхолдер Рис. 1 и геометрия 70/30.
  - Сценарий 2: Клик по кнопке [0] -> подсветка и открытие формы Рис. 2.
  - Сценарий 3: Реактивное изменение Title в инспекторе -> живое превью на холсте.
  - Сценарий 4: Назначение действия из каталога на выделенный слот.
  - Сценарий 5: Переключение выделения на секцию тачбара -> открытие инспектора тачбара.
  - Сценарий 6: Сброс выделения по клику в пустоту холста и по клавише Esc.
  - Сценарий 7: Очистка слота кнопкой корзины 🗑️ с возвратом в плейсхолдер.
  - Сценарий 8: Горячее переключение языка Hot Reload:
                bus.language_changed.emit("ru") -> проверка перевода заголовка, тулбара,
                плейсхолдера, категорий;
                bus.language_changed.emit("en") -> возврат английских строк.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.deck.editor.demo_data import load_demo_profile_into_window
from modules.deck.editor.styles import (
    WINDOW_DEFAULT_SIZE,
    WINDOW_MIN_SIZE,
)
from modules.deck.editor.widgets.action_drawer import ActionLibraryDrawer
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.editor.widgets.header_bar import EditorHeaderBar
from modules.deck.editor.widgets.property_inspector import KeyPropertyInspector
from modules.deck.editor.window import DeckEditorWindow


@pytest.fixture(autouse=True)
def reset_i18n_language():
    """Гарантирует изоляцию локализации и возврат к исходному языку после теста."""
    initial_lang = I18nManager().current_language
    yield
    I18nManager().set_language(initial_lang, emit_signal=False)


@pytest.fixture
def e2e_window(qapp, qtbot):
    """
    Фикстура создания и инициализации главного окна DeckEditorWindow
    с эталонными демо-данными Рис. 1 для E2E сценариев.
    """
    # Гарантируем английский начальный язык для дефолтных строковых проверок
    I18nManager().set_language("en", emit_signal=False)

    window = DeckEditorWindow()
    load_demo_profile_into_window(window)
    window.show()
    qtbot.addWidget(window)
    qapp.processEvents()

    yield window

    window.close()
    window.deleteLater()
    qapp.processEvents()


# ==============================================================================
# Сквозной E2E пользовательский сценарий (Continuous User Journey)
# ==============================================================================


def test_deck_editor_e2e_full_journey(e2e_window, qtbot):
    """
    Полный сквозной пользовательский цикл (User Journey):
    Сценарии 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 в единой сессии взаимодействия.
    """
    window = e2e_window
    canvas = window.canvas_widget
    inspector = window.inspector
    drawer = window.action_drawer
    header = window.header_bar

    assert isinstance(canvas, DeckCanvasWidget)
    assert isinstance(inspector, KeyPropertyInspector)
    assert isinstance(drawer, ActionLibraryDrawer)
    assert isinstance(header, EditorHeaderBar)

    # --------------------------------------------------------------------------
    # Сценарий 1: Начальный плейсхолдер Рис. 1 и геометрия 70/30
    # --------------------------------------------------------------------------
    assert window.width() == WINDOW_DEFAULT_SIZE[0]
    assert window.height() == WINDOW_DEFAULT_SIZE[1]
    assert window.minimumSize().width() == WINDOW_MIN_SIZE[0]
    assert window.minimumSize().height() == WINDOW_MIN_SIZE[1]

    # Пропорции сплиттера 70/30 (левая колонка ~756, правая ~324)
    sizes = window.main_splitter.sizes()
    assert len(sizes) == 2
    total_w = sum(sizes)
    ratio_left = sizes[0] / total_w
    assert 0.68 <= ratio_left <= 0.72

    # Заполненные демо-кнопки по Рис. 1
    cell0 = canvas.get_cell(0)
    cell1 = canvas.get_cell(1)
    cell8 = canvas.get_cell(8)
    assert cell0 is not None and cell1 is not None and cell8 is not None

    assert cell0.get_button_data()["title"] == "Open Discord"
    assert cell0.get_button_data()["icon"] == "🖲️"
    assert cell1.get_button_data()["title"] == "Launch App"
    assert cell1.get_button_data()["icon"] == "🚀"
    assert cell8.get_button_data()["title"] == "Brightness"
    assert cell8.get_button_data()["icon"] == "☀️"

    # Пустые слоты
    for empty_idx in (2, 3, 4, 5, 6, 7, 9):
        c = canvas.get_cell(empty_idx)
        assert c is not None
        assert c.get_button_data()["title"] == ""
        assert c.get_button_data()["icon"] == ""

    # Отсутствие выделения на холсте и нейтральный плейсхолдер инспектора (Index 0)
    assert canvas.get_selected_target() is None
    assert inspector.stack.currentIndex() == 0
    assert inspector.current_mode == "placeholder"
    assert inspector.lbl_placeholder.text() == t("deck.editor.inspector.placeholder")

    # --------------------------------------------------------------------------
    # Сценарий 2: Клик по кнопке [0] -> подсветка и открытие формы Рис. 2
    # --------------------------------------------------------------------------
    qtbot.mouseClick(cell0, Qt.LeftButton)

    assert canvas.get_selected_target() == ("button", 0)
    assert cell0.is_selected() is True
    assert cell0.property("selected") == "true"

    # Инспектор переключился на форму кнопки (Index 1)
    assert inspector.stack.currentIndex() == 1
    assert inspector.current_slot_index == 0
    assert inspector.current_mode == "button"

    assert inspector.button_form.edit_title.text() == "Open Discord"
    assert inspector.button_form.get_category() == "System: Hotkey"
    assert inspector.button_form.btn_hotkey.get_hotkey() == "Ctrl+Shift+D"
    assert inspector.button_form.preview_tile.get_icon() == "🖲️"

    # --------------------------------------------------------------------------
    # Сценарий 3: Реактивное изменение Title в инспекторе -> живое превью на холсте
    # --------------------------------------------------------------------------
    inspector.button_form.edit_title.setText("Discord Mute")
    inspector.button_form.edit_title.textEdited.emit("Discord Mute")

    assert window._button_slots[0].title == "Discord Mute"
    assert cell0.get_button_data()["title"] == "Discord Mute"
    assert cell0.lbl_title.text() == "Discord Mute"
    assert inspector.button_form.edit_title.text() == "Discord Mute"

    # --------------------------------------------------------------------------
    # Сценарий 4: Назначение действия из каталога на выделенный слот
    # --------------------------------------------------------------------------
    # Находим категорию navigation в аккордеоне правой панели
    nav_section = next(
        s for s in drawer.accordion.sections if s.category_dto.id == "navigation"
    )
    nav_section.set_expanded(True)

    # Находим действие next_page ("Next Page", иконка ⏩)
    next_page_item = next(
        w for w in nav_section.item_widgets if w.item_dto.id == "next_page"
    )

    # Кликаем по действию в каталоге
    qtbot.mouseClick(next_page_item, Qt.LeftButton)

    expected_title = next_page_item.item_dto.get_title()
    expected_icon = next_page_item.item_dto.icon

    # Модель слота [0] окна обновилась
    assert window._button_slots[0].action_type == "next_page"
    assert window._button_slots[0].title == expected_title
    assert window._button_slots[0].icon == expected_icon

    # Превью на холсте обновилось
    assert cell0.lbl_title.text() == expected_title
    assert cell0.lbl_icon.text() == expected_icon

    # Инспектор свойств обновился
    assert inspector.button_form.edit_title.text() == expected_title
    assert inspector.button_form.preview_tile.get_icon() == expected_icon

    # --------------------------------------------------------------------------
    # Сценарий 5: Переключение выделения на секцию тачбара -> открытие инспектора тачбара
    # --------------------------------------------------------------------------
    sec_media = canvas.touchbar_strip.sec_media
    qtbot.mouseClick(sec_media, Qt.LeftButton)

    # Кнопка [0] снята с выделения, тачбар подсвечен
    assert cell0.is_selected() is False
    assert cell0.property("selected") == "false"
    assert sec_media.is_selected() is True
    assert canvas.touchbar_strip.get_selected_section() == "media"
    assert canvas.get_selected_target() == ("touchbar", "media")

    # Инспектор переключился на медиаплеер (Index 2)
    assert inspector.stack.currentIndex() == 2
    assert inspector.current_section_type == "media"
    assert inspector.current_mode == "touchbar"
    assert inspector.media_form.combo_player.currentText() == "YouTube Music"

    # --------------------------------------------------------------------------
    # Сценарий 6: Сброс выделения по клику в пустоту холста и по клавише Esc
    # --------------------------------------------------------------------------
    # Часть 1: Сброс по клавише Escape
    qtbot.keyClick(canvas, Qt.Key_Escape)

    assert sec_media.is_selected() is False
    assert canvas.get_selected_target() is None
    assert inspector.stack.currentIndex() == 0
    assert inspector.current_mode == "placeholder"

    # Часть 2: Повторный выбор кнопки и сброс кликом в нейтральную область холста
    qtbot.mouseClick(cell0, Qt.LeftButton)
    assert canvas.get_selected_target() == ("button", 0)
    assert inspector.stack.currentIndex() == 1

    # Клик в свободную область холста (точка 4, 4)
    qtbot.mouseClick(canvas, Qt.LeftButton, pos=QPoint(4, 4))

    assert cell0.is_selected() is False
    assert canvas.get_selected_target() is None
    assert inspector.stack.currentIndex() == 0
    assert inspector.current_mode == "placeholder"

    # --------------------------------------------------------------------------
    # Сценарий 7: Очистка слота кнопкой корзины 🗑️ с возвратом в плейсхолдер
    # --------------------------------------------------------------------------
    # Выбираем слот [1] ("Launch App", "🚀")
    qtbot.mouseClick(cell1, Qt.LeftButton)
    assert inspector.stack.currentIndex() == 1
    assert inspector.current_slot_index == 1
    assert inspector.button_form.edit_title.text() == "Launch App"

    # Кликаем по кнопке корзины 🗑️
    qtbot.mouseClick(inspector.button_form.btn_delete, Qt.LeftButton)

    # Слот очищен в модели, на холсте и выделение сброшено
    assert window._button_slots[1].title == ""
    assert window._button_slots[1].icon == ""
    assert cell1.lbl_title.text() == ""
    assert cell1.lbl_icon.text() == ""
    assert cell1.is_selected() is False
    assert canvas.get_selected_target() is None

    # Инспектор вернулся в плейсхолдер (Index 0)
    assert inspector.stack.currentIndex() == 0
    assert inspector.current_mode == "placeholder"

    # --------------------------------------------------------------------------
    # Сценарий 8: Горячее переключение языка Hot Reload (RU <-> EN)
    # --------------------------------------------------------------------------
    # 1. Переключение на русский язык
    bus.language_changed.emit("ru")

    # Заголовок окна на русском
    assert window.windowTitle() == t("deck.editor.window.title")
    assert window.windowTitle() == "Редактор кнопок и тачбара DuckDeck"

    # Плейсхолдер инспектора
    assert inspector.lbl_placeholder.text() == "Выберите кнопку для настройки действия."

    # Тулбар: селектор устройств и подсказки кнопок
    assert header.device_combo.currentText() == "DuckDeck Touch (2x5 + Strip)"
    assert header.btn_notifications.toolTip() == "Уведомления и лог макросов"
    assert header.btn_store.toolTip() == "Магазин расширений и иконок"
    assert header.btn_settings.toolTip() == "Настройки редактора DuckDeck"
    assert header.btn_account.toolTip() == "Профиль пользователя"

    # Категории аккордеона правой панели переведены
    sec_titles_ru = {s.category_dto.id: s.header.lbl_title.text() for s in drawer.accordion.sections}
    assert sec_titles_ru.get("navigation") == "Навигация"
    assert sec_titles_ru.get("system") == "Система"
    assert sec_titles_ru.get("multi_action") == "Мульти-действие"
    assert sec_titles_ru.get("soundboard") == "Саундборд"
    assert sec_titles_ru.get("volume_controller") == "Регулятор громкости"

    # Строка поиска
    assert drawer.search_bar.search_input.placeholderText() == "Поиск..."
    assert drawer.search_bar.btn_view_options.toolTip() == "Параметры отображения действий"

    # 2. Возврат на английский язык
    bus.language_changed.emit("en")

    # Заголовок окна на английском
    assert window.windowTitle() == "DuckDeck Button & Touchbar Editor"

    # Плейсхолдер инспектора
    assert inspector.lbl_placeholder.text() == "Select a key to configure its action."

    # Тулбар на английском
    assert header.btn_notifications.toolTip() == "Notifications & Macro Log"
    assert header.btn_settings.toolTip() == "DuckDeck Editor Settings"

    # Категории аккордеона на английском
    sec_titles_en = {s.category_dto.id: s.header.lbl_title.text() for s in drawer.accordion.sections}
    assert sec_titles_en.get("navigation") == "Navigation"
    assert sec_titles_en.get("system") == "System"
    assert sec_titles_en.get("multi_action") == "Multi Action"

    # Строка поиска на английском
    assert drawer.search_bar.search_input.placeholderText() == "Search..."


# ==============================================================================
# Изолированные тесты каждого отдельного сценария
# ==============================================================================


def test_scenario_1_initial_placeholder_and_geometry(e2e_window):
    """Сценарий 1: Начальный плейсхолдер Рис. 1 и геометрия 70/30."""
    window = e2e_window
    assert window.width() == 1080
    assert window.height() == 740

    sizes = window.main_splitter.sizes()
    assert len(sizes) == 2
    assert 0.68 <= sizes[0] / sum(sizes) <= 0.72

    canvas = window.canvas_widget
    assert canvas.get_cell(0).get_button_data()["title"] == "Open Discord"
    assert canvas.get_cell(1).get_button_data()["title"] == "Launch App"
    assert canvas.get_cell(8).get_button_data()["title"] == "Brightness"

    assert canvas.get_selected_target() is None
    assert window.inspector.stack.currentIndex() == 0
    assert window.inspector.current_mode == "placeholder"
    assert window.inspector.lbl_placeholder.text() == "Select a key to configure its action."


def test_scenario_2_click_button_opens_inspector(e2e_window, qtbot):
    """Сценарий 2: Клик по кнопке [0] -> подсветка и открытие формы Рис. 2."""
    window = e2e_window
    cell0 = window.canvas_widget.get_cell(0)

    qtbot.mouseClick(cell0, Qt.LeftButton)

    assert window.canvas_widget.get_selected_target() == ("button", 0)
    assert cell0.is_selected() is True

    inspector = window.inspector
    assert inspector.stack.currentIndex() == 1
    assert inspector.current_slot_index == 0
    assert inspector.current_mode == "button"
    assert inspector.button_form.edit_title.text() == "Open Discord"
    assert inspector.button_form.get_category() == "System: Hotkey"
    assert inspector.button_form.btn_hotkey.get_hotkey() == "Ctrl+Shift+D"
    assert inspector.button_form.preview_tile.get_icon() == "🖲️"


def test_scenario_3_reactive_title_editing(e2e_window, qtbot):
    """Сценарий 3: Реактивное изменение Title в инспекторе -> живое превью на холсте."""
    window = e2e_window
    cell0 = window.canvas_widget.get_cell(0)

    qtbot.mouseClick(cell0, Qt.LeftButton)

    window.inspector.button_form.edit_title.setText("Discord Mute")
    window.inspector.button_form.edit_title.textEdited.emit("Discord Mute")

    assert window._button_slots[0].title == "Discord Mute"
    assert cell0.get_button_data()["title"] == "Discord Mute"
    assert cell0.lbl_title.text() == "Discord Mute"


def test_scenario_4_assign_action_from_catalog(e2e_window, qtbot):
    """Сценарий 4: Назначение действия из каталога на выделенный слот."""
    window = e2e_window
    cell0 = window.canvas_widget.get_cell(0)

    qtbot.mouseClick(cell0, Qt.LeftButton)

    nav_section = next(
        s for s in window.action_drawer.accordion.sections if s.category_dto.id == "navigation"
    )
    nav_section.set_expanded(True)

    next_page_item = next(
        w for w in nav_section.item_widgets if w.item_dto.id == "next_page"
    )
    qtbot.mouseClick(next_page_item, Qt.LeftButton)

    assert window._button_slots[0].action_type == "next_page"
    assert cell0.lbl_title.text() == next_page_item.item_dto.get_title()
    assert cell0.lbl_icon.text() == next_page_item.item_dto.icon
    assert window.inspector.button_form.edit_title.text() == next_page_item.item_dto.get_title()


def test_scenario_5_switch_selection_to_touchbar(e2e_window, qtbot):
    """Сценарий 5: Переключение выделения на секцию тачбара -> открытие инспектора тачбара."""
    window = e2e_window
    cell0 = window.canvas_widget.get_cell(0)
    qtbot.mouseClick(cell0, Qt.LeftButton)
    assert cell0.is_selected() is True

    sec_media = window.canvas_widget.touchbar_strip.sec_media
    qtbot.mouseClick(sec_media, Qt.LeftButton)

    assert cell0.is_selected() is False
    assert sec_media.is_selected() is True
    assert window.canvas_widget.get_selected_target() == ("touchbar", "media")

    assert window.inspector.stack.currentIndex() == 2
    assert window.inspector.current_section_type == "media"
    assert window.inspector.current_mode == "touchbar"


def test_scenario_6_clear_selection_background_and_esc(e2e_window, qtbot):
    """Сценарий 6: Сброс выделения по клику в пустоту холста и по клавише Esc."""
    window = e2e_window
    canvas = window.canvas_widget
    sec_media = canvas.touchbar_strip.sec_media

    # Выделение тачбара -> Esc -> сброс
    qtbot.mouseClick(sec_media, Qt.LeftButton)
    assert canvas.get_selected_target() == ("touchbar", "media")

    qtbot.keyClick(canvas, Qt.Key_Escape)
    assert canvas.get_selected_target() is None
    assert window.inspector.stack.currentIndex() == 0

    # Выделение кнопки -> клик в нейтральную область холста -> сброс
    cell0 = canvas.get_cell(0)
    qtbot.mouseClick(cell0, Qt.LeftButton)
    assert canvas.get_selected_target() == ("button", 0)

    qtbot.mouseClick(canvas, Qt.LeftButton, pos=QPoint(4, 4))
    assert canvas.get_selected_target() is None
    assert window.inspector.stack.currentIndex() == 0


def test_scenario_7_clear_slot_with_trash_button(e2e_window, qtbot):
    """Сценарий 7: Очистка слота кнопкой корзины 🗑️ с возвратом в плейсхолдер."""
    window = e2e_window
    cell1 = window.canvas_widget.get_cell(1)

    qtbot.mouseClick(cell1, Qt.LeftButton)
    assert window.inspector.stack.currentIndex() == 1
    assert window.inspector.button_form.edit_title.text() == "Launch App"

    qtbot.mouseClick(window.inspector.button_form.btn_delete, Qt.LeftButton)

    assert window._button_slots[1].title == ""
    assert cell1.lbl_title.text() == ""
    assert cell1.is_selected() is False
    assert window.canvas_widget.get_selected_target() is None
    assert window.inspector.stack.currentIndex() == 0
    assert window.inspector.current_mode == "placeholder"


def test_scenario_8_hot_reload_language_switch(e2e_window):
    """
    Сценарий 8: Горячее переключение языка Hot Reload:
    bus.language_changed.emit("ru") -> проверка перевода заголовка, тулбара, плейсхолдера, категорий;
    bus.language_changed.emit("en") -> возврат английских строк.
    """
    window = e2e_window
    header = window.header_bar
    inspector = window.inspector
    drawer = window.action_drawer

    # 1. Переключение на русский
    bus.language_changed.emit("ru")

    assert window.windowTitle() == "Редактор кнопок и тачбара DuckDeck"
    assert inspector.lbl_placeholder.text() == "Выберите кнопку для настройки действия."
    assert header.btn_notifications.toolTip() == "Уведомления и лог макросов"
    assert header.btn_settings.toolTip() == "Настройки редактора DuckDeck"

    sec_titles_ru = {s.category_dto.id: s.header.lbl_title.text() for s in drawer.accordion.sections}
    assert sec_titles_ru.get("navigation") == "Навигация"
    assert sec_titles_ru.get("system") == "Система"

    # 2. Переключение на английский
    bus.language_changed.emit("en")

    assert window.windowTitle() == "DuckDeck Button & Touchbar Editor"
    assert inspector.lbl_placeholder.text() == "Select a key to configure its action."
    assert header.btn_notifications.toolTip() == "Notifications & Macro Log"
    assert header.btn_settings.toolTip() == "DuckDeck Editor Settings"

    sec_titles_en = {s.category_dto.id: s.header.lbl_title.text() for s in drawer.accordion.sections}
    assert sec_titles_en.get("navigation") == "Navigation"
    assert sec_titles_en.get("system") == "System"


def test_deck_editor_full_runtime_integration_journey(qapp, qtbot, tmp_path):
    """
    Сквозной интеграционный сценарий полного пути (E2E User Journey) согласно шагу 5.4:
      - Фаза A: Запуск DeckView на 7" в изоляции -> клик по ⚙ -> DeckEditorManager открывает DeckEditorWindow на 27";
                проверка сохранения Stealth Focus (Qt.NoFocus у DeckView).
      - Фаза B: Выбор слота [0] -> назначение действия 'website' -> ввод URL 'https://github.com' -> ввод названия 'GitHub'.
      - Фаза C: Открытие IconLibraryDialog -> выбор иконки -> выбор неонового цвета Cyan (#38bdf8).
      - Фаза D: Сохранение через Save -> атомарная запись .tmp -> .bak -> индикация "✓" -> эмит bus.deck_config_updated.
      - Фаза E: Прием сигнала в боевом DeckView -> in-place обновление слота [0] с новым названием 'GitHub', иконкой и цветом #38bdf8.
    """
    from modules.deck.view import DeckView
    from modules.deck.editor.manager import DeckEditorManager
    from modules.deck.editor.adapter import DeckConfigAdapter
    from modules.deck.models import DeckConfigLoader

    # 1. Подготовка изолированного конфига в tmp_path
    cfg_file = tmp_path / "deck_runtime_journey.json"
    root_cfg = DeckConfigLoader.get_default_config()
    DeckConfigAdapter.save_deck_config_atomic(root_cfg, str(cfg_file))

    # Фаза A: Инициализация DeckView на 7" экране
    view = DeckView(config_path=str(cfg_file))
    view.show()
    qtbot.addWidget(view)
    qapp.processEvents()

    try:
        # Проверка инварианта Stealth Focus (Qt.NoFocus)
        assert view.focusPolicy() == Qt.NoFocus

        # Клик по кнопке ⚙ в interactive_panel
        settings_btn = view.interactive_panel.right_section.btn_settings
        qtbot.mouseClick(settings_btn, Qt.LeftButton)
        qapp.processEvents()

        # DeckEditorManager открыл DeckEditorWindow
        editor_win = DeckEditorManager.get_instance()
        assert editor_win is not None
        assert editor_win.width() == 1080
        assert editor_win.height() == 740

        # Направляем редактор на изолированный файл и загружаем слоты
        editor_win.load_configuration(config_path=str(cfg_file), page_id="default")
        qapp.processEvents()

        # Фаза B: Выбор слота [0] и настройка действия Website
        cell0 = editor_win.canvas_widget.get_cell(0)
        assert cell0 is not None
        qtbot.mouseClick(cell0, Qt.LeftButton)
        qapp.processEvents()

        inspector = editor_win.inspector
        button_form = inspector.button_form
        assert inspector.stack.currentIndex() == 1  # форма кнопки

        # Выбираем website в комбобоксе
        idx_web = button_form.combo_actions.findData("website")
        assert idx_web >= 0
        button_form.combo_actions.setCurrentIndex(idx_web)
        qapp.processEvents()

        button_form.edit_title.setText("GitHub")
        button_form.edit_title.textEdited.emit("GitHub")
        button_form.subform_path_url.edit_input.setText("https://github.com")
        button_form.subform_path_url._on_text_edited("https://github.com")

        # Фаза C: Выбор иконки и цвета акцента
        button_form.preview_tile.set_icon("🌐")
        button_form.property_changed.emit("icon", "🌐")
        button_form.accent_picker._on_color_clicked("#38bdf8")
        qapp.processEvents()

        # Фаза D: Сохранение и Hot Reload
        save_btn = editor_win.header_bar.btn_save
        qtbot.mouseClick(save_btn, Qt.LeftButton)
        qapp.processEvents()

        assert "✓" in save_btn.text()

        # Фаза E: Реакция рантайма на тачскрине
        # DeckView получил сигнал bus.deck_config_updated и обновился in-place
        qapp.processEvents()

        btn0 = None
        for b in view.grid.get_buttons().values():
            if b.button_config.slot_index == 0:
                btn0 = b
                break
        assert btn0 is not None
        assert btn0.button_config.title == "GitHub"
        assert btn0.button_config.color_accent == "#38bdf8"
        assert view.focusPolicy() == Qt.NoFocus
    finally:
        DeckEditorManager.close_editor()
        view.cleanup()
        view.deleteLater()
        qapp.processEvents()

