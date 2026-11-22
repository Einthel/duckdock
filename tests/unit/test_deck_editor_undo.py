"""
Модульные тесты архитектуры Undo/Redo и отслеживания состояния (Sprint 6.4, 6.5).
Проверяют:
  - AssignActionCommand: назначение действия, отмена и повтор.
  - ClearSlotCommand: очистка слота, отмена и повтор.
  - SwapButtonsCommand: обмен кнопок и копирование (Ctrl), отмена и повтор.
  - UpdatePropertyCommand: атомарное обновление свойств кнопки, отмена и повтор.
  - Dirty-state индикацию (звездочка '*' в заголовке окна) и сброс при сохранении.
  - Диалог подтверждения закрытия окна при наличии несохраненных изменений.
"""
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.deck.editor.commands import (
    AssignActionCommand,
    ClearSlotCommand,
    SwapButtonsCommand,
    UpdatePropertyCommand,
)
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.window import DeckEditorWindow


@pytest.fixture
def editor_win(qapp: QApplication, tmp_path):
    """Фикстура окна редактора с изолированным временным конфигом."""
    cfg_file = tmp_path / "deck_config.json"
    cfg_file.write_text('{"version": "2.0", "pages": [{"id": "page_1", "name": "Main", "buttons": []}]}', encoding="utf-8")

    initial_lang = I18nManager().current_language
    win = DeckEditorWindow(config_path=str(cfg_file))
    yield win
    win._is_dirty = False
    win._undo_stack.setClean()
    win.close()
    win.deleteLater()
    qapp.processEvents()
    I18nManager().set_language(initial_lang, emit_signal=False)


def test_assign_action_command(editor_win: DeckEditorWindow) -> None:
    """AssignActionCommand корректно применяет новое DTO, undo восстанавливает старое, redo накатывает."""
    old_dto = ButtonSlotDTO(slot_index=0, title="Empty")
    new_dto = ButtonSlotDTO(slot_index=0, title="Mute Mic", action_type="mic_mute_control", icon="🎙")

    editor_win.apply_slot_dto(0, old_dto)
    assert editor_win.get_slot_dto(0).title == "Empty"

    cmd = AssignActionCommand(editor_win, 0, new_dto, old_dto)
    editor_win._undo_stack.push(cmd)

    assert editor_win.get_slot_dto(0).title == "Mute Mic"
    assert editor_win.get_slot_dto(0).action_type == "mic_mute_control"

    # Undo
    editor_win._undo_stack.undo()
    assert editor_win.get_slot_dto(0).title == "Empty"

    # Redo
    editor_win._undo_stack.redo()
    assert editor_win.get_slot_dto(0).title == "Mute Mic"


def test_clear_slot_command(editor_win: DeckEditorWindow) -> None:
    """ClearSlotCommand сбрасывает данные слота, undo восстанавливает их полностью."""
    initial_dto = ButtonSlotDTO(slot_index=1, title="Browser", action_type="website", icon="🌐", color_accent="#38bdf8")
    editor_win.apply_slot_dto(1, initial_dto)

    cmd = ClearSlotCommand(editor_win, 1, initial_dto)
    editor_win._undo_stack.push(cmd)

    cleared = editor_win.get_slot_dto(1)
    assert cleared.title == ""
    assert cleared.action_type == ""

    # Undo
    editor_win._undo_stack.undo()
    restored = editor_win.get_slot_dto(1)
    assert restored.title == "Browser"
    assert restored.action_type == "website"
    assert restored.icon == "🌐"
    assert restored.color_accent == "#38bdf8"

    # Redo
    editor_win._undo_stack.redo()
    assert editor_win.get_slot_dto(1).title == ""


