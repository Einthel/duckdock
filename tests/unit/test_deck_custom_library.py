"""
Модульные и интеграционные тесты пользовательской библиотеки DuckDeck (Фаза 4):
- CustomLibraryStorage (CRUD вкладок и кнопок, атомарная запись, изоляция от системных пресетов, to_categories_dto).
- ActionCategoryDTO / ActionItemDTO (raw_title, is_custom, get_title() без вызова t()).
- ActionLibraryDrawer (кнопка + Вкладка, reload_library с сохранением состояния раскрытия и фильтра).
- ButtonPropertyForm (btnSaveToLibrary ⭐) и EditorGridCell (пункт контекстного меню).
- Полный Drag-and-Drop пользовательской кнопки на холст DeckEditorWindow с переносом всех параметров.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent

from core.i18n import I18nManager
from modules.deck.custom_library import CustomButtonPreset, CustomLibraryStorage
from modules.deck.editor.dto import ActionCategoryDTO, ActionItemDTO, ButtonSlotDTO
from modules.deck.editor.widgets.action_drawer import ActionLibraryDrawer
from modules.deck.editor.widgets.button_property_form import ButtonPropertyForm
from modules.deck.editor.widgets.grid_cell import EditorGridCell
from modules.deck.editor.window import DeckEditorWindow
from modules.deck.models import DeckActionConfig


@pytest.fixture(autouse=True)
def reset_i18n_language():
    initial_lang = I18nManager().current_language
    yield
    I18nManager().set_language(initial_lang, emit_signal=False)


# ==============================================================================
# 1. CustomLibraryStorage CRUD и атомарное сохранение
# ==============================================================================


def test_custom_library_storage_crud_tabs_and_items(tmp_path):
    lib_path = str(tmp_path / "deck_custom_library.json")
    storage = CustomLibraryStorage(lib_path)

    assert storage.list_tabs() == []
    assert storage.list_items() == []

    # Создание вкладок
    tab1 = storage.create_tab("Stream Tools", "🎮")
    tab2 = storage.create_tab("Work Macros", "💻")
    assert len(storage.list_tabs()) == 2
    assert tab1.title == "Stream Tools"
    assert tab1.icon == "🎮"

    # Переименование вкладки
    assert storage.rename_tab(tab1.id, "OBS Controls") is True
    assert storage.list_tabs()[0].title == "OBS Controls"
    assert storage.rename_tab("nonexistent", "X") is False

    # Добавление кнопки
    preset = CustomButtonPreset(
        id="",
        tab_id=tab1.id,
        title="Mute Mic",
        icon="🎙️",
        color_accent="#f43f5e",
        status_source="mic_mute",
        sound_override="muted",
        action=DeckActionConfig(
            action_type="audio",
            params={"target": "mic", "command": "toggle_mute"},
        ),
        keywords=["mic", "микрофон"],
    )
    saved = storage.add_item(tab1.id, preset)
    assert saved.id.startswith("custom_btn_")
    assert len(storage.list_items(tab1.id)) == 1

    # Переименование кнопки
    assert storage.rename_item(saved.id, "Toggle Mic") is True
    assert storage.get_item(saved.id).title == "Toggle Mic"

    # Персистентность на диск (атомарный JSON без .tmp хвостов)
    assert not (tmp_path / "deck_custom_library.json.tmp").exists()
    reloaded = CustomLibraryStorage(lib_path)
    assert len(reloaded.list_tabs()) == 2
    assert len(reloaded.list_items(tab1.id)) == 1
    assert reloaded.get_item(saved.id).color_accent == "#f43f5e"
    assert reloaded.get_item(saved.id).status_source == "mic_mute"
    assert reloaded.get_item(saved.id).sound_override == "muted"

    # Конвертация в DTO
    cats = reloaded.to_categories_dto()
    assert len(cats) == 2
    assert cats[0].is_custom is True
    assert cats[0].raw_title == "OBS Controls"
    assert cats[0].get_title() == "OBS Controls"
    assert len(cats[0].items) == 1
    assert cats[0].items[0].is_custom is True
    assert cats[0].items[0].get_title() == "Toggle Mic"

    # Удаление кнопки
    assert reloaded.delete_item(saved.id) is True
    assert reloaded.list_items(tab1.id) == []

    # Удаление вкладки (вместе с её кнопками)
    reloaded.add_item(tab2.id, preset.model_copy(update={"id": "", "tab_id": tab2.id}))
    assert len(reloaded.list_items(tab2.id)) == 1
    assert reloaded.delete_tab(tab2.id) is True
    assert len(reloaded.list_tabs()) == 1
    assert reloaded.list_items(tab2.id) == []


def test_custom_dto_get_title_bypasses_i18n():
    cat = ActionCategoryDTO(
        id="custom_tab_1",
        title_key="",
        raw_title="My Custom Tab",
        is_custom=True,
    )
    item = ActionItemDTO(
        id="custom_btn_1",
        title_key="",
        category_key="",
        icon="⭐",
        raw_title="Custom Action",
        is_custom=True,
    )
    assert cat.get_title() == "My Custom Tab"
    assert item.get_title() == "Custom Action"


# ==============================================================================
# 2. UI-элементы: ActionLibraryDrawer, ButtonPropertyForm, EditorGridCell
# ==============================================================================


def test_action_drawer_reload_preserves_state_and_custom_tabs(qapp, qtbot, tmp_path):
    lib_path = str(tmp_path / "custom.json")
    storage = CustomLibraryStorage(lib_path)
    tab = storage.create_tab("Streaming", "🎮")
    storage.add_item(
        tab.id,
        CustomButtonPreset(
            id="c_1",
            tab_id=tab.id,
            title="Scene 1",
            icon="🎬",
            action=DeckActionConfig(action_type="hotkey", params={"keys": ["f13"]}),
        ),
    )

    drawer = ActionLibraryDrawer(custom_storage=storage)
    drawer.show()
    qtbot.addWidget(drawer)

    assert drawer.btn_add_tab.focusPolicy() == Qt.NoFocus
    assert len(drawer.accordion.sections) == 8  # 1 custom + 7 system

    custom_sec = drawer.accordion.sections[0]
    assert custom_sec.category_dto.id == tab.id
    assert custom_sec.category_dto.is_custom is True
    assert "Streaming" in custom_sec.header.lbl_title.text()

    # Раскрываем секцию и задаем поиск, затем перезагружаем библиотеку
    custom_sec.set_expanded(True)
    drawer.search_bar.search_input.setText("Scene")
    drawer.reload_library()

    assert drawer.accordion.sections[0].is_expanded is True
    assert drawer.accordion.sections[0].item_widgets[0].isVisible() is True


def test_button_property_form_and_cell_save_to_library_controls(qapp, qtbot):
    form = ButtonPropertyForm()
    qtbot.addWidget(form)

    assert form.btn_save_to_library.objectName() == "btnSaveToLibrary"
    assert form.btn_save_to_library.focusPolicy() == Qt.NoFocus

    # Для пустого слота кнопка ⭐ отключена
    form.load_slot_data(ButtonSlotDTO(slot_index=0, title="", action_type="", hotkey=""))
    assert form.btn_save_to_library.isEnabled() is False

    # Для настроенного слота кнопка ⭐ активна и эмитит сигнал
    form.load_slot_data(ButtonSlotDTO(slot_index=0, title="Build", action_type="hotkey", hotkey="ctrl+b"))
    assert form.btn_save_to_library.isEnabled() is True
    with qtbot.waitSignal(form.save_to_library_requested, timeout=1000):
        qtbot.mouseClick(form.btn_save_to_library, Qt.LeftButton)

    # Контекстное меню ячейки содержит пункт сохранения в библиотеку
    cell = EditorGridCell(slot_index=2)
    qtbot.addWidget(cell)
    cell.set_button_data(title="Build", icon="🔨", hotkey="Ctrl+B")
    menu = cell.show_context_menu()
    texts = [act.text() for act in menu.actions()]
    assert any("⭐" in txt for txt in texts)


# ==============================================================================
# 3. Полный Drag-and-Drop кастомной кнопки на холст DeckEditorWindow
# ==============================================================================


def test_custom_button_drag_and_drop_restores_all_attributes(qapp, qtbot, tmp_path):
    cfg_path = str(tmp_path / "deck_config.json")
    lib_path = str(tmp_path / "deck_custom_library.json")

    win = DeckEditorWindow(config_path=cfg_path, custom_library_path=lib_path)
    qtbot.addWidget(win)

    tab = win.custom_library.create_tab("My Macros", "⭐")
    saved = win.custom_library.add_item(
        tab.id,
        CustomButtonPreset(
            id="custom_btn_test",
            tab_id=tab.id,
            title="Discord Mute",
            icon="🔇",
            color_accent="#10b981",
            status_source="mic_mute",
            sound_override="muted",
            action=DeckActionConfig(
                action_type="hotkey",
                params={"mode": "toggle", "keys": ["ctrl", "shift", "m"], "toggle_keys": ["ctrl", "shift", "u"]},
            ),
            keywords=["discord", "mute"],
        ),
    )
    win.action_drawer.reload_library()

    # Симулируем MIME-payload из ActionItemWidget.mouseMoveEvent
    payload = {
        "id": saved.id,
        "title": saved.title,
        "icon": saved.icon,
        "category": "",
        "category_id": tab.id,
        "keywords": saved.keywords,
        "is_custom": True,
        "color_accent": saved.color_accent,
        "status_source": saved.status_source,
        "sound_override": saved.sound_override,
        "default_config": {
            "id": saved.id,
            "title": saved.title,
            "icon": saved.icon,
            "color_accent": saved.color_accent,
            "status_source": saved.status_source,
            "sound_override": saved.sound_override,
            "action": saved.action.model_dump(exclude_none=True),
        },
    }
    mime = QMimeData()
    mime.setData("application/x-duckdeck-action", json.dumps(payload).encode("utf-8"))

    target_cell = win.canvas_widget.cells[3]
    drop_event = QDropEvent(
        QPointF(10, 10),
        Qt.CopyAction,
        mime,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    target_cell.dropEvent(drop_event)

    dto = win.get_slot_dto(3)
    assert dto.title == "Discord Mute"
    assert dto.icon == "🔇"
    assert dto.color_accent == "#10b981"
    assert dto.status_source == "mic_mute"
    assert dto.sound_override == "muted"
    assert dto.action_type == "hotkey"
    assert dto.action_params["mode"] == "toggle"
    assert dto.action_params["keys"] == ["ctrl", "shift", "m"]
    assert dto.action_params["toggle_keys"] == ["ctrl", "shift", "u"]


def test_save_loaded_launch_button_preserves_action_and_params(qapp, qtbot, tmp_path):
    """
    Регрессионный тест: кнопка, загруженная через DeckConfigAdapter.slot_to_dto
    (где dto.action_type == 'Open Application'), при сохранении в библиотеку
    и перетаскивании на новый слот обязана сохранить action_type='launch' и target.
    """
    from PySide6.QtWidgets import QDialog

    cfg_path = str(tmp_path / "deck_config.json")
    lib_path = str(tmp_path / "deck_custom_library.json")

    win = DeckEditorWindow(config_path=cfg_path, custom_library_path=lib_path)
    qtbot.addWidget(win)

    tab = win.custom_library.create_tab("Apps", "💻")

    # Имитируем слот 0, загруженный из конфига (action_type='Open Application')
    loaded_dto = ButtonSlotDTO(
        slot_index=0,
        title="sec",
        icon="resources/deck/icons/deck/images.png",
        category="System: Open Application",
        action_type="Open Application",
        action_params={"kind": "app", "target": "C:/Program Files/SecureCRT/SecureCRT.exe"},
    )
    win.apply_slot_dto(0, loaded_dto)

    with patch("modules.deck.editor.widgets.custom_library_dialogs.SaveToLibraryDialog.exec", return_value=QDialog.Accepted), \
         patch("modules.deck.editor.widgets.custom_library_dialogs.SaveToLibraryDialog.get_button_title", return_value="sec"), \
         patch("modules.deck.editor.widgets.custom_library_dialogs.SaveToLibraryDialog.get_selected_tab_id", return_value=tab.id):
        win._on_save_slot_to_library_requested(0)

    items = win.custom_library.list_items(tab.id)
    assert len(items) == 1
    saved = items[0]
    assert saved.action.action_type == "launch"
    assert saved.action.params["kind"] == "app"
    assert saved.action.params["target"] == "C:/Program Files/SecureCRT/SecureCRT.exe"

    # Перетаскиваем сохранённую кнопку на слот 4
    payload = {
        "id": saved.id,
        "title": saved.title,
        "icon": saved.icon,
        "is_custom": True,
        "default_config": {
            "id": saved.id,
            "title": saved.title,
            "icon": saved.icon,
            "color_accent": saved.color_accent,
            "action": saved.action.model_dump(exclude_none=True),
        },
    }
    mime = QMimeData()
    mime.setData("application/x-duckdeck-action", json.dumps(payload).encode("utf-8"))
    drop_event = QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    win.canvas_widget.cells[4].dropEvent(drop_event)

    restored = win.get_slot_dto(4)
    assert restored.title == "sec"
    assert restored.action_type == "launch"
    assert restored.action_params["kind"] == "app"
    assert restored.action_params["target"] == "C:/Program Files/SecureCRT/SecureCRT.exe"
