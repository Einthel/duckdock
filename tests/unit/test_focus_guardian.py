"""
Тестирование защитника фокуса (FocusGuardian).
"""
import pytest
from core.focus_guardian import FocusGuardian

@pytest.mark.unit
def test_focus_guardian_initialization():
    fg = FocusGuardian(subscreen_rect=(1920, 0, 800, 600))
    assert fg.subscreen_rect == (1920, 0, 800, 600)
    assert fg.input_lock_mode is False

@pytest.mark.unit
def test_cursor_tracking_within_primary_screen():
    fg = FocusGuardian(subscreen_rect=(1920, 0, 800, 600))
    # Курсор на основном мониторе
    fg.update_primary_cursor(500, 500)
    assert fg.last_primary_cursor_pos == (500, 500)

    # Курсор зашел на вспомогательный монитор (x >= 1920) - не должен перезаписывать позицию первого экрана!
    fg.update_primary_cursor(2000, 300)
    assert fg.last_primary_cursor_pos == (500, 500)
