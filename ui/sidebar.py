"""
Сайдбар управления DuckDock (80x600) с крупными кнопками 64x64 под касания пальцем.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QSize
from core.event_bus import bus

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

QPushButton.sidebar-btn:hover {
    background-color: #242b3a;
    color: #e2e8f0;
    border-color: #3b82f6;
}

QPushButton.sidebar-btn:pressed {
    background-color: #1e3a8a;
    color: #ffffff;
}

QPushButton.sidebar-btn[active="true"] {
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

QPushButton.action-btn:hover {
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

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 1. YouTube / Media
        self.btn_yt = self._create_nav_button("▶", "YouTube & Media", 0)
        layout.addWidget(self.btn_yt)

        # 2. Sensors / Telemetry
        self.btn_sensors = self._create_nav_button("⚡", "AIDA64 Sensors", 1)
        layout.addWidget(self.btn_sensors)

        # 3. External Apps / happ
        self.btn_happ = self._create_nav_button("🌐", "happ Proxy & Tunnels", 2)
        layout.addWidget(self.btn_happ)

        # 4. Audio Mixer
        self.btn_audio = self._create_nav_button("🔊", "Audio Mixer", 3)
        layout.addWidget(self.btn_audio)

        # 5. Showcase / Diagnostics
        self.btn_showcase = self._create_nav_button("⚙", "System Showcase", 4)
        layout.addWidget(self.btn_showcase)

        # Распорка между навигацией и сервисными кнопками
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 6. Lock Focus (Stealth vs Text Input)
        self.btn_lock = QPushButton("🔒")
        self.btn_lock.setObjectName("lock_toolB")
        self.btn_lock.setProperty("class", "action-btn")
        self.btn_lock.setFixedSize(QSize(64, 64))
        self.btn_lock.setFocusPolicy(Qt.NoFocus)
        self.btn_lock.setToolTip("Stealth Focus Mode (Click to allow keyboard input)")
        self.btn_lock.clicked.connect(self._toggle_input_lock)
        layout.addWidget(self.btn_lock)

        # 7. Sleep / Dimmer
        self.btn_dimmer = QPushButton("🌙")
        self.btn_dimmer.setObjectName("sleep_toolB")
        self.btn_dimmer.setProperty("class", "action-btn")
        self.btn_dimmer.setFixedSize(QSize(64, 64))
        self.btn_dimmer.setFocusPolicy(Qt.NoFocus)
        self.btn_dimmer.setToolTip("Toggle Screen Dimmer / Night Mode")
        self.btn_dimmer.clicked.connect(self._toggle_dimmer)
        layout.addWidget(self.btn_dimmer)

        self._update_button_states()

    def _create_nav_button(self, icon: str, tooltip: str, tab_index: int) -> QPushButton:
        btn = QPushButton(icon)
        btn.setProperty("class", "sidebar-btn")
        btn.setFixedSize(QSize(64, 64))
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

    def _toggle_dimmer(self):
        bus.dimmer_toggle_requested.emit()
