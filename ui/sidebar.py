"""
Сайдбар управления DuckDock (80x600) с крупными кнопками под касания пальцем
и сквозным сенсорным Mini Media Bar для управления воспроизведением.
"""
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)

from core.event_bus import bus
from modules.media.widgets.mini_media_bar import MiniMediaBar
from ui.widgets.marquee_label import MarqueeLabel

__all__ = ["SidebarDock", "MiniMediaBar", "MarqueeLabel"]

SIDEBAR_QSS = """
QFrame#sidebar {
    background-color: #12141a;
    border-right: 1px solid #1f2430;
}

QPushButton.sidebar-btn {
    background-color: #1a1e28;
    color: #8b9bb4;
    border: 1px solid #282f40;
    border-radius: 12px;
    font-size: 20px;
    font-weight: bold;
}

QPushButton.sidebar-btn:pressed {
    background-color: #1e3a8a;
    color: #ffffff;
    border-color: #3b82f6;
}

QPushButton.sidebar-btn[active="true"] {
    background-color: #2563eb;
    color: #ffffff;
    border-color: #60a5fa;
}

/* Сквозной Mini Media Bar */
QFrame#mini_media_bar {
    background-color: #161b26;
    border: 1px solid #232b3e;
    border-radius: 10px;
}

QLabel#media_title {
    color: #60a5fa;
    font-size: 10px;
    font-weight: bold;
    padding: 2px;
}

QPushButton.mini-media-btn {
    background-color: #1e2430;
    color: #cbd5e1;
    border: 1px solid #2d3748;
    border-radius: 6px;
    font-size: 11px;
}

QPushButton.mini-media-btn:pressed {
    background-color: #2563eb;
    color: #ffffff;
    border-color: #60a5fa;
}

QPushButton.action-btn {
    background-color: #1e2430;
    color: #94a3b8;
    border: 1px solid #2d3748;
    border-radius: 12px;
    font-size: 16px;
}

QPushButton.action-btn:pressed {
    background-color: #334155;
    color: #f8fafc;
}

QPushButton.action-btn[toggled_state="true"] {
    background-color: #dc2626;
    color: #ffffff;
    border-color: #ef4444;
}
"""


class SidebarDock(QFrame):
    """Сайдбар для сенсорного экрана 80x600."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(80)
        self.setStyleSheet(SIDEBAR_QSS)

        self._active_tab = 0
        self._buttons = []
        self._input_locked = False

        self._init_ui()
        bus.tab_changed.connect(self._sync_tab)
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self, *args):
        try:
            bus.tab_changed.disconnect(self._sync_tab)
        except Exception:
            pass

    def _sync_tab(self, index: int):
        if self._active_tab != index:
            self._active_tab = index
            self._update_button_states()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. YouTube / Media
        self.btn_yt = self._create_nav_button("▶", "YouTube & Media", 0)
        layout.addWidget(self.btn_yt)

        # 2. Sensors / Telemetry
        self.btn_sensors = self._create_nav_button("⚡", "AIDA64 Sensors", 1)
        layout.addWidget(self.btn_sensors)

        # 3. DuckDeck Macro Panel
        self.btn_deck = self._create_nav_button("🎛", "DuckDeck (Макро-панель и управление)", 2)
        layout.addWidget(self.btn_deck)

        # 4. Audio Mixer
        self.btn_audio = self._create_nav_button("🔊", "Audio Mixer", 3)
        layout.addWidget(self.btn_audio)

        # 5. Showcase / Diagnostics
        self.btn_showcase = self._create_nav_button("⚙", "System Showcase", 4)
        layout.addWidget(self.btn_showcase)

        # Распорка между навигацией и сервисными кнопками
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 6. Mini Media Bar (Сквозной плеер в сайдбаре)
        self.mini_media_bar = MiniMediaBar(self)
        layout.addWidget(self.mini_media_bar)

        # 7. Lock Focus (Stealth vs Text Input)
        self.btn_lock = QPushButton("🔒")
        self.btn_lock.setObjectName("lock_toolB")
        self.btn_lock.setProperty("class", "action-btn")
        self.btn_lock.setFixedSize(QSize(64, 48))
        self.btn_lock.setFocusPolicy(Qt.NoFocus)
        self.btn_lock.setToolTip("Stealth Focus Mode (Click to allow keyboard input)")
        self.btn_lock.clicked.connect(self._toggle_input_lock)
        layout.addWidget(self.btn_lock)

        self._update_button_states()

    def _create_nav_button(self, icon: str, tooltip: str, tab_index: int) -> QPushButton:
        btn = QPushButton(icon)
        btn.setProperty("class", "sidebar-btn")
        btn.setFixedSize(QSize(64, 60))
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setToolTip(tooltip)
        btn.clicked.connect(lambda: self._on_tab_clicked(tab_index))
        self._buttons.append((btn, tab_index))
        return btn

    def _on_tab_clicked(self, index: int):
        self._active_tab = index
        self._update_button_states()
        bus.tab_changed.emit(index)

    def _update_button_states(self):
        for btn, idx in self._buttons:
            is_active = (idx == self._active_tab)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _toggle_input_lock(self):
        self._input_locked = not self._input_locked
        self.btn_lock.setText("🔓" if self._input_locked else "🔒")
        self.btn_lock.setProperty("toggled_state", "true" if self._input_locked else "false")
        self.btn_lock.style().unpolish(self.btn_lock)
        self.btn_lock.style().polish(self.btn_lock)
        bus.input_lock_toggled.emit(self._input_locked)
