"""
Модульные тесты захвата сложных комбинаций клавиш (HotkeyCaptureButton)
и ручного конструктора комбинаций (HotkeyBuilderPopover).
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from core.i18n import I18nManager
from modules.deck.editor.widgets.hotkey_capture import HotkeyCaptureButton
from modules.deck.editor.widgets.hotkey_popover import HotkeyBuilderPopover


@pytest.fixture(autouse=True)
def reset_i18n_language():
    initial_lang = I18nManager().current_language
    yield
    I18nManager().set_language(initial_lang, emit_signal=False)


def test_capture_tab_backtab_and_ctrl_shift_tab(qapp, qtbot):
    win = QWidget()
    layout = QVBoxLayout(win)
    btn = HotkeyCaptureButton(win)
    other = HotkeyCaptureButton(win)
    layout.addWidget(btn)
    layout.addWidget(other)
    win.show()
    qtbot.addWidget(win)

    btn.start_capture()
    assert btn.is_capturing() is True

    # Ctrl+Shift+Tab (Qt.Key_Backtab)
    ev = QKeyEvent(QEvent.KeyPress, Qt.Key_Backtab, Qt.ControlModifier | Qt.ShiftModifier)
    qapp.sendEvent(btn, ev)
    assert btn.is_capturing() is False
    assert btn.get_hotkey() == "Ctrl+Shift+Tab"

    # Одиночный Tab
    btn.start_capture()
    ev_tab = QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier)
    qapp.sendEvent(btn, ev_tab)
    assert btn.get_hotkey() == "Tab"


def test_capture_esc_with_modifiers_vs_bare_esc(qapp, qtbot):
    btn = HotkeyCaptureButton()
    btn.show()
    qtbot.addWidget(btn)

    btn.set_hotkey("F5")
    btn.start_capture()

    # Голый Esc отменяет захват без изменения хоткея
    qapp.sendEvent(btn, QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    assert btn.is_capturing() is False
    assert btn.get_hotkey() == "F5"

    # Ctrl+Shift+Esc записывается как комбинация
    btn.start_capture()
    qapp.sendEvent(
        btn,
        QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.ControlModifier | Qt.ShiftModifier),
    )
    assert btn.is_capturing() is False
    assert btn.get_hotkey() == "Ctrl+Shift+Esc"


def test_capture_f1_to_f12_and_shortcut_override(qapp, qtbot):
    win = QMainWindow()
    btn = HotkeyCaptureButton(win)
    win.setCentralWidget(btn)

    shortcut_triggered = []
    sc = QShortcut(QKeySequence("Ctrl+Shift+Z"), win)
    sc.activated.connect(lambda: shortcut_triggered.append(True))

    win.show()
    qtbot.addWidget(win)

    # ShortcutOverride при активном захвате должен приниматься кнопкой
    btn.start_capture()
    so_ev = QKeyEvent(QEvent.ShortcutOverride, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    assert btn.event(so_ev) is True
    assert so_ev.isAccepted() is True

    # Захват F12
    qapp.sendEvent(btn, QKeyEvent(QEvent.KeyPress, Qt.Key_F12, Qt.ControlModifier | Qt.ShiftModifier))
    assert btn.get_hotkey() == "Ctrl+Shift+F12"
    assert shortcut_triggered == []


def test_hotkey_builder_popover_manual_selection_and_presets(qapp, qtbot):
    btn = HotkeyCaptureButton()
    btn.resize(220, 30)
    btn.show()
    qtbot.addWidget(btn)

    # Клик по зоне стрелки ▾ справа открывает поповер, а не захват
    arrow_pos = QPoint(btn.width() - 10, btn.height() // 2)
    qtbot.mouseClick(btn, Qt.LeftButton, pos=arrow_pos)
    assert btn.is_capturing() is False
    assert btn._popover is not None
    assert btn._popover.isVisible() is True

    pop: HotkeyBuilderPopover = btn._popover
    pop._mod_buttons["Ctrl"].setChecked(True)
    pop._mod_buttons["Shift"].setChecked(True)
    idx_esc = pop.combo_special.findData("Esc")
    assert idx_esc > 0
    pop.combo_special.setCurrentIndex(idx_esc)

    with qtbot.waitSignal(btn.hotkey_changed, timeout=1000) as blocker:
        qtbot.mouseClick(pop.btn_apply, Qt.LeftButton)

    assert blocker.args == ["Ctrl+Shift+Esc"]
    assert btn.get_hotkey() == "Ctrl+Shift+Esc"
    assert pop.isVisible() is False

    # Повторное открытие: состояние конструктора синхронизировано с текущим хоткеем
    btn.open_builder_popover()
    assert pop._mod_buttons["Ctrl"].isChecked() is True
    assert pop._mod_buttons["Shift"].isChecked() is True
    assert pop._mod_buttons["Alt"].isChecked() is False
    assert pop.combo_special.currentData() == "Esc"

    # Ручной ввод буквы + Alt
    pop._mod_buttons["Ctrl"].setChecked(False)
    pop._mod_buttons["Shift"].setChecked(False)
    pop._mod_buttons["Alt"].setChecked(True)
    pop.edit_custom.setText("k")
    pop._on_custom_edited("k")
    pop._on_apply_clicked()
    assert btn.get_hotkey() == "Alt+K"

    # Retranslate
    I18nManager().set_language("en")
    btn.retranslate_ui()
    assert pop.btn_apply.text() == "Apply"
