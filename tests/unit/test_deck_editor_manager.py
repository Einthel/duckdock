"""
Unit tests for DeckEditorManager and Settings Button (⚙) integration.
Tests Sprint 2 Steps 2.1 - 2.2:
  - DeckEditorManager singleton lifecycle (open_editor, get_instance, close_editor).
  - Top-level OS window invariants (parent=None, Stealth Focus).
  - Window geometry (1080x740) and centering on primaryScreen.
  - Page selection routing (page_id forwarding).
  - Resource cleanup on close / destroyed signal.
  - Interactive panel settings button integration & ticker feedback.
  - Zero circular imports between modules.deck.editor and modules.deck.widgets.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from core.i18n import t
from modules.deck.editor.manager import DeckEditorManager
from modules.deck.editor.styles import WINDOW_DEFAULT_SIZE
from modules.deck.editor.window import DeckEditorWindow
from modules.deck.widgets.interactive_panel import (
    DeckInteractivePanel,
    DeckRightSection,
)


@pytest.fixture(autouse=True)
def cleanup_editor_manager(qapp: QApplication):
    """Ensure DeckEditorManager is cleanly closed before and after each test."""
    DeckEditorManager.close_editor()
    qapp.processEvents()
    yield
    DeckEditorManager.close_editor()
    qapp.processEvents()


def test_deck_editor_manager_singleton_lifecycle(qapp: QApplication):
    """DeckEditorManager returns a single DeckEditorWindow instance across repeated open calls."""
    assert DeckEditorManager.get_instance() is None

    win1 = DeckEditorManager.open_editor()
    assert isinstance(win1, DeckEditorWindow)
    assert DeckEditorManager.get_instance() is win1

    win2 = DeckEditorManager.open_editor()
    assert win2 is win1

    DeckEditorManager.close_editor()
    assert DeckEditorManager.get_instance() is None


def test_deck_editor_manager_top_level_parent_none(qapp: QApplication):
    """Stealth Focus invariant: editor window must be top-level (parent is None)."""
    parent_dummy = DeckInteractivePanel()
    try:
        # Even if a parent is passed, open_editor enforces independent top-level window
        win = DeckEditorManager.open_editor(parent=parent_dummy)
        assert win.parent() is None
        assert win.isWindow()
    finally:
        parent_dummy.cleanup()
        parent_dummy.deleteLater()


def test_deck_editor_manager_geometry_and_centering(qapp: QApplication):
    """Window geometry is set to 1080x740 and centered within primaryScreen."""
    win = DeckEditorManager.open_editor()
    screen = QGuiApplication.primaryScreen()

    assert win.width() == WINDOW_DEFAULT_SIZE[0]
    assert win.height() == WINDOW_DEFAULT_SIZE[1]

    if screen:
        avail_geo = screen.availableGeometry()
        expected_x = avail_geo.x() + (avail_geo.width() - WINDOW_DEFAULT_SIZE[0]) // 2
        expected_y = avail_geo.y() + (avail_geo.height() - WINDOW_DEFAULT_SIZE[1]) // 2
        # Учитываем толщину рамки и заголовка Windows (DWM frame decoration)
        assert abs(win.x() - expected_x) <= 40
        assert abs(win.y() - expected_y) <= 40


def test_deck_editor_manager_page_id_forwarding(qapp: QApplication):
    """Passing page_id in open_editor switches page in editor window."""
    win = DeckEditorManager.open_editor(page_id="page_2")
    assert win.pagination_bar.get_current_page() == 3

    DeckEditorManager.open_editor(page_id="page_0")
    assert win.pagination_bar.get_current_page() == 1


def test_deck_editor_manager_reopen_after_widget_destroyed(qapp: QApplication):
    """If window is destroyed externally, open_editor creates a new instance safely."""
    from PySide6.QtCore import QEvent
    win1 = DeckEditorManager.open_editor()
    win1.deleteLater()
    qapp.sendPostedEvents(None, int(QEvent.Type.DeferredDelete))
    qapp.processEvents()

    assert DeckEditorManager.get_instance() is None

    win2 = DeckEditorManager.open_editor()
    assert isinstance(win2, DeckEditorWindow)
    assert win2 is not win1


def test_interactive_panel_settings_button_triggers_editor_and_notification(qapp: QApplication):
    """Clicking ⚙ on DeckRightSection invokes manager and displays ticker notification."""
    panel = DeckInteractivePanel()
    try:
        panel.set_page_ids(["page_0", "page_1", "page_2"])
        panel.set_current_page(1, animated=False)

        # Ensure manager is closed initially
        DeckEditorManager.close_editor()
        assert DeckEditorManager.get_instance() is None

        # Click settings button ⚙
        panel.right_section.btn_settings.click()
        qapp.processEvents()

        # Window opened
        opened_win = DeckEditorManager.get_instance()
        assert opened_win is not None
        assert isinstance(opened_win, DeckEditorWindow)

        # Page forwarded (index 1 -> page_1 -> 2nd page)
        assert opened_win.pagination_bar.get_current_page() == 2

        # Ticker updated with opening message
        assert panel.right_section.lbl_ticker.text() == t("deck.interactive.opening_editor")
    finally:
        panel.cleanup()
        panel.deleteLater()


def test_no_circular_imports():
    """Verify that importing modules.deck.widgets does not import editor modules prematurely."""
    import sys

    # Check that modules.deck.widgets.interactive_panel does not statically import editor.manager
    import modules.deck.widgets.interactive_panel as ip
    assert "DeckEditorManager" not in ip.__dict__


# ==============================================================================
# Aliases and Explicit Step 5.1 Test Cases
# ==============================================================================


def test_manager_singleton_identity(qapp: QApplication):
    """Многократные вызовы get_instance / open_editor возвращают идентичный инстанс."""
    assert DeckEditorManager.get_instance() is None
    w1 = DeckEditorManager.open_editor()
    assert DeckEditorManager.get_instance() is w1
    w2 = DeckEditorManager.open_editor()
    assert w2 is w1
    DeckEditorManager.close_editor()
    assert DeckEditorManager.get_instance() is None


def test_manager_open_creates_window_on_primary_screen(qapp: QApplication):
    """Проверка создания окна 1080x740 и центрирования относительно экрана primaryScreen."""
    win = DeckEditorManager.open_editor()
    assert win.width() == 1080
    assert win.height() == 740
    screen = QGuiApplication.primaryScreen()
    if screen:
        avail = screen.availableGeometry()
        expected_x = avail.x() + (avail.width() - 1080) // 2
        expected_y = avail.y() + (avail.height() - 740) // 2
        assert abs(win.x() - expected_x) <= 40
        assert abs(win.y() - expected_y) <= 40


def test_manager_reopen_reactivates_existing_window(qapp: QApplication):
    """Повторный вызов open_editor() активирует существующее окно без создания второго."""
    win1 = DeckEditorManager.open_editor()
    win1.showMinimized()
    qapp.processEvents()

    win2 = DeckEditorManager.open_editor()
    assert win2 is win1
    assert not win2.isMinimized()


def test_manager_switch_page_on_open(qapp: QApplication):
    """Передача аргумента page_id переключает активную страницу в редакторе."""
    win = DeckEditorManager.open_editor(page_id="page_2")
    assert win.pagination_bar.get_current_page() == 3


def test_manager_close_cleans_reference(qapp: QApplication):
    """Закрытие окна корректно сбрасывает ссылку в менеджере."""
    DeckEditorManager.open_editor()
    assert DeckEditorManager.get_instance() is not None
    DeckEditorManager.close_editor()
    assert DeckEditorManager.get_instance() is None

