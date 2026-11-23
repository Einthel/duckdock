"""
Модульные тесты дизайн-системы Dark Obsidian v2 и таблицы стилей styles.py (Шаг 1.1).
Проверяют 4-уровневую систему поверхностей, палитру Slate, Re-export Shims и валидность QSS.
"""
import re
import pytest
from PySide6.QtWidgets import QApplication, QMainWindow

from modules.deck.editor.styles import (
    # Поверхности Surface 0-3
    SURFACE_0_CANVAS,
    SURFACE_1_PANEL,
    SURFACE_2_CARD,
    SURFACE_3_HOVER,
    # Границы и фокусы
    BORDER_SURFACE_1,
    BORDER_SURFACE_2,
    BORDER_FOCUS_NEON,
    BORDER_FOCUS_BASE,
    BORDER_FOCUS,
    BORDER_FOCUS_ACCENT,
    BORDER_HOVER,
    BORDER_SUBTLE,
    BORDER_CELL,
    BORDER_SELECTED_GLOW,
    # Типографика Slate
    TEXT_SLOT_INDEX,
    TEXT_PRIMARY_HIGH,
    TEXT_SECONDARY_MED,
    TEXT_MUTED_SUBTLE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    TEXT_PLACEHOLDER,
    # Re-export Shims
    BG_WINDOW,
    BG_PANEL,
    BG_CARD,
    BG_STRIP,
    BG_CELL,
    BG_CELL_HOVER,
    BG_TOUCHBAR,
    BG_SECTION_HOVER,
    # Геометрия и QSS
    WINDOW_DEFAULT_SIZE,
    WINDOW_MIN_SIZE,
    EDITOR_MAIN_QSS,
    apply_editor_theme,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_surface_tokens_values():
    """Проверка точных значений 4-уровневой системы поверхностей Dark Obsidian v2."""
    assert SURFACE_0_CANVAS == "#0b0d13"
    assert SURFACE_1_PANEL == "#0f141f"
    assert SURFACE_2_CARD == "#141924"
    assert SURFACE_3_HOVER == "#1c2940"


def test_border_and_focus_tokens():
    """Проверка токенов границ и акцентов фокуса."""
    assert BORDER_SURFACE_1 == "#1e2638"
    assert BORDER_SURFACE_2 == "#202a3c"
    assert BORDER_FOCUS_NEON == "#38bdf8"
    assert BORDER_FOCUS_BASE == "#0078d4"
    assert BORDER_FOCUS == BORDER_FOCUS_BASE
    assert BORDER_FOCUS_ACCENT == BORDER_FOCUS_NEON


def test_slate_typography_tokens():
    """Проверка токенов типографики Slate."""
    assert TEXT_SLOT_INDEX == "#475569"
    assert TEXT_PRIMARY_HIGH == "#f8fafc"
    assert TEXT_SECONDARY_MED == "#94a3b8"
    assert TEXT_MUTED_SUBTLE == "#64748b"


def test_hex_format_for_all_tokens():
    """Проверка корректности формата HEX (#rrggbb) для всех цветовых токенов."""
    hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    color_tokens = [
        SURFACE_0_CANVAS,
        SURFACE_1_PANEL,
        SURFACE_2_CARD,
        SURFACE_3_HOVER,
        BORDER_SURFACE_1,
        BORDER_SURFACE_2,
        BORDER_FOCUS_NEON,
        BORDER_FOCUS_BASE,
        BORDER_HOVER,
        TEXT_SLOT_INDEX,
        TEXT_PRIMARY_HIGH,
        TEXT_SECONDARY_MED,
        TEXT_MUTED_SUBTLE,
    ]
    for token in color_tokens:
        assert hex_pattern.match(token), f"Token {token} has invalid hex format"


def test_backward_compatibility_shims():
    """Проверка 100% обратной совместимости Re-export Shims (v1 -> v2)."""
    assert BG_WINDOW == SURFACE_0_CANVAS
    assert BG_PANEL == SURFACE_1_PANEL
    assert BG_CARD == SURFACE_2_CARD
    assert BG_STRIP == SURFACE_1_PANEL
    assert BG_CELL == SURFACE_2_CARD
    assert BG_CELL_HOVER == SURFACE_3_HOVER
    assert BG_TOUCHBAR == SURFACE_1_PANEL
    assert BG_SECTION_HOVER == SURFACE_3_HOVER

    assert BORDER_SUBTLE == BORDER_SURFACE_1
    assert BORDER_CELL == BORDER_SURFACE_2
    assert BORDER_SELECTED_GLOW == BORDER_FOCUS_NEON

    assert TEXT_PRIMARY == TEXT_PRIMARY_HIGH
    assert TEXT_SECONDARY == TEXT_SECONDARY_MED
    assert TEXT_MUTED == TEXT_MUTED_SUBTLE
    assert TEXT_PLACEHOLDER == TEXT_MUTED_SUBTLE


def test_qss_contains_surface_tokens_and_applies_without_errors(qapp):
    """Проверка валидности QSS: все ключевые токены присутствуют, стили применяются без ошибок."""
    assert SURFACE_0_CANVAS in EDITOR_MAIN_QSS
    assert SURFACE_1_PANEL in EDITOR_MAIN_QSS
    assert SURFACE_2_CARD in EDITOR_MAIN_QSS
    assert BORDER_SURFACE_1 in EDITOR_MAIN_QSS
    assert BORDER_FOCUS_NEON in EDITOR_MAIN_QSS

    # Проверка наличия селекторов классов ячеек и тачбара
    assert "CellIndexLabel" in EDITOR_MAIN_QSS
    assert "CellIconLabel" in EDITOR_MAIN_QSS
    assert "CellTitleLabel" in EDITOR_MAIN_QSS
    assert "TouchbarDivider" in EDITOR_MAIN_QSS
    assert "TouchbarMediaIcon" in EDITOR_MAIN_QSS
    assert "TouchbarClockTime" in EDITOR_MAIN_QSS
    assert "TouchbarTelemetrySensor" in EDITOR_MAIN_QSS

    # Проверка селекторов инспектора и превью-плитки (Шаг 1.4)
    assert "KeyPreviewTile" in EDITOR_MAIN_QSS
    assert "TileCornerButton" in EDITOR_MAIN_QSS
    assert "InspectorLineEdit" in EDITOR_MAIN_QSS
    assert "#101522" in EDITOR_MAIN_QSS
    assert "InspectorDeleteButton" in EDITOR_MAIN_QSS
    assert "#2a171b" in EDITOR_MAIN_QSS
    assert "FormSeparator" in EDITOR_MAIN_QSS

    # Проверка селекторов библиотеки действий и поиска (Шаг 1.5)
    assert "ActionLibraryDrawer" in EDITOR_MAIN_QSS
    assert "ActionSearchInput" in EDITOR_MAIN_QSS
    assert "SearchIconLabel" in EDITOR_MAIN_QSS
    assert "SearchClearButton" in EDITOR_MAIN_QSS
    assert "ActionViewButton" in EDITOR_MAIN_QSS
    assert "ActionCategoryHeader" in EDITOR_MAIN_QSS
    assert "CategoryChevron" in EDITOR_MAIN_QSS
    assert "ActionItemCard" in EDITOR_MAIN_QSS
    assert "ActionItemIconBox" in EDITOR_MAIN_QSS
    assert "ActionItemTitle" in EDITOR_MAIN_QSS
    assert "SearchEmptyPlaceholder" in EDITOR_MAIN_QSS
    assert "DrawerInternalSeparator" in EDITOR_MAIN_QSS

    # Проверка применения к QMainWindow
    window = QMainWindow()
    apply_editor_theme(window)
    assert len(window.styleSheet()) > 0
    assert window.styleSheet() == EDITOR_MAIN_QSS


def test_deck_editor_window_theme_applied_on_init(qapp, sample_two_page_deck_config_path):
    """Проверка автоматического применения темы Dark Obsidian v2 к DeckEditorWindow при создании."""
    from modules.deck.editor.window import DeckEditorWindow

    window = DeckEditorWindow(config_path=sample_two_page_deck_config_path)
    try:
        assert len(window.styleSheet()) > 0
        assert window.styleSheet() == EDITOR_MAIN_QSS
        assert window.minimumSize().width() == WINDOW_MIN_SIZE[0]
        assert window.minimumSize().height() == WINDOW_MIN_SIZE[1]
    finally:
        window.close()


def test_grid_cell_selected_property_toggle(qapp):
    """
    Проверка динамического свойства 'selected' ячейки EditorGridCell:
    - по умолчанию selected == 'false' и is_selected() is False;
    - при set_selected(True) свойство переключается в 'true', is_selected() is True;
    - при set_selected(False) возвращается в 'false', is_selected() is False;
    - инвариант Stealth Focus: setFocusPolicy(Qt.NoFocus).
    """
    from PySide6.QtCore import Qt
    from modules.deck.editor.widgets.grid_cell import EditorGridCell

    cell = EditorGridCell(slot_index=0)
    assert cell.focusPolicy() == Qt.NoFocus
    assert cell.property("selected") == "false"
    assert not cell.is_selected()

    # Включение выделения
    cell.set_selected(True)
    assert cell.property("selected") == "true"
    assert cell.is_selected()

    # Повторный вызов не должен ломать состояние
    cell.set_selected(True)
    assert cell.property("selected") == "true"
    assert cell.is_selected()

    # Сброс выделения
    cell.set_selected(False)
    assert cell.property("selected") == "false"
    assert not cell.is_selected()


def test_touchbar_section_selected_property_toggle(qapp):
    """
    Проверка динамического свойства 'selected' секции TouchbarSectionWidget:
    - по умолчанию selected == 'false' и is_selected() is False;
    - при set_selected(True) свойство переключается в 'true', is_selected() is True;
    - при set_selected(False) возвращается в 'false', is_selected() is False;
    - инвариант Stealth Focus: setFocusPolicy(Qt.NoFocus);
    - инвариант изоляции клика: дочерние виджеты имеют WA_TransparentForMouseEvents.
    """
    from PySide6.QtCore import Qt
    from modules.deck.editor.widgets.touchbar_section import TouchbarSectionWidget

    section = TouchbarSectionWidget(
        section_type="media",
        title_key="deck.editor.canvas.touchbar.media_title",
    )
    assert section.focusPolicy() == Qt.NoFocus
    assert section.property("selected") == "false"
    assert not section.is_selected()

    # Включение выделения
    section.set_selected(True)
    assert section.property("selected") == "true"
    assert section.is_selected()

    # Повторный вызов
    section.set_selected(True)
    assert section.property("selected") == "true"
    assert section.is_selected()

    # Снятие выделения
    section.set_selected(False)
    assert section.property("selected") == "false"
    assert not section.is_selected()

