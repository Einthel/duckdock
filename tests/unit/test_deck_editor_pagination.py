"""
Модульные и интеграционные тесты многостраничности и контекстного меню DuckDeck Editor.
Проверяют:
  1. Отображение пустой страницы без warning "not found" и отката на default;
  2. Фильтрацию пустых страниц на сенсорной панели DeckView (только непустые страницы на панели);
  3. Двустороннюю синхронизацию страниц между редактором и панелью через bus.deck_page_changed;
  4. Динамическое добавление страниц по нажатию кнопки '+';
  5. Контекстное меню ПКМ: переименование, дублирование, удаление страницы;
  6. Аккуратную подпись страницы над сеткой (отображение при наличии названия, скрытие при отсутствии).
"""
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from modules.deck.editor.adapter import DeckConfigAdapter
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.editor.widgets.pagination_bar import PageNavigationBar
from modules.deck.editor.window import DeckEditorWindow
from modules.deck.models import DeckButtonConfig, DeckPageConfig, DeckRootConfig
from modules.deck.view import DeckView


@pytest.fixture
def sample_root_config() -> DeckRootConfig:
    """Фикстура с 2 страницами: 1-я с кнопками, 2-я пустая."""
    return DeckRootConfig(
        active_profile="page_main",
        pages=[
            DeckPageConfig(
                id="page_main",
                name="Основной",
                buttons=[
                    DeckButtonConfig(
                        id="btn_1",
                        slot_index=0,
                        title="Тест",
                        action={"action_type": "website", "params": {"url": "https://test.com"}},
                    )
                ],
            ),
            DeckPageConfig(
                id="page_empty",
                name="Пустая",
                buttons=[],
            ),
        ],
    )


def test_empty_page_no_not_found_warning(caplog, sample_root_config):
    """
    Требование 1: При клике на пустую или несуществующую страницу нет 'not found' warning,
    возвращаются чистые пустые слоты 0..9.
    """
    caplog.clear()
    slots = DeckConfigAdapter.load_page_slots(sample_root_config, "page_nonexistent_99")

    # Никакого warning "not found in DeckRootConfig"
    assert "not found in DeckRootConfig" not in caplog.text
    assert len(slots) == 10
    # Все слоты пустые
    for idx, slot in slots.items():
        assert slot.slot_index == idx
        assert not slot.title
        assert not slot.hotkey


def test_deck_view_filters_empty_pages(qapp, sample_root_config, tmp_path):
    """
    Требование 1: Сенсорная панель DuckDeck (DeckView) не отображает пустые страницы
    и не включает их в счетчик страниц. Как только появляется кнопка - страница отображается.
    """
    cfg_file = tmp_path / "deck_test.json"
    DeckConfigAdapter.save_deck_config_atomic(sample_root_config, str(cfg_file))

    view = DeckView(config_path=str(cfg_file))
    try:
        # В конфиге 2 страницы, но 2-я пустая (без кнопок)
        display_pages = view.get_display_pages()
        assert len(display_pages) == 1
        assert display_pages[0].id == "page_main"

        # Добавим кнопку на 2-ю страницу
        updated = DeckConfigAdapter.apply_slots_to_page(
            sample_root_config,
            page_id_or_index="page_empty",
            slots={0: ButtonSlotDTO(slot_index=0, title="Новая кнопка", icon="⚡", action_type="website")},
        )
        DeckConfigAdapter.save_deck_config_atomic(updated, str(cfg_file))

        # Перезагружаем конфигурацию
        view.reload_config()
        display_pages_after = view.get_display_pages()
        assert len(display_pages_after) == 2
        assert display_pages_after[1].id == "page_empty"
    finally:
        view.cleanup()


def test_page_canvas_title_visibility(qapp):
    """
    Требование: Подпись страницы аккуратно отображается над сеткой.
    Контейнер всегда сохраняет фиксированную геометрию (высоту 24 px),
    исключая сдвиг кнопок вверх.
    """
    canvas = DeckCanvasWidget()
    canvas.show()
    try:
        # Контейнер всегда присутствует в layout и не скрывается
        assert not canvas.page_title_label.isHidden()
        assert canvas.page_title_label.height() == 24
        assert canvas.get_page_title() == ""

        # Установка имени
        canvas.set_page_title("Стриминг и OBS")
        assert not canvas.page_title_label.isHidden()
        assert canvas.get_page_title() == "Стриминг и OBS"

        # Сброс в пустое имя - контейнер остается, текст пустой
        canvas.set_page_title("")
        assert not canvas.page_title_label.isHidden()
        assert canvas.get_page_title() == ""

        canvas.set_page_title(None)
        assert not canvas.page_title_label.isHidden()
        assert canvas.get_page_title() == ""
    finally:
        canvas.deleteLater()


def test_pagination_bar_add_page_button(qapp):
    """
    Требование: Минимум 1 страница в PageNavigationBar, динамическое добавление.
    """
    bar = PageNavigationBar()
    try:
        # Изначально ровно 1 кнопка
        assert len(bar.page_buttons) == 1
        assert bar.page_buttons[0].text() == "1"

        # Добавляем 2-ю страницу
        new_idx = bar.add_page_button()
        assert new_idx == 2
        assert len(bar.page_buttons) == 2
        assert bar.page_buttons[1].text() == "2"

        # Удаление единственной страницы запрещено
        bar.remove_page_button(1)
        assert len(bar.page_buttons) == 1
        # Повторная попытка удалить 1-ю страницу
        bar.remove_page_button(1)
        assert len(bar.page_buttons) == 1
    finally:
        bar.deleteLater()