def test_swap_buttons_command_swap(editor_win: DeckEditorWindow) -> None:
    """SwapButtonsCommand (is_copy=False) меняет два слота местами."""
    dto0 = ButtonSlotDTO(slot_index=0, title="Button 0", action_type="system")
    dto1 = ButtonSlotDTO(slot_index=1, title="Button 1", action_type="hotkey")
    editor_win.apply_slot_dto(0, dto0)
    editor_win.apply_slot_dto(1, dto1)

    cmd = SwapButtonsCommand(editor_win, 0, 1, is_copy=False)
    editor_win._undo_stack.push(cmd)

    assert editor_win.get_slot_dto(0).title == "Button 1"
    assert editor_win.get_slot_dto(1).title == "Button 0"

    # Undo
    editor_win._undo_stack.undo()
    assert editor_win.get_slot_dto(0).title == "Button 0"
    assert editor_win.get_slot_dto(1).title == "Button 1"

    # Redo
    editor_win._undo_stack.redo()
    assert editor_win.get_slot_dto(0).title == "Button 1"
    assert editor_win.get_slot_dto(1).title == "Button 0"


def test_swap_buttons_command_copy(editor_win: DeckEditorWindow) -> None:
    """SwapButtonsCommand (is_copy=True) копирует исходный слот в целевой."""
    dto0 = ButtonSlotDTO(slot_index=0, title="Source Button", action_type="system", icon="⚙️")
    dto1 = ButtonSlotDTO(slot_index=1, title="Target Old", action_type="hotkey")
    editor_win.apply_slot_dto(0, dto0)
    editor_win.apply_slot_dto(1, dto1)

    cmd = SwapButtonsCommand(editor_win, 0, 1, is_copy=True)
    editor_win._undo_stack.push(cmd)

    # Исходный слот не изменился, целевой стал копией
    assert editor_win.get_slot_dto(0).title == "Source Button"
    assert editor_win.get_slot_dto(1).title == "Source Button"
    assert editor_win.get_slot_dto(1).icon == "⚙️"

    # Undo
    editor_win._undo_stack.undo()
    assert editor_win.get_slot_dto(0).title == "Source Button"
    assert editor_win.get_slot_dto(1).title == "Target Old"

    # Redo
    editor_win._undo_stack.redo()
    assert editor_win.get_slot_dto(1).title == "Source Button"


def test_update_property_command(editor_win: DeckEditorWindow) -> None:
    """UpdatePropertyCommand атомарно изменяет отдельное свойство кнопки."""
    dto = ButtonSlotDTO(slot_index=0, title="Initial Title", color_accent="#38bdf8")
    editor_win.apply_slot_dto(0, dto)

    cmd = UpdatePropertyCommand(editor_win, 0, "title", "Updated Title", "Initial Title")
    editor_win._undo_stack.push(cmd)
    assert editor_win.get_slot_dto(0).title == "Updated Title"

    editor_win._undo_stack.undo()
    assert editor_win.get_slot_dto(0).title == "Initial Title"

    editor_win._undo_stack.redo()
    assert editor_win.get_slot_dto(0).title == "Updated Title"


def test_dirty_state_indicator_and_save(editor_win: DeckEditorWindow) -> None:
    """Изменение состояния выставляет '*' в заголовке, save_configuration сбрасывает dirty state."""
    base_title = t("deck.editor.window.title")
    assert editor_win.windowTitle() == base_title
    assert editor_win._is_dirty is False

    # Добавляем команду
    cmd = UpdatePropertyCommand(editor_win, 0, "title", "Dirty Title", "Old Title")
    editor_win._undo_stack.push(cmd)

    assert editor_win._is_dirty is True
    assert editor_win.windowTitle() == f"{base_title} *"

    # Сохраняем
    saved = editor_win.save_configuration()
    assert saved is True
    assert editor_win._is_dirty is False
    assert editor_win.windowTitle() == base_title


def test_close_event_clean_window(editor_win: DeckEditorWindow) -> None:
    """При закрытии чистого окна событие принимается без всплытия диалога."""
    evt = QCloseEvent()
    editor_win.closeEvent(evt)
    assert evt.isAccepted() is True


