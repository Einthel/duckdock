"""
Панель системной диагностики и витрина компонентов (Showcase View).
Позволяет в реальном времени отслеживать состояние WinAPI хуков,
координаты дисплеев и работу защитника фокуса.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt
from core.event_bus import bus

SHOWCASE_QSS = """
QFrame.diag-card {
    background-color: #161b26;
    border: 1px solid #232b3e;
    border-radius: 12px;
    padding: 14px;
}

QLabel.diag-label {
    color: #94a3b8;
    font-size: 13px;
}

QLabel.diag-value {
    color: #38bdf8;
    font-size: 14px;
    font-weight: bold;
}

QPushButton.test-btn {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: bold;
}

QPushButton.test-btn:hover {
    background-color: #3b82f6;
}
"""

class ShowcaseView(QWidget):
    """Экран статуса подсистем DuckDock."""

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.lbl_dimmer_status = None
        self.setStyleSheet(SHOWCASE_QSS)
        self._init_ui()
        bus.dimmer_opacity_changed.connect(self._on_dimmer_opacity_changed)
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self, *args):
        try:
            bus.dimmer_opacity_changed.disconnect(self._on_dimmer_opacity_changed)
        except Exception:
            pass

    def _on_dimmer_opacity_changed(self, opacity: float):
        if opacity > 0.05:
            self.btn_test_dimmer.setText(f"☀️ Выключить затемнение ({int(opacity * 100)}%)")
            self.btn_test_dimmer.setStyleSheet("background-color: #f59e0b; color: #000000;")
            if self.lbl_dimmer_status:
                self.lbl_dimmer_status.setText(f"Активен ({int(opacity * 100)}%)")
                self.lbl_dimmer_status.setStyleSheet("color: #f59e0b; font-size: 14px; font-weight: bold;")
        else:
            self.btn_test_dimmer.setText("🌙 Включить ночной режим (Диммер)")
            self.btn_test_dimmer.setStyleSheet("")
            if self.lbl_dimmer_status:
                self.lbl_dimmer_status.setText("Выключен (0%)")
                self.lbl_dimmer_status.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: bold;")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("⚙ ДИАГНОСТИКА ПОДСИСТЕМ И ИНВАРИАНТОВ DUCKDOCK")
        title.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Карточка 1: Дисплей и DPI
        card_dpi = self._create_card(
            "ПАРАМЕТРЫ ДИСПЛЕЯ",
            [
                ("Разрешение:", "800 x 600 px (4:3)"),
                ("DPI Awareness:", "Per-Monitor V2 (Active)"),
                ("Рендеринг:", "iGPU (AMD Radeon Graphics)"),
            ]
        )
        grid.addWidget(card_dpi, 0, 0)

        # Карточка 2: Stealth Focus
        card_focus = self._create_card(
            "STEALTH TOUCH GUARDIAN",
            [
                ("WS_EX_NOACTIVATE:", "Включен (0x08000000)"),
                ("Anti-Cursor Warp:", "Активен (Задержка 25 мс)"),
                ("Primary Focus Restore:", "80 мс"),
            ]
        )
        grid.addWidget(card_focus, 0, 1)

        # Карточка 3: Менеджер сторонних окон
        card_wm = self._create_card(
            "BORDERLESS TILING (720x600)",
            [
                ("Зона тайлинга:", "X: +80px, W: 720, H: 600"),
                ("Обрезка рамок:", "WS_CAPTION | WS_THICKFRAME"),
                ("Целевой процесс:", "happ.exe (Proxy UI)"),
            ]
        )
        grid.addWidget(card_wm, 1, 0)

        # Карточка 4: Сервисные функции
        card_qol = self._create_card(
            "СЕРВИСНЫЕ ФУНКЦИИ (QoL)",
            [
                ("Software Dimmer:", "Выключен (0%)"),
                ("Mouse Barrier:", "Alt Key Bypass"),
                ("Display Hotplug:", "WM_DISPLAYCHANGE Listener"),
            ]
        )
        grid.addWidget(card_qol, 1, 1)

        layout.addLayout(grid)

        # Интерактивные тесты
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_test_dimmer = QPushButton("🌙 Включить ночной режим (Диммер)")
        self.btn_test_dimmer.setProperty("class", "test-btn")
        self.btn_test_dimmer.setFocusPolicy(Qt.NoFocus)
        self.btn_test_dimmer.clicked.connect(lambda: bus.dimmer_toggle_requested.emit())
        btn_layout.addWidget(self.btn_test_dimmer)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _create_card(self, header: str, items: list) -> QFrame:
        card = QFrame()
        card.setProperty("class", "diag-card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        lbl_head = QLabel(header)
        lbl_head.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_head)

        for label_text, val_text in items:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setProperty("class", "diag-label")
            val = QLabel(val_text)
            val.setProperty("class", "diag-value")
            if label_text == "Software Dimmer:":
                self.lbl_dimmer_status = val
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            layout.addLayout(row)

        return card
