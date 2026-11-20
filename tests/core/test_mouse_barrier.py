"""
Тестирование контроллера барьера мыши (MouseBarrier).
"""
import pytest
from unittest.mock import patch, MagicMock
from core.mouse_barrier import MouseBarrier

@pytest.mark.unit
def test_mouse_barrier_initialization():
    mb = MouseBarrier(primary_rect=(0, 0, 1920, 1080))
    assert mb.primary_rect == (0, 0, 1920, 1080)
    assert mb.enabled is False
    assert mb._is_clipped is False

@pytest.mark.unit
def test_mouse_barrier_enable_disable():
    mb = MouseBarrier(primary_rect=(0, 0, 1920, 1080))
    with patch("ctypes.windll.user32.ClipCursor", return_value=1) as mock_clip, \
         patch.object(mb, "is_cursor_in_primary", return_value=True), \
         patch.object(mb, "is_alt_pressed", return_value=False):
        
        mb.enable()
        assert mb.enabled is True
        assert mb._is_clipped is True
        assert mock_clip.called

        mb.disable()
        assert mb.enabled is False
        assert mb._is_clipped is False

@pytest.mark.unit
def test_mouse_barrier_alt_release():
    mb = MouseBarrier(primary_rect=(0, 0, 1920, 1080))
    mb.enabled = True
    mb._is_clipped = True

    with patch("ctypes.windll.user32.ClipCursor", return_value=1) as mock_clip, \
         patch.object(mb, "is_alt_pressed", return_value=True):
        
        # Когда Alt нажат, барьер должен освободить курсор (ClipCursor(None))
        mb.update()
        assert mb._is_clipped is False
        mock_clip.assert_called_with(None)

@pytest.mark.unit
def test_mouse_barrier_cursor_bounds_check():
    mb = MouseBarrier(primary_rect=(0, 0, 1920, 1080))
    with patch("win32api.GetCursorPos", return_value=(500, 500)):
        assert mb.is_cursor_in_primary() is True

    with patch("win32api.GetCursorPos", return_value=(2000, 500)):
        assert mb.is_cursor_in_primary() is False