def test_close_event_dirty_window_discard(editor_win: DeckEditorWindow) -> None:
    """При подтверждении Discard в диалоге закрытия окно закрывается."""
    cmd = UpdatePropertyCommand(editor_win, 0, "title", "Unsaved Title", "")
    editor_win._undo_stack.push(cmd)
    assert editor_win._is_dirty is True

    def fake_get_discard(box):
        for b in box.buttons():
            if box.buttonRole(b) == QMessageBox.DestructiveRole:
                return b
        return None

    with patch.object(QMessageBox, "exec", return_value=0), \
         patch.object(QMessageBox, "clickedButton", fake_get_discard):
        evt = QCloseEvent()
        editor_win.closeEvent(evt)
        assert evt.isAccepted() is True


def test_close_event_dirty_window_cancel(editor_win: DeckEditorWindow) -> None:
    """При нажатии Cancel в диалоге закрытия окно остается открытым."""
    cmd = UpdatePropertyCommand(editor_win, 0, "title", "Unsaved Title", "")
    editor_win._undo_stack.push(cmd)
    assert editor_win._is_dirty is True

    def fake_get_cancel(box):
        for b in box.buttons():
            if box.buttonRole(b) == QMessageBox.RejectRole:
                return b
        return None

    with patch.object(QMessageBox, "exec", return_value=0), \
         patch.object(QMessageBox, "clickedButton", fake_get_cancel):
        evt = QCloseEvent()
        editor_win.closeEvent(evt)
        assert evt.isAccepted() is False


def test_close_event_dirty_window_save(editor_win: DeckEditorWindow) -> None:
    """При нажатии Save в диалоге закрытия вызывается save_configuration и окно закрывается."""
    cmd = UpdatePropertyCommand(editor_win, 0, "title", "Unsaved Title", "")
    editor_win._undo_stack.push(cmd)
    assert editor_win._is_dirty is True

    def fake_get_save(box):
        for b in box.buttons():
            if box.buttonRole(b) == QMessageBox.AcceptRole:
                return b
        return None

    with patch.object(QMessageBox, "exec", return_value=0), \
         patch.object(QMessageBox, "clickedButton", fake_get_save), \
         patch.object(editor_win, "save_configuration", return_value=True) as mock_save:
        evt = QCloseEvent()
        editor_win.closeEvent(evt)
        assert mock_save.called
        assert evt.isAccepted() is True


def test_undo_stack_cleared_on_page_change(editor_win: DeckEditorWindow) -> None:
    """При переключении страницы стек отмены очищается (гигиена памяти)."""
    cmd = UpdatePropertyCommand(editor_win, 0, "title", "Page 1 Title", "")
    editor_win._undo_stack.push(cmd)
    assert editor_win._undo_stack.count() == 1
    assert editor_win._undo_stack.canUndo() is True

    # Переключаем на страницу 2
    editor_win._on_pagination_page_changed(2)

    assert editor_win._undo_stack.count() == 0
    assert editor_win._undo_stack.canUndo() is False
    assert editor_win._is_dirty is False


def test_undo_stack_cleared_on_remote_bus_sync(editor_win: DeckEditorWindow) -> None:
    """При удаленном переключении страницы со свитча (EventBus) стек отмены очищается."""
    cmd = UpdatePropertyCommand(editor_win, 0, "title", "Remote Sync Title", "")
    editor_win._undo_stack.push(cmd)
    assert editor_win._undo_stack.count() == 1
    assert editor_win._undo_stack.canUndo() is True

    # Имитируем удаленное переключение страницы
    editor_win._on_bus_deck_page_changed("page_1")

    assert editor_win._undo_stack.count() == 0
    assert editor_win._undo_stack.canUndo() is False
    assert editor_win._is_dirty is False


def test_undo_stack_cleared_on_page_clear(editor_win: DeckEditorWindow) -> None:
    """При контекстной очистке страницы стек отмены сбрасывается."""
    cmd = UpdatePropertyCommand(editor_win, 0, "title", "To Clear", "")
    editor_win._undo_stack.push(cmd)
    assert editor_win._undo_stack.count() == 1

    with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
        editor_win._on_pagination_clear_page_requested(1)

    assert editor_win._undo_stack.count() == 0
    assert editor_win._undo_stack.canUndo() is False
    assert editor_win._is_dirty is False

