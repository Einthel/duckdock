"""
Тестирование менеджера окон и инвариантов тайлинга.
"""
import pytest
from core.window_manager import WindowManager

@pytest.mark.unit
def test_window_manager_instantiation():
    wm = WindowManager()
    assert wm is not None

@pytest.mark.unit
def test_find_window_nonexistent_process():
    wm = WindowManager()
    hwnd = wm.find_window_by_process_name("non_existent_fake_app_12345.exe")
    assert hwnd is None

@pytest.mark.unit
def test_tile_window_invalid_hwnd():
    wm = WindowManager()
    # Попытка позиционирования невалидного HWND должна возвращать False без выброса исключений
    result = wm.tile_window(999999999, (0, 0, 720, 600))
    assert result is False
