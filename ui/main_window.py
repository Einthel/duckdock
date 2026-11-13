"""
Главное окно оболочки DuckDock (800x600, Frameless, WS_EX_NOACTIVATE).
Размещается на вспомогательном сенсорном экране.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QLabel, QVBoxLayout, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QScreen

from core.config import AppConfig
from core.event_bus import bus
from core.focus_guardian import FocusGuardian
from core.window_manager import WindowManager
from ui.sidebar import SidebarDock
from ui.dimmer_overlay import DimmerOverlay
from ui.showcase_view import ShowcaseView
from ui.modules.sensors_view import SensorsView
from ui.modules.youtube_view import YouTubeView

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
        self.focus_guardian = FocusGuardian(
            subscreen_rect=self.config.display.fallback_geometry,
            restore_delay_ms=self.config.stealth.focus_restore_delay_ms,
            cursor_restore_delay_ms=self.config.stealth.cursor_restore_delay_ms,
        )
        self.window_manager = WindowManager()

        self._init_window_flags()
        self._init_ui()
        self._connect_signals()

        # Позиционирование на второй монитор
        self.reposition_to_subscreen()

        # Применение WS_EX_NOACTIVATE после инициализации WinID
        QTimer.singleShot(100, self._apply_stealth_winapi)

    def _init_window_flags(self):
        self.setObjectName("duckdock_root")
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(self.config.display.width, self.config.display.height)
        self.setStyleSheet(MAIN_QSS)

    def _init_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.root_layout = QHBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # 1. Сайдбар (80x600)
        self.sidebar = SidebarDock(self)
        self.root_layout.addWidget(self.sidebar)

        # 2. Рабочая область (720x600)
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

        # 2: happ / External App Placeholder
        self.page_happ = self._create_external_app_view("happ.exe (Proxy UI)", 2)
        self.workspace.addWidget(self.page_happ)

        # 3: Audio Mixer Placeholder
        self.page_audio = self._create_external_app_view("Windows Audio Session Mixer", 3)
        self.workspace.addWidget(self.page_audio)

        # 4: Showcase & Diagnostics
        self.page_showcase = ShowcaseView(self.config, self)
        self.workspace.addWidget(self.page_showcase)

        self.root_layout.addWidget(self.workspace)

        # 3. Сквозной слой затемнения поверх всего окна 800x600
        self.dimmer = DimmerOverlay(self)
        self.dimmer.setGeometry(0, 0, self.config.display.width, self.config.display.height)
        self.dimmer.raise_()

    def _create_external_app_view(self, title: str, tab_idx: int) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setProperty("class", "placeholder-card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        lbl_t = QLabel(f"Тайлинг внешнего приложения: {title}")
        lbl_t.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: bold;")
        c_layout.addWidget(lbl_t)

        lbl_desc = QLabel(
            "Вкладка активна. Менеджер окон автоматически находит процесс по имени,\n"
            "снимает рамки заголовка (WS_CAPTION) и бесшовно вписывает окно в зону 720x600.\n\n"
            "Если приложение не запущено, окно ожидает запуска в фоне."
        )
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
        c_layout.addWidget(lbl_desc)

        layout.addWidget(card)
        return widget

    def _connect_signals(self):
        bus.tab_changed.connect(self._on_tab_changed)
        bus.dimmer_toggle_requested.connect(self._on_dimmer_toggle)
        bus.input_lock_toggled.connect(self._on_input_lock_toggled)

    def _on_tab_changed(self, index: int):
        self.workspace.setCurrentIndex(index)

        # Если переключились на вкладку стороннего приложения (например, happ)
        if index == 2:
            self._try_tile_app("happ.exe")

    def _try_tile_app(self, process_name: str):
        hwnd = self.window_manager.find_window_by_process_name(process_name)
        if hwnd:
            self.window_manager.strip_window_decorations(hwnd)
            # Вписываем в координаты: глобальный X окна + 80px, глобальный Y, W: 720, H: 600
            wx = self.x() + self.config.layout.sidebar_width
            wy = self.y()
            self.window_manager.tile_window(
                hwnd, (wx, wy, self.config.layout.workspace_width, self.config.display.height)
            )

    def _on_dimmer_toggle(self):
        self.dimmer.toggle(self.config.dimmer.night_mode_opacity)

    def _on_input_lock_toggled(self, locked: bool):
        self.focus_guardian.input_lock_mode = locked

    def reposition_to_subscreen(self):
        """Определить координаты 7" экрана и переместить окно туда."""
        screens = QGuiApplication.screens()
        target_screen: Optional[QScreen] = None

        target_idx = self.config.display.screen_index
        if len(screens) > target_idx:
            target_screen = screens[target_idx]
        elif len(screens) > 1:
            target_screen = screens[1]
        elif len(screens) == 1:
            target_screen = screens[0]

        if target_screen:
            geom = target_screen.geometry()
            # Обновляем координаты для защитника фокуса
            self.focus_guardian.subscreen_rect = (geom.x(), geom.y(), geom.width(), geom.height())
            self.move(geom.x(), geom.y())
        else:
            fb = self.config.display.fallback_geometry
            self.move(fb[0], fb[1])

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
