"""
Главное окно оболочки DuckDock (800x600 / 1024x600, Frameless, WS_EX_NOACTIVATE).
Размещается на вспомогательном сенсорном экране.
"""
from ctypes import wintypes
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from core.event_bus import bus
from core.focus_guardian import FocusGuardian
from core.i18n import I18nManager, t
from core.mouse_barrier import MouseBarrier
from core.touch_filter import TouchCursorFilter
from core.window_manager import ProcessWatcher, WindowManager
from modules.audio.view import AudioMixerView
from modules.deck.view import DeckView
from modules.media.view import YouTubeView
from modules.settings.config import AppConfig
from modules.telemetry.view import SensorsView
from ui.dimmer_overlay import DimmerOverlay
from ui.showcase_view import ShowcaseView
from ui.sidebar import SidebarDock

MAIN_QSS = """
QMainWindow {
    background-color: #0b0d13;
}

QStackedWidget {
    background-color: #0e1118;
}

QFrame.placeholder-card {
    background-color: #161b26;
    border: 1px dashed #2d3748;
    border-radius: 12px;
    padding: 24px;
}
"""

class MainWindow(QMainWindow):
    """Главный контейнер оконного менеджера и дашборда второго экрана."""

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        I18nManager().set_language(self.config.language, emit_signal=False)
        self.mouse_barrier = MouseBarrier(
            primary_rect=(0, 0, 1920, 1080)
        )
        self.focus_guardian = FocusGuardian(
            subscreen_rect=self.config.display.fallback_geometry,
            restore_delay_ms=self.config.stealth.focus_restore_delay_ms,
            cursor_restore_delay_ms=self.config.stealth.cursor_restore_delay_ms,
            parent=self,
        )
        self.window_manager = WindowManager()

        self._init_window_flags()
        self._init_ui()
        self._connect_signals()

        # Позиционирование на второй монитор
        self.reposition_to_subscreen()

        # Фоновый наблюдатель за процессами сторонних приложений (Спринт 2)
        tracked_names = [app.process_name for app in self.config.tracked_apps if app.auto_tile]
        self.process_watcher = ProcessWatcher(
            window_manager=self.window_manager,
            tracked_apps=tracked_names,
            poll_interval_ms=1500,
            parent=self,
        )
        self.process_watcher.window_discovered.connect(self._on_external_window_discovered)
        self.process_watcher.window_lost.connect(self._on_external_window_lost)
        self.process_watcher.start()

        # 1. Запуск Focus Guardian hook
        if self.config.stealth.enable_stealth_focus:
            self.focus_guardian.start_hook()

        # 2. Инициализация Touch Event Filter & Swipe Engine
        if self.config.stealth.anti_cursor_warp:
            self.touch_filter = TouchCursorFilter(self.focus_guardian, self)
            qapp = QApplication.instance()
            if qapp:
                qapp.installEventFilter(self.touch_filter)
                qapp.aboutToQuit.connect(self._cleanup)

        # 3. Таймер барьера мыши и трекера положения курсора (30 мс)
        self._barrier_timer = QTimer(self)
        self._barrier_timer.setInterval(30)
        self._barrier_timer.timeout.connect(self._on_barrier_tick)
        self._barrier_timer.start()

        # Активация аппаратного барьера мыши
        self.mouse_barrier.enable()

        # 4. Подписка на сигналы изменения состава мониторов
        qapp = QApplication.instance()
        if qapp:
            qapp.screenAdded.connect(self._on_screens_changed)
            qapp.screenRemoved.connect(self._on_screens_changed)

        # Применение WS_EX_NOACTIVATE после инициализации WinID
        QTimer.singleShot(100, self._apply_stealth_winapi)

    def _init_window_flags(self):
        self.setObjectName("duckdock_root")
        self.setWindowTitle(f"DuckDock - {t('common.app_subtitle')}")
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.setFixedSize(self.config.display.width, self.config.display.height)
        self.setStyleSheet(MAIN_QSS)

    def _init_ui(self):
        self.central_widget = QWidget(self)
        self.central_widget.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.setCentralWidget(self.central_widget)

        self.root_layout = QHBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # 1. Сайдбар (80x600)
        self.sidebar = SidebarDock(self)
        self.sidebar.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.root_layout.addWidget(self.sidebar)

        # 2. Рабочая область
        self.workspace = QStackedWidget(self)
        self.workspace.setObjectName("workspace_stackedW")
        self.workspace.setFixedSize(
            self.config.layout.workspace_width,
            self.config.display.height
        )

        # Страницы рабочей области:
        # 0: YouTube & Media
        self.page_yt = YouTubeView(self)
        self.workspace.addWidget(self.page_yt)

        # 1: Sensors (AIDA64)
        self.page_sensors = SensorsView(self)
        self.workspace.addWidget(self.page_sensors)

        # 2: DuckDeck (Macro Panel & Controls)
        self.page_deck = DeckView(parent=self)
        self.workspace.addWidget(self.page_deck)

        # 3: Audio Mixer (Windows Core Audio PyCaw)
        self.page_audio = AudioMixerView(self)
        self.workspace.addWidget(self.page_audio)

        # 4: Showcase & Diagnostics
        self.page_showcase = ShowcaseView(self.config, self)
        self.workspace.addWidget(self.page_showcase)

        self.root_layout.addWidget(self.workspace)

        # 3. Сквозной слой затемнения поверх всего окна
        self.dimmer = DimmerOverlay(self)
        self.dimmer.setGeometry(0, 0, self.config.display.width, self.config.display.height)
        self.dimmer.raise_()

        # 4. Первичная инициализация локализации для сайдбара
        self.sidebar.retranslate_ui()

    def _connect_signals(self):
        bus.tab_changed.connect(self._on_tab_changed)
        bus.dimmer_toggle_requested.connect(self._on_dimmer_toggle)
        bus.input_lock_toggled.connect(self._on_input_lock_toggled)
        bus.language_changed.connect(self._on_language_changed)

    def switch_tab_by_offset(self, offset: int):
        """Переключение активной вкладки со смещением (+1: следующая, -1: предыдущая)."""
        if not hasattr(self, "workspace") or self.workspace.count() == 0:
            return
        total = self.workspace.count()
        current = self.workspace.currentIndex()
        new_tab = (current + offset) % total
        bus.tab_changed.emit(new_tab)

    def _on_tab_changed(self, index: int):
        self.workspace.setCurrentIndex(index)
        if hasattr(self, "dimmer"):
            self.dimmer.raise_()

        # Управление видимостью окон сторонних приложений (Спринт 2)
        for app in self.config.tracked_apps:
            if not app.auto_tile:
                continue

            if app.tab_index == index:
                self._tile_and_show_app(app.process_name)
            else:
                self._hide_app(app.process_name)

    def _tile_and_show_app(self, process_name: str):
        """Бесшовный тайлинг и отображение окна внешнего приложения без активации."""
        hwnd = self.window_manager.get_cached_hwnd(process_name) or self.window_manager.find_window_by_process_name(process_name)
        if hwnd and self.window_manager.is_window_valid(hwnd):
            if self.window_manager.is_minimized(hwnd):
                self.window_manager.restore_window(hwnd)

            self.window_manager.strip_window_decorations(hwnd)
            sidebar_w = self.config.layout.sidebar_width
            wx = self.x() + sidebar_w
            wy = self.y()
            ww = max(100, self.width() - sidebar_w)
            wh = self.height()
            self.window_manager.tile_window(hwnd, (wx, wy, ww, wh))
            self.window_manager.show_window_no_activate(hwnd)
            bus.external_window_tiled.emit(process_name, hwnd)

    def _hide_app(self, process_name: str):
        """Скрытие окна внешнего приложения при переходе на другую вкладку."""
        hwnd = self.window_manager.get_cached_hwnd(process_name)
        if hwnd and self.window_manager.is_window_valid(hwnd):
            self.window_manager.hide_window(hwnd)

    def _on_external_window_discovered(self, process_name: str, hwnd: int):
        """Реакция ProcessWatcher на появление нового окна в системе."""
        if not hasattr(self, "workspace"):
            return
        current_tab = self.workspace.currentIndex()
        for app in self.config.tracked_apps:
            if app.process_name.lower() == process_name.lower():
                if app.tab_index == current_tab and app.auto_tile:
                    self._tile_and_show_app(process_name)
                else:
                    # Окно найдено, но вкладка не активна — держим скрытым
                    self.window_manager.hide_window(hwnd)
                break

    def _on_external_window_lost(self, process_name: str, hwnd: int):
        """Реакция ProcessWatcher на закрытие процесса."""
        print(f"[-] Окно процесса {process_name} (HWND {hwnd}) закрыто.")

    def _on_dimmer_toggle(self):
        if hasattr(self, "dimmer"):
            self.dimmer.toggle(self.config.dimmer.night_mode_opacity)
            self.dimmer.raise_()

    def _on_input_lock_toggled(self, locked: bool):
        self.focus_guardian.input_lock_mode = locked

    def _on_language_changed(self, lang_code: str):
        self.setWindowTitle(f"DuckDock - {t('common.app_subtitle')}")

    def _on_barrier_tick(self):
        """Периодическое обновление барьера мыши и трекера координат."""
        self.mouse_barrier.update()
        try:
            import win32api
            x, y = win32api.GetCursorPos()
            self.focus_guardian.update_primary_cursor(x, y)
        except Exception:
            pass

    def _on_screens_changed(self, screen=None):
        """Реакция на системное добавление/удаление дисплея."""
        print("[*] Обнаружено изменение конфигурации мониторов (Hotplug)...")
        QTimer.singleShot(300, self.reposition_to_subscreen)

    def nativeEvent(self, event_type, message):
        """Перехват Win32 событий, включая WM_DISPLAYCHANGE (0x007E)."""
        try:
            if event_type in (b"windows_generic_MSG", "windows_generic_MSG"):
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x007E:  # WM_DISPLAYCHANGE
                    print("[*] Перехвачено системное сообщение WM_DISPLAYCHANGE (0x007E)")
                    QTimer.singleShot(300, self.reposition_to_subscreen)
        except Exception as e:
            print(f"[!] Ошибка nativeEvent: {e}")

        return super().nativeEvent(event_type, message)

    def reposition_to_subscreen(self):
        """Определить координаты экрана и адаптировать размеры окна под целевой монитор."""
        screens = QGuiApplication.screens()
        target_screen: Optional[QScreen] = None
        primary_screen: Optional[QScreen] = None

        if screens:
            primary_screen = screens[0]

        # 1. Поиск экрана по высоте 600 (800x600 или 1024x600)
        for s in screens:
            geom = s.geometry()
            if geom.height() == 600 and (geom.width() in (800, 1024)):
                target_screen = s
                break

        # 2. Если по разрешению не найден, используем индекс из конфига
        if not target_screen:
            target_idx = self.config.display.screen_index
            if len(screens) > target_idx:
                target_screen = screens[target_idx]
            elif len(screens) > 1:
                target_screen = screens[1]
            elif len(screens) == 1:
                target_screen = screens[0]

        if target_screen:
            geom = target_screen.geometry()
            target_x = geom.x()
            target_y = geom.y()
            target_w = geom.width()
            target_h = geom.height()
        else:
            fb = self.config.display.fallback_geometry
            target_x, target_y, target_w, target_h = fb

        # Обновляем геометрию барьера для основного монитора
        if primary_screen:
            p_geom = primary_screen.geometry()
            self.mouse_barrier.primary_rect = (
                p_geom.x(), p_geom.y(), p_geom.width(), p_geom.height()
            )

        # Адаптируем размер окна и рабочей зоны
        self.focus_guardian.subscreen_rect = (target_x, target_y, target_w, target_h)
        self.setFixedSize(target_w, target_h)
        self.move(target_x, target_y)

        # Рабочая зона занимает всю ширину за вычетом сайдбара
        sidebar_w = self.config.layout.sidebar_width
        workspace_w = max(100, target_w - sidebar_w)
        self.workspace.setFixedSize(workspace_w, target_h)

        if hasattr(self, "dimmer"):
            self.dimmer.setGeometry(0, 0, target_w, target_h)
            self.dimmer.raise_()

        # Перепозиционируем активное внешнее приложение под новую геометрию
        if hasattr(self, "workspace"):
            current_tab = self.workspace.currentIndex()
            for app in self.config.tracked_apps:
                if app.tab_index == current_tab and app.auto_tile:
                    self._tile_and_show_app(app.process_name)

    def _apply_stealth_winapi(self):
        """Применить WS_EX_NOACTIVATE через WinAPI."""
        try:
            hwnd = int(self.winId())
            self.focus_guardian.enable_stealth_window_style(hwnd)
        except Exception as e:
            print(f"[!] Ошибка WinAPI стелс-стиля: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "dimmer"):
            self.dimmer.setGeometry(0, 0, self.width(), self.height())
            self.dimmer.raise_()

    def _cleanup(self):
        """Освобождение системных ресурсов WinAPI при выходе."""
        if hasattr(self, "touch_filter"):
            qapp = QApplication.instance()
            if qapp:
                try:
                    qapp.removeEventFilter(self.touch_filter)
                except Exception:
                    pass
        if hasattr(self, "page_sensors") and hasattr(self.page_sensors, "cleanup"):
            self.page_sensors.cleanup()
        if hasattr(self, "page_deck") and hasattr(self.page_deck, "cleanup"):
            self.page_deck.cleanup()
        if hasattr(self, "page_audio") and hasattr(self.page_audio, "cleanup"):
            self.page_audio.cleanup()
        elif hasattr(self, "page_audio") and hasattr(self.page_audio, "poll_timer") and self.page_audio.poll_timer.isActive():
            self.page_audio.poll_timer.stop()
        if hasattr(self, "process_watcher"):
            self.process_watcher.stop()
        if hasattr(self, "_barrier_timer") and self._barrier_timer.isActive():
            self._barrier_timer.stop()
        try:
            self.mouse_barrier.disable()
        except Exception:
            pass
        try:
            self.focus_guardian.stop_hook()
        except Exception:
            pass
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            try:
                bus.tab_changed.disconnect(self._on_tab_changed)
            except Exception:
                pass
            try:
                bus.dimmer_toggle_requested.disconnect(self._on_dimmer_toggle)
            except Exception:
                pass
            try:
                bus.input_lock_toggled.disconnect(self._on_input_lock_toggled)
            except Exception:
                pass
            try:
                bus.language_changed.disconnect(self._on_language_changed)
            except Exception:
                pass

    def close(self):
        self._cleanup()
        return super().close()

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)
