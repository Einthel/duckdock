"""
Модульные тесты диалога библиотеки иконок (IconLibraryDialog) и превью-плитки (KeyPreviewTile).
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from modules.deck.editor.widgets.icon_library_dialog import (
    IconLibraryDialog,
    IconTileWidget,
)
from modules.deck.editor.widgets.key_preview_tile import KeyPreviewTile


@pytest.fixture(scope="session")
def qapp():
    """Единый экземпляр QApplication для тестов с GUI-объектами."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_icon_library_dialog_initialization(qapp):
    """Проверка создания диалога, геометрии 580x640 и атрибутов."""
    dialog = IconLibraryDialog(current_icon="🔊")
    assert dialog.width() == 580
    assert dialog.height() == 640
    assert dialog.isModal() is True
    assert dialog.objectName() == "iconLibraryDialog"
    assert dialog.get_selected_icon() == "🔊"
    dialog.close()


def test_icon_library_dialog_search_filter(qapp):
    """Проверка живого поиска по тексту."""
    dialog = IconLibraryDialog()

    initial_count = len(dialog._tile_widgets)
    assert initial_count > 0

    # Вводим строку поиска
    dialog.edit_search.setText("discord")
    assert len(dialog._tile_widgets) < initial_count
    assert any("discord" in t.entry.id.lower() for t in dialog._tile_widgets)

    # Очищаем строку поиска
    dialog.btn_clear_search.click()
    assert dialog.edit_search.text() == ""
    assert len(dialog._tile_widgets) == initial_count
    dialog.close()


def test_icon_library_dialog_category_switching(qapp):
    """Проверка переключения категорий через Pills."""
    dialog = IconLibraryDialog()

    assert "system" in dialog._pill_buttons
    dialog._pill_buttons["system"].click()
    assert dialog._active_category == "system"
    assert all(t.entry.category == "system" for t in dialog._tile_widgets)

    dialog._pill_buttons["media"].click()
    assert dialog._active_category == "media"
    assert all(t.entry.category == "media" for t in dialog._tile_widgets)
    dialog.close()


def test_icon_library_dialog_zoom(qapp):
    """Проверка переключения зума (36, 48, 60 px)."""
    dialog = IconLibraryDialog()

    dialog.btn_zoom_out.click()
    assert dialog._zoom_size == 36

    dialog.btn_zoom_in.click()
    assert dialog._zoom_size == 60

    dialog.btn_zoom_mid.click()
    assert dialog._zoom_size == 48
    dialog.close()


def test_icon_library_dialog_selection(qapp):
    """Проверка выбора тайла кликом и двойным кликом."""
    dialog = IconLibraryDialog()
    assert len(dialog._tile_widgets) > 0

    first_tile = dialog._tile_widgets[0]
    first_tile.clicked.emit(first_tile.entry)
    assert dialog.get_selected_icon() == first_tile.entry.path_or_glyph
    assert dialog.btn_select.isEnabled() is True

    # Двойной клик вызывает accept
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))
    first_tile.double_clicked.emit(first_tile.entry)
    assert len(accepted) == 1
    dialog.close()


def test_key_preview_tile_signals_and_menu(qapp):
    """Проверка сигналов плитки KeyPreviewTile."""
    tile = KeyPreviewTile()
    assert tile.get_icon() == "🖲️"

    # Смена иконки
    tile.set_icon("🚀")
    assert tile.get_icon() == "🚀"

    # Проверка вызова сигналов
    library_requested = []
    tile.open_library_requested.connect(lambda: library_requested.append(True))
    tile.btn_add.click()
    assert len(library_requested) == 1

    selected_icons = []
    tile.icon_selected.connect(lambda val: selected_icons.append(val))
    tile._reset_icon()
    assert tile.get_icon() == ""
    assert selected_icons == [""]


# Aliases & Step 5.2 Specific Tests
test_icon_dialog_initialization_and_modal_state = test_icon_library_dialog_initialization
test_icon_dialog_search_input_updates_grid = test_icon_library_dialog_search_filter
test_icon_dialog_zoom_slider = test_icon_library_dialog_zoom
test_icon_dialog_selection_and_signal = test_icon_library_dialog_selection


def test_icon_dialog_retranslate_ui(qapp):
    """Смена языка обновляет заголовок, плейсхолдер и кнопки диалога."""
    from core.i18n import I18nManager
    mgr = I18nManager()
    orig = mgr.current_language
    try:
        dialog = IconLibraryDialog()
        mgr.set_language("ru", emit_signal=False)
        dialog.retranslate_ui()
        assert dialog.windowTitle() == "Библиотека иконок DuckDeck"
        assert dialog.btn_select.text() == "Выбрать"

        mgr.set_language("en", emit_signal=False)
        dialog.retranslate_ui()
        assert dialog.windowTitle() == "DuckDeck Icon Library"
        assert dialog.btn_select.text() == "Select"
        dialog.close()
    finally:
        mgr.set_language(orig, emit_signal=False)