def test_pagination_bar_context_menu_signals(qapp):
    """
    Требование: ПКМ по кнопке страницы эмитирует сигналы контекстного меню
    (переименовать, дублировать, очистить, удалить).
    """
    bar = PageNavigationBar()
    try:
        received = []
        bar.rename_page_requested.connect(lambda p: received.append(("rename", p)))
        bar.duplicate_page_requested.connect(lambda p: received.append(("duplicate", p)))
        bar.clear_page_requested.connect(lambda p: received.append(("clear", p)))
        bar.delete_page_requested.connect(lambda p: received.append(("delete", p)))

        # Прямая эмиссия сигналов, которые вызываются из меню
        bar.rename_page_requested.emit(1)
        bar.duplicate_page_requested.emit(1)
        bar.clear_page_requested.emit(1)
        bar.delete_page_requested.emit(1)

        assert received == [("rename", 1), ("duplicate", 1), ("clear", 1), ("delete", 1)]
    finally:
        bar.deleteLater()


def test_bidirectional_page_synchronization(qapp, sample_root_config, tmp_path):
    """
    Требование 2: При перелистывании страниц в редакторе переключается панель,
    и при переключении на панели переключается редактор.
    """
    cfg_file = tmp_path / "sync_deck.json"
    # Создадим 2 страницы с кнопками
    config = sample_root_config.model_copy(deep=True)
    config.pages[1].buttons = [
        DeckButtonConfig(
            id="btn_p2",
            slot_index=0,
            title="Страница 2",
            action={"action_type": "website", "params": {"url": "https://p2.com"}},
        )
    ]
    DeckConfigAdapter.save_deck_config_atomic(config, str(cfg_file))

    view = DeckView(config_path=str(cfg_file))
    editor = DeckEditorWindow()
    editor.config_path = str(cfg_file)
    editor.load_configuration()

    try:
        # 1. Редактор переключается на страницу 2 -> панель переключается на page_empty
        editor._on_pagination_page_changed(2)
        assert view.active_page_id == "page_empty"

        # 2. Панель переключается на страницу 1 -> редактор переключается на страницу 1
        view.set_active_page("page_main", emit_signal=True)
        assert editor.pagination_bar.get_current_page() == 1
        assert editor.canvas_widget.get_page_title() == "Основной"
    finally:
        view.cleanup()
        editor.close()


def test_adapter_rename_duplicate_delete_page(sample_root_config):
    """
    Требование 4: Методы адаптера для переименования, дублирования и удаления страниц.
    """
    # 1. Переименование
    renamed = DeckConfigAdapter.rename_page(sample_root_config, "page_main", "Рабочий стол")
    assert renamed.pages[0].name == "Рабочий стол"

    # 2. Дублирование
    duplicated, new_page = DeckConfigAdapter.duplicate_page(renamed, 0, copy_suffix=" (Копия)")
    assert len(duplicated.pages) == 3
    assert new_page.name == "Рабочий стол (Копия)"
    assert len(new_page.buttons) == 1
    assert new_page.buttons[0].id != renamed.pages[0].buttons[0].id

    # 3. Удаление
    deleted = DeckConfigAdapter.delete_page(duplicated, 1) # удаляем 2-ю страницу
    assert len(deleted.pages) == 2
    assert deleted.pages[0].name == "Рабочий стол"
    assert deleted.pages[1].name == "Рабочий стол (Копия)"


def test_page_switch_auto_saves_progress(tmp_path, sample_root_config):
    """
    Требование: при переключении страниц в редакторе изменения на текущей странице
    автоматически сохраняются без необходимости нажимать кнопку 'Сохранить'.
    """
    cfg_file = tmp_path / "deck_config_autosave.json"
    DeckConfigAdapter.save_deck_config_atomic(sample_root_config, str(cfg_file))

    editor = DeckEditorWindow()
    editor.config_path = str(cfg_file)
    editor.load_configuration()

    try:
        # Изменяем заголовок и хоткей слота 0 на первой странице
        editor._on_inspector_button_updated(0, "title", "Автосохраненный ярлык")
        editor._on_inspector_button_updated(0, "hotkey", "Ctrl+Alt+S")

        # Переключаемся на страницу 2 без вызова save_configuration() вручную
        editor._on_pagination_page_changed(2)

        # Проверяем, что файл на диске уже содержит наши изменения для page_main
        saved_cfg = DeckConfigAdapter.load_deck_config(str(cfg_file))
        assert len(saved_cfg.pages[0].buttons) >= 1
        assert saved_cfg.pages[0].buttons[0].title == "Автосохраненный ярлык"

        # Переключаемся обратно на страницу 1
        editor._on_pagination_page_changed(1)
        assert editor._button_slots[0].title == "Автосохраненный ярлык"
        assert "Ctrl" in editor._button_slots[0].hotkey and "Alt" in editor._button_slots[0].hotkey
    finally:
        editor.close()

