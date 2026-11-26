"""
Тестирование главного окна (MainWindow) и механизмов Спринтов 1 и 2.
"""
import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import Qt, QTimer
from core.config import AppConfig, TrackedAppConfig
from ui.main_window import MainWindow

@pytest.mark.unit
def test_main_window_initialization(qapp):
    config = AppConfig()
    with patch("core.window_manager.WindowManager.find_window_by_process_name", return_value=None):
        win = MainWindow(config)
    assert win is not None
    assert win.focus_guardian is not None
    assert win.mouse_barrier is not None
    assert hasattr(win, "touch_filter")
    assert hasattr(win, "process_watcher")
    win.close()

@pytest.mark.unit
def test_main_window_reposition_to_subscreen(qapp):
    config = AppConfig()
    with patch("core.window_manager.WindowManager.find_window_by_process_name", return_value=None):
        win = MainWindow(config)
    win.reposition_to_subscreen()
    
    # Должен установить ширину окна равной ширине экрана
    assert win.width() in (800, 1024, 1920, 2560)
    # Рабочая зона должна быть: ширина окна - ширина сайдбара (80)
    assert win.workspace.width() == win.width() - 80
    win.close()

@pytest.mark.unit
def test_main_window_tab_switching_external_app(qapp):
    config = AppConfig(
        tracked_apps=[
            TrackedAppConfig(name="happ", process_name="happ.exe", tab_index=2, auto_tile=True)
        ]
    )
    with patch("core.window_manager.WindowManager.find_window_by_process_name", return_value=None):
        win = MainWindow(config)

    with patch.object(win, "_tile_and_show_app") as mock_show, \
         patch.object(win, "_hide_app") as mock_hide:
        
        # Переключение на вкладку 2 (happ.exe)
        win._on_tab_changed(2)
        mock_show.assert_called_with("happ.exe")

        # Переключение на вкладку 0 (YouTube) -> happ.exe должен быть скрыт
        win._on_tab_changed(0)
        mock_hide.assert_called_with("happ.exe")

    win.close()

@pytest.mark.unit
def test_main_window_external_app_already_running(qapp):
    """
    Регрессионный тест: стороннее приложение уже запущено до старта DuckDock.
    ProcessWatcher при синхронном scan() в конструкторе не должен вызывать
    AttributeError: 'MainWindow' object has no attribute 'workspace'.
    """
    config = AppConfig(
        tracked_apps=[
            TrackedAppConfig(name="happ", process_name="happ.exe", tab_index=2, auto_tile=True)
        ]
    )
    with patch("core.window_manager.WindowManager.find_window_by_process_name", return_value=77777), \
         patch("core.window_manager.WindowManager.strip_window_decorations", return_value=True), \
         patch("core.window_manager.WindowManager.is_window_valid", return_value=True), \
         patch("core.window_manager.WindowManager.hide_window", return_value=True):

        win = MainWindow(config)
        assert win is not None
        win.close()


@pytest.mark.unit
def test_main_window_mouse_barrier_uses_physical_dpi_pixels(qapp):
    """
    Регрессионный тест: при системном масштабировании Windows (напр. 125% -> 2048x1152 в Qt)
    MouseBarrier должен получать физические пиксели (2560x1440), а не логические QScreen.geometry().
    """
    from PySide6.QtCore import QRect

    mock_primary = MagicMock()
    mock_primary.geometry.return_value = QRect(0, 0, 2048, 1152)
    mock_primary.devicePixelRatio.return_value = 1.25

    config = AppConfig()
    with patch("core.window_manager.WindowManager.find_window_by_process_name", return_value=None), \
         patch("core.mouse_barrier.MouseBarrier.get_physical_primary_rect", return_value=None), \
         patch("PySide6.QtGui.QGuiApplication.primaryScreen", return_value=mock_primary), \
         patch("PySide6.QtGui.QGuiApplication.screens", return_value=[mock_primary]):
        win = MainWindow(config)
        assert win.mouse_barrier.primary_rect == (0, 0, 2560, 1440)
        win.close()
