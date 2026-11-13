# DuckDock / TouchWM: Архитектурная спецификация модулей

## 1. Схема взаимодействия подсистем

```mermaid
graph TD
    Main[main.py] --> DPI[core.dpi]
    Main --> App[QApplication]
    App --> Bus[core.event_bus.EventBus]
    App --> Win[ui.main_window.MainWindow]
    
    Win --> Sidebar[ui.sidebar.SidebarDock]
    Win --> Workspace[QStackedWidget: 720x600]
    Win --> Dimmer[ui.dimmer_overlay.DimmerOverlay]
    
    Workspace --> Showcase[ui.showcase_view.ShowcaseView]
    Workspace --> Sensors[ui.modules.sensors_view.SensorsView]
    Workspace --> Media[ui.modules.youtube_view.YouTubeView]
    
    App --> Guardian[core.focus_guardian.FocusGuardian]
    App --> WM[core.window_manager.WindowManager]
    Sensors --> Aida[core.aida_reader.AidaReader]
    App --> Barrier[core.mouse_barrier.MouseBarrier]
```

## 2. Контракты ядра

* `WindowManager`:
  * `find_window_by_process(exe_name: str) -> Optional[int]`
  * `strip_window_decorations(hwnd: int) -> bool`
  * `tile_window(hwnd: int, rect: Tuple[int, int, int, int]) -> bool`
  * `set_window_visible(hwnd: int, visible: bool) -> None`

* `FocusGuardian`:
  * `enable_stealth_mode(hwnd: int) -> None`
  * `start_hook() -> bool`
  * `stop_hook() -> None`
  * `on_touch_detected(primary_pos: Tuple[int, int]) -> None`

* `AidaReader`:
  * `read_sensors() -> Dict[str, Any]`
  * `is_available() -> bool`
