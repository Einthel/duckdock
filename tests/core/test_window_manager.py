"""
Тестирование менеджера окон и инвариантов тайлинга.
"""
import pytest
from unittest.mock import patch, MagicMock
from core.window_manager import WindowManager, ProcessWatcher

@pytest.mark.unit
def test_window_manager_instantiation():
    wm = WindowManager()
    assert wm is not None
    assert wm._cached_hwnds == {}

@pytest.mark.unit
def test_find_window_nonexistent_process():
    wm = WindowManager()
    with patch("psutil.process_iter", return_value=[]):
        hwnd = wm.find_window_by_process_name("non_existent_fake_app_12345.exe")
        assert hwnd is None

@pytest.mark.unit
def test_tile_window_invalid_hwnd():
    wm = WindowManager()
    # Попытка позиционирования невалидного HWND должна возвращать False без выброса исключений
    result = wm.tile_window(999999999, (0, 0, 720, 600))
    assert result is False

@pytest.mark.unit
def test_window_manager_cache_management():
    wm = WindowManager()
    wm._cached_hwnds["test.exe"] = 12345

    with patch.object(wm, "is_window_valid", return_value=True):
        assert wm.get_cached_hwnd("test.exe") == 12345

    with patch.object(wm, "is_window_valid", return_value=False):
        assert wm.get_cached_hwnd("test.exe") is None
        assert "test.exe" not in wm._cached_hwnds

@pytest.mark.unit
def test_process_watcher_initialization():
    wm = WindowManager()
    with patch.object(wm, "find_window_by_process_name", return_value=None):
        watcher = ProcessWatcher(wm, tracked_apps=["happ.exe"], poll_interval_ms=1000)
        assert watcher.tracked_apps == ["happ.exe"]
        assert watcher.poll_interval_ms == 1000

        watcher.add_tracked_app("aida64.exe")
        assert "aida64.exe" in watcher.tracked_apps

        watcher.remove_tracked_app("happ.exe")
        assert "happ.exe" not in watcher.tracked_apps

@pytest.mark.unit
def test_process_watcher_scan_discovery_and_loss():
    wm = WindowManager()
    with patch.object(wm, "find_window_by_process_name", return_value=None):
        watcher = ProcessWatcher(wm, tracked_apps=["happ.exe"], poll_interval_ms=1000)

    discovered_events = []
    lost_events = []
    watcher.window_discovered.connect(lambda name, hwnd: discovered_events.append((name, hwnd)))
    watcher.window_lost.connect(lambda name, hwnd: lost_events.append((name, hwnd)))

    # 1. Симулируем обнаружение окна
    with patch.object(wm, "get_cached_hwnd", return_value=None), \
         patch.object(wm, "find_window_by_process_name", return_value=54321), \
         patch.object(wm, "strip_window_decorations", return_value=True):
        
        watcher.scan()
        assert len(discovered_events) == 1
        assert discovered_events[0] == ("happ.exe", 54321)

    # 2. Симулируем потерю окна (процесс закрыт)
    wm._cached_hwnds["happ.exe"] = 54321
    with patch.object(wm, "is_window_valid", return_value=False), \
         patch.object(wm, "find_window_by_process_name", return_value=None):
        watcher.scan()
        assert len(lost_events) == 1
        assert lost_events[0] == ("happ.exe", 54321)
        assert "happ.exe" not in wm._cached_hwnds
