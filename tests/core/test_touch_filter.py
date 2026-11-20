"""
Тестирование перехватчика тач-событий (TouchCursorFilter).
"""
import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import QEvent, QObject
from core.focus_guardian import FocusGuardian
from core.touch_filter import TouchCursorFilter

@pytest.mark.unit
def test_touch_filter_creation():
    guardian = FocusGuardian()
    filter_obj = TouchCursorFilter(guardian)
    assert filter_obj.guardian is guardian
    assert filter_obj._touch_active is False

@pytest.mark.unit
def test_touch_filter_events():
    guardian = MagicMock(spec=FocusGuardian)
    guardian.cursor_restore_delay_ms = 0
    filter_obj = TouchCursorFilter(guardian)

    dummy_target = QObject()

    # TouchBegin
    ev_begin = QEvent(QEvent.Type.TouchBegin)
    filter_obj.eventFilter(dummy_target, ev_begin)
    assert filter_obj._touch_active is True

    # TouchEnd
    ev_end = QEvent(QEvent.Type.TouchEnd)
    filter_obj.eventFilter(dummy_target, ev_end)
    assert filter_obj._touch_active is False
