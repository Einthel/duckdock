"""
Модульные тесты кастомизации типографики кнопок DuckDeck (Спринт 7.1).
Проверяют FontCustomizationPopover, сигналы font_changed, флаги фокуса,
адаптер DTO и применение параметров шрифта.
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from modules.deck.editor.adapter import DeckConfigAdapter
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.widgets.font_popover import (
    FONT_SIZES,
    TEXT_COLORS,
    FontCustomizationPopover,
)
from modules.deck.models import DeckButtonConfig


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_font_popover_init_and_invariants(qapp):
    """Проверка флагов изоляции фокуса и модальности поповера."""
    parent = QWidget()
    popover = FontCustomizationPopover(parent=parent)

    assert popover.focusPolicy() == Qt.NoFocus
    assert popover.testAttribute(Qt.WA_ShowWithoutActivating) is True
    window_flags = popover.windowFlags()
    assert bool(window_flags & Qt.Popup) is True
    assert bool(window_flags & Qt.FramelessWindowHint) is True


def test_font_popover_size_buttons(qapp):
    """Проверка выбора размеров шрифта (9, 11, 13, 15 px)."""
    popover = FontCustomizationPopover()
    received = []
    popover.font_changed.connect(lambda data: received.append(data))

    for sz in FONT_SIZES:
        btn = popover._size_buttons.get(sz)
        assert btn is not None
        btn.click()
        assert len(received) > 0
        assert received[-1].get("font_size") == sz
        assert popover._font_size == sz


def test_font_popover_alignment_buttons(qapp):
    """Проверка выбора выравнивания (bottom, center, top)."""
    popover = FontCustomizationPopover()
    received = []
    popover.font_changed.connect(lambda data: received.append(data))

    for align in ["top", "center", "bottom"]:
        btn = popover._align_buttons.get(align)
        assert btn is not None
        btn.click()
        assert len(received) > 0
        assert received[-1].get("text_alignment") == align
        assert popover._text_alignment == align


def test_font_popover_color_chips_and_reset(qapp):
    """Проверка выбора цвета и кнопки Reset."""
    popover = FontCustomizationPopover()
    received = []
    popover.font_changed.connect(lambda data: received.append(data))

    # Клик по цветному чипу
    test_color = TEXT_COLORS[0]
    chip_btn = popover._color_buttons.get(test_color)
    assert chip_btn is not None
    chip_btn.click()
    assert len(received) > 0
    assert received[-1].get("font_color") == test_color
    assert popover._font_color == test_color

    # Клик по кнопке Reset (возврат дефолтного цвета #d4d4d8)
    popover.btn_reset_color.click()
    assert received[-1].get("font_color") == "#d4d4d8"
    assert popover._font_color == "#d4d4d8"


def test_font_popover_hide_title_checkbox(qapp):
    """Проверка чекбокса скрытия заголовка."""
    popover = FontCustomizationPopover()
    received = []
    popover.font_changed.connect(lambda data: received.append(data))

    popover.chk_hide_title.setChecked(True)
    assert len(received) > 0
    assert received[-1].get("hide_title") is True
    assert popover._hide_title is True

    popover.chk_hide_title.setChecked(False)
    assert received[-1].get("hide_title") is False
    assert popover._hide_title is False


def test_font_popover_set_state(qapp):
    """Проверка программной установки состояния set_state."""
    popover = FontCustomizationPopover()
    popover.set_state(
        font_size=15,
        font_color="#38bdf8",
        text_alignment="top",
        hide_title=True,
    )
    assert popover._font_size == 15
    assert popover._font_color == "#38bdf8"
    assert popover._text_alignment == "top"
    assert popover._hide_title is True
    assert popover.chk_hide_title.isChecked() is True


def test_font_popover_show_at_widget(qapp):
    """Проверка позиционирования всплывающего окна под целевым виджетом."""
    parent = QWidget()
    parent.setGeometry(100, 100, 400, 300)
    target_btn = QPushButton("T", parent)
    target_btn.setGeometry(50, 50, 28, 28)
    parent.show()

    popover = FontCustomizationPopover(parent=parent)
    popover.show_at_widget(target_btn)
    assert popover.isVisible()
    popover.close()
    parent.close()


def test_adapter_typography_mapping():
    """Проверка двустороннего мапинга типографики в DeckConfigAdapter."""
    from modules.deck.models import DeckActionConfig

    btn_config = DeckButtonConfig(
        id="btn_test",
        title="Custom Text",
        action=DeckActionConfig(action_type="hotkey"),
        font_size=13,
        font_color="#f59e0b",
        text_alignment="top",
        hide_title=True,
    )
    dto = DeckConfigAdapter.slot_to_dto(btn_config)
    assert dto.font_size == 13
    assert dto.font_color == "#f59e0b"
    assert dto.text_alignment == "top"
    assert dto.hide_title is True

    reconstructed = DeckConfigAdapter.dto_to_slot(dto)
    assert reconstructed.font_size == 13
    assert reconstructed.font_color == "#f59e0b"
    assert reconstructed.text_alignment == "top"
    assert reconstructed.hide_title is True
