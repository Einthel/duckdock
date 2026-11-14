"""
Двухуровневый аппаратный NOC-дашборд 944x600 (SensorsView).
Прямой сбор телеметрии через LibreHardwareMonitorLib (Ring 0 / UAC) с изоляцией в QThread.

Архитектура UI:
- Header Bar (36px): Индикатор Ring 0, UAC статус, системный Uptime.
- Верхний ярус (Hero Cards 2x ~250px):
    * CPU Master: Температура Tctl/Tdie, Load %, Clock GHz, Power W, Fan/Pump RPM, 60s Sparkline.
    * GPU Master: Температура dGPU + Hotspot, Load %, VRAM Bar, Power W, Fan RPM, 60s Sparkline.
- Нижний ярус (NOC Grid 4x ~220px):
    * RAM DDR5: Занято/Всего ГБ, прогресс-бар, мини-спарклайн нагрузки.
    * Network & Ping: Download/Upload MB/s, задержка DNS Ping (мс), мини-спарклайн.
    * NVMe Storage: Температура накопителя, % активности, статус.
    * Chassis & Motherboard: Обороты корпусных вентиляторов, VRM темп, статус охлаждения.
- Инвариант Stealth Focus: Строгий Qt.NoFocus на всех элементах.
"""
from typing import Optional, Union, Dict, Any, List

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QProgressBar,
    QSizePolicy,
)

from core.event_bus import bus
from core.telemetry_history import TelemetryHistory
from core.telemetry_model import TelemetrySnapshot
from core.telemetry_worker import TelemetryWorker
from ui.widgets.sparkline import SparklineWidget


# ==============================================================================
# Таблица стилей QSS для NOC-дашборда
# ==============================================================================

SENSORS_QSS = """
QWidget#sensors_view_root {
    background-color: #0b0e17;
}

/* Header Bar */
QFrame.noc-header-bar {
    background-color: #111625;
    border: 1px solid #1e2638;
    border-radius: 8px;
    padding: 0px 12px;
}

QLabel.header-title {
    color: #f8fafc;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel.header-badge {
    font-size: 11px;
    font-weight: 600;
    border-radius: 4px;
    padding: 2px 6px;
}

QLabel.badge-lhm-active {
    color: #4ade80;
    background-color: rgba(34, 197, 94, 0.15);
    border: 1px solid rgba(34, 197, 94, 0.35);
}

QLabel.badge-lhm-fallback {
    color: #fbbf24;
    background-color: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
}

QLabel.badge-uac-admin {
    color: #38bdf8;
    background-color: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.35);
}

QLabel.badge-uac-user {
    color: #94a3b8;
    background-color: rgba(148, 163, 184, 0.12);
    border: 1px solid rgba(148, 163, 184, 0.25);
}

QLabel.header-uptime {
    color: #94a3b8;
    font-size: 11px;
    font-family: "Consolas", "Roboto Mono", monospace;
    font-weight: 600;
}

/* Hero Cards */
QFrame.hero-card {
    background-color: #131826;
    border: 1px solid #1f293d;
    border-radius: 10px;
}

QLabel.hero-tag {
    color: #38bdf8;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

QLabel.hero-title {
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 600;
}

QLabel.hero-temp-large {
    color: #38bdf8;
    font-size: 34px;
    font-weight: 900;
    font-family: "Consolas", "Segoe UI", sans-serif;
}

QLabel.hero-temp-sub {
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}

QLabel.hero-chip-key {
    color: #64748b;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
}

QLabel.hero-chip-val {
    color: #f1f5f9;
    font-size: 12px;
    font-weight: 700;
    font-family: "Consolas", "Roboto Mono", monospace;
}

/* Lower NOC Cards */
QFrame.noc-card {
    background-color: #121724;
    border: 1px solid #1e2638;
    border-radius: 8px;
}

QLabel.noc-card-title {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel.noc-card-val-big {
    color: #f8fafc;
    font-size: 18px;
    font-weight: 800;
    font-family: "Consolas", "Segoe UI", monospace;
}

QLabel.noc-card-subtext {
    color: #64748b;
    font-size: 11px;
    font-weight: 500;
}

/* Progress Bars */
QProgressBar.noc-progress {
    background-color: #1e2638;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}

QProgressBar.noc-progress::chunk {
    background-color: #38bdf8;
    border-radius: 3px;
}

QProgressBar.noc-progress-gpu::chunk {
    background-color: #a855f7;
    border-radius: 3px;
}

QProgressBar.noc-progress-ram::chunk {
    background-color: #10b981;
    border-radius: 3px;
}
"""


def _format_uptime(seconds: int) -> str:
    """Форматирует секунды аптайма в читаемый вид (Xd Xh Xm Xs)."""
    if seconds <= 0:
        return "0s"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours:02d}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes:02d}m")
    parts.append(f"{secs:02d}s")
    return " ".join(parts)


def _format_net_speed(kbps: float) -> str:
    """Форматирует скорость сети в KB/s или MB/s."""
    if kbps >= 1024.0:
        return f"{kbps / 1024.0:.1f} MB/s"
    return f"{kbps:.0f} KB/s"


def _temp_color_hex(temp: float) -> str:
    """Возвращает HEX-цвет по температуре (<60 Cyan, 60-78 Amber, >=80 Crimson)."""
    if temp >= 80.0:
        return "#ef4444"
    if temp >= 60.0:
        return "#f59e0b"
    return "#38bdf8"


class SensorsView(QWidget):
    """
    Главный виджет дашборда аппаратной телеметрии NOC DuckDock (944x600).
    Полностью автономен, не зависит от сторонних GUI и рендерится на iGPU.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        worker: Optional[TelemetryWorker] = None,
        history: Optional[TelemetryHistory] = None,
        auto_start: bool = True,
    ):
        super().__init__(parent)
        self.setObjectName("sensors_view_root")

        # Инвариант Stealth Focus: окно и все дочерние виджеты не отбирают системный фокус
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._history = history or TelemetryHistory(maxlen=60)
        self._worker = worker
        self._owns_worker = False
        self._auto_start = auto_start

        self.setStyleSheet(SENSORS_QSS)
        self._init_ui()

        # Подключение к переданному рабочему потоку
        if self._worker is not None:
            self._worker.snapshot_ready.connect(self.update_snapshot)

        # Подписка на общую шину событий (для внешних эмиттеров и обратной совместимости)
        bus.sensors_updated.connect(self._on_bus_sensors_updated)

    def start_worker(self) -> None:
        """Запуск фонового потока телеметрии."""
        if self._worker is None:
            self._worker = TelemetryWorker(interval_ms=1000, parent=self)
            self._owns_worker = True
            self._worker.snapshot_ready.connect(self.update_snapshot)
        if not self._worker.isRunning():
            self._worker.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._auto_start:
            self.start_worker()

    @property
    def history(self) -> TelemetryHistory:
        """Менеджер истории телеметрии."""
        return self._history

    @property
    def worker(self) -> Optional[TelemetryWorker]:
        """Рабочий поток сбора телеметрии."""
        return self._worker

    # --------------------------------------------------------------------------
    # Инициализация интерфейса
    # --------------------------------------------------------------------------

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # 1. Header Bar (36px)
        header_bar = self._create_header_bar()
        root_layout.addWidget(header_bar)

        # 2. Верхний ярус (Hero Cards: CPU Master & GPU Master)
        hero_layout = QHBoxLayout()
        hero_layout.setSpacing(8)

        self.cpu_card = self._create_cpu_hero_card()
        self.gpu_card = self._create_gpu_hero_card()

        hero_layout.addWidget(self.cpu_card, 1)
        hero_layout.addWidget(self.gpu_card, 1)
        root_layout.addLayout(hero_layout, 11)

        # 3. Нижний ярус (NOC Grid: RAM, Network & Ping, NVMe, Chassis & Motherboard)
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(8)

        self.ram_card = self._create_ram_card()
        self.net_card = self._create_network_card()
        self.storage_card = self._create_storage_card()
        self.chassis_card = self._create_chassis_card()

        grid_layout.addWidget(self.ram_card, 1)
        grid_layout.addWidget(self.net_card, 1)
        grid_layout.addWidget(self.storage_card, 1)
        grid_layout.addWidget(self.chassis_card, 1)
        root_layout.addLayout(grid_layout, 9)

    # --------------------------------------------------------------------------
    # 1. Header Bar (36px)
    # --------------------------------------------------------------------------

    def _create_header_bar(self) -> QFrame:
        frame = QFrame(self)
        frame.setFixedHeight(36)
        frame.setProperty("class", "noc-header-bar")
        frame.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # LHM статус
        self.lbl_lhm_status = QLabel("● LibreHardwareMonitor (Direct Ring0)", frame)
        self.lbl_lhm_status.setProperty("class", "header-badge badge-lhm-active")
        self.lbl_lhm_status.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.lbl_lhm_status)

        # UAC статус
        self.lbl_uac_status = QLabel("[UAC: ADMIN]", frame)
        self.lbl_uac_status.setProperty("class", "header-badge badge-uac-admin")
        self.lbl_uac_status.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.lbl_uac_status)

        # Разделитель
        layout.addStretch()

        # Системный аптайм
        self.lbl_uptime = QLabel("UPTIME: --", frame)
        self.lbl_uptime.setProperty("class", "header-uptime")
        self.lbl_uptime.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.lbl_uptime)

        # Индикатор NOC Stream
        lbl_stream = QLabel("STREAM: 1000ms", frame)
        lbl_stream.setProperty("class", "header-uptime")
        lbl_stream.setStyleSheet("color: #64748b;")
        lbl_stream.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(lbl_stream)

        return frame

    # --------------------------------------------------------------------------
    # 2. Hero Card: CPU Master
    # --------------------------------------------------------------------------

    def _create_cpu_hero_card(self) -> QFrame:
        card = QFrame(self)
        card.setProperty("class", "hero-card")
        card.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Верхняя плашка: Tag + Название процессора + Ватты
        top_row = QHBoxLayout()
        lbl_tag = QLabel("CPU MASTER", card)
        lbl_tag.setProperty("class", "hero-tag")
        lbl_tag.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(lbl_tag)

        self.lbl_cpu_name = QLabel("AMD Ryzen 7 7700", card)
        self.lbl_cpu_name.setProperty("class", "hero-title")
        self.lbl_cpu_name.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(self.lbl_cpu_name)
        top_row.addStretch()

        self.lbl_cpu_power_badge = QLabel("-- W", card)
        self.lbl_cpu_power_badge.setStyleSheet(
            "color: #f59e0b; font-weight: 700; font-size: 11px; font-family: monospace;"
        )
        self.lbl_cpu_power_badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(self.lbl_cpu_power_badge)
        layout.addLayout(top_row)

        # Средний блок метрик: Крупная температура + чипы
        mid_row = QHBoxLayout()
        mid_row.setSpacing(12)

        # Левая колонка среднего блока: Температура и Load Bar
        temp_col = QVBoxLayout()
        temp_col.setSpacing(2)

        self.lbl_cpu_temp = QLabel("--.-°C", card)
        self.lbl_cpu_temp.setProperty("class", "hero-temp-large")
        self.lbl_cpu_temp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        temp_col.addWidget(self.lbl_cpu_temp)

        lbl_t_sub = QLabel("Tctl / Tdie Core", card)
        lbl_t_sub.setProperty("class", "hero-temp-sub")
        lbl_t_sub.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        temp_col.addWidget(lbl_t_sub)

        # Load Bar
        self.bar_cpu_load = QProgressBar(card)
        self.bar_cpu_load.setProperty("class", "noc-progress")
        self.bar_cpu_load.setRange(0, 100)
        self.bar_cpu_load.setValue(0)
        self.bar_cpu_load.setTextVisible(False)
        self.bar_cpu_load.setFixedHeight(6)
        self.bar_cpu_load.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        temp_col.addWidget(self.bar_cpu_load)

        mid_row.addLayout(temp_col, 5)

        # Правая колонка: Сетка чипов (Load, Clock, Cooler, Pump)
        chips_grid = QGridLayout()
        chips_grid.setHorizontalSpacing(10)
        chips_grid.setVerticalSpacing(4)

        # 1. Load %
        k1 = QLabel("LOAD", card)
        k1.setProperty("class", "hero-chip-key")
        self.val_cpu_load = QLabel("0.0%", card)
        self.val_cpu_load.setProperty("class", "hero-chip-val")
        chips_grid.addWidget(k1, 0, 0)
        chips_grid.addWidget(self.val_cpu_load, 0, 1)

        # 2. Clock
        k2 = QLabel("CLOCK", card)
        k2.setProperty("class", "hero-chip-key")
        self.val_cpu_clock = QLabel("-- GHz", card)
        self.val_cpu_clock.setProperty("class", "hero-chip-val")
        chips_grid.addWidget(k2, 0, 2)
        chips_grid.addWidget(self.val_cpu_clock, 0, 3)

        # 3. CPU Fan
        k3 = QLabel("COOLER", card)
        k3.setProperty("class", "hero-chip-key")
        self.val_cpu_fan = QLabel("-- RPM", card)
        self.val_cpu_fan.setProperty("class", "hero-chip-val")
        chips_grid.addWidget(k3, 1, 0)
        chips_grid.addWidget(self.val_cpu_fan, 1, 1)

        # 4. Pump
        k4 = QLabel("PUMP", card)
        k4.setProperty("class", "hero-chip-key")
        self.val_cpu_pump = QLabel("-- RPM", card)
        self.val_cpu_pump.setProperty("class", "hero-chip-val")
        chips_grid.addWidget(k4, 1, 2)
        chips_grid.addWidget(self.val_cpu_pump, 1, 3)

        for w in (k1, self.val_cpu_load, k2, self.val_cpu_clock, k3, self.val_cpu_fan, k4, self.val_cpu_pump):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        mid_row.addLayout(chips_grid, 6)
        layout.addLayout(mid_row)

        # Нижний блок: Живой 60-секундный Sparkline-график
        self.spark_cpu = SparklineWidget(
            parent=card,
            maxlen=60,
            min_val=30.0,
            max_val=90.0,
            warning_threshold=60.0,
            critical_threshold=80.0,
            line_width=2.0,
            fill_opacity=0.25,
            show_beacon=True,
            show_grid=True,
            auto_scale=False,
        )
        self.spark_cpu.setMinimumHeight(64)
        layout.addWidget(self.spark_cpu)

        return card

    # --------------------------------------------------------------------------
    # 3. Hero Card: GPU Master
    # --------------------------------------------------------------------------

    def _create_gpu_hero_card(self) -> QFrame:
        card = QFrame(self)
        card.setProperty("class", "hero-card")
        card.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Верхняя плашка
        top_row = QHBoxLayout()
        lbl_tag = QLabel("GPU MASTER", card)
        lbl_tag.setProperty("class", "hero-tag")
        lbl_tag.setStyleSheet("color: #a855f7;")
        lbl_tag.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(lbl_tag)

        self.lbl_gpu_name = QLabel("Discrete GPU", card)
        self.lbl_gpu_name.setProperty("class", "hero-title")
        self.lbl_gpu_name.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(self.lbl_gpu_name)
        top_row.addStretch()

        self.lbl_gpu_power_badge = QLabel("-- W", card)
        self.lbl_gpu_power_badge.setStyleSheet(
            "color: #f59e0b; font-weight: 700; font-size: 11px; font-family: monospace;"
        )
        self.lbl_gpu_power_badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(self.lbl_gpu_power_badge)
        layout.addLayout(top_row)

        # Средний блок
        mid_row = QHBoxLayout()
        mid_row.setSpacing(12)

        # Левая колонка: Крупная температура GPU + Hotspot
        temp_col = QVBoxLayout()
        temp_col.setSpacing(2)

        self.lbl_gpu_temp = QLabel("--.-°C", card)
        self.lbl_gpu_temp.setProperty("class", "hero-temp-large")
        self.lbl_gpu_temp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        temp_col.addWidget(self.lbl_gpu_temp)

        self.lbl_gpu_hotspot = QLabel("HOTSPOT: --.-°C", card)
        self.lbl_gpu_hotspot.setProperty("class", "hero-temp-sub")
        self.lbl_gpu_hotspot.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        temp_col.addWidget(self.lbl_gpu_hotspot)

        # VRAM Bar
        self.bar_gpu_vram = QProgressBar(card)
        self.bar_gpu_vram.setProperty("class", "noc-progress noc-progress-gpu")
        self.bar_gpu_vram.setRange(0, 100)
        self.bar_gpu_vram.setValue(0)
        self.bar_gpu_vram.setTextVisible(False)
        self.bar_gpu_vram.setFixedHeight(6)
        self.bar_gpu_vram.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        temp_col.addWidget(self.bar_gpu_vram)

        mid_row.addLayout(temp_col, 5)

        # Правая колонка: Чипы (Load %, VRAM GB, Fan RPM, Power)
        chips_grid = QGridLayout()
        chips_grid.setHorizontalSpacing(10)
        chips_grid.setVerticalSpacing(4)

        k1 = QLabel("LOAD", card)
        k1.setProperty("class", "hero-chip-key")
        self.val_gpu_load = QLabel("0.0%", card)
        self.val_gpu_load.setProperty("class", "hero-chip-val")
        chips_grid.addWidget(k1, 0, 0)
        chips_grid.addWidget(self.val_gpu_load, 0, 1)

        k2 = QLabel("VRAM", card)
        k2.setProperty("class", "hero-chip-key")
        self.val_gpu_vram = QLabel("-- / -- GB", card)
        self.val_gpu_vram.setProperty("class", "hero-chip-val")
        chips_grid.addWidget(k2, 0, 2)
        chips_grid.addWidget(self.val_gpu_vram, 0, 3)

        k3 = QLabel("FANS", card)
        k3.setProperty("class", "hero-chip-key")
        self.val_gpu_fan = QLabel("-- RPM", card)
        self.val_gpu_fan.setProperty("class", "hero-chip-val")
        chips_grid.addWidget(k3, 1, 0)
        chips_grid.addWidget(self.val_gpu_fan, 1, 1)

        k4 = QLabel("POWER", card)
        k4.setProperty("class", "hero-chip-key")
        self.val_gpu_power = QLabel("-- W", card)
        self.val_gpu_power.setProperty("class", "hero-chip-val")
        chips_grid.addWidget(k4, 1, 2)
        chips_grid.addWidget(self.val_gpu_power, 1, 3)

        for w in (k1, self.val_gpu_load, k2, self.val_gpu_vram, k3, self.val_gpu_fan, k4, self.val_gpu_power):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        mid_row.addLayout(chips_grid, 6)
        layout.addLayout(mid_row)

        # Sparkline
        self.spark_gpu = SparklineWidget(
            parent=card,
            maxlen=60,
            min_val=30.0,
            max_val=90.0,
            warning_threshold=65.0,
            critical_threshold=82.0,
            line_width=2.0,
            fill_opacity=0.25,
            show_beacon=True,
            show_grid=True,
            auto_scale=False,
        )
        self.spark_gpu.setMinimumHeight(64)
        layout.addWidget(self.spark_gpu)

        return card

    # --------------------------------------------------------------------------
    # 4. NOC Grid: RAM Card
    # --------------------------------------------------------------------------

    def _create_ram_card(self) -> QFrame:
        card = QFrame(self)
        card.setProperty("class", "noc-card")
        card.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        t_row = QHBoxLayout()
        lbl_title = QLabel("RAM DDR5", card)
        lbl_title.setProperty("class", "noc-card-title")
        lbl_title.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_row.addWidget(lbl_title)
        t_row.addStretch()

        self.lbl_ram_pct = QLabel("0%", card)
        self.lbl_ram_pct.setStyleSheet("color: #10b981; font-weight: 700; font-size: 11px;")
        self.lbl_ram_pct.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_row.addWidget(self.lbl_ram_pct)
        layout.addLayout(t_row)

        self.val_ram_gb = QLabel("-- / -- GB", card)
        self.val_ram_gb.setProperty("class", "noc-card-val-big")
        self.val_ram_gb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.val_ram_gb)

        self.bar_ram = QProgressBar(card)
        self.bar_ram.setProperty("class", "noc-progress noc-progress-ram")
        self.bar_ram.setRange(0, 100)
        self.bar_ram.setValue(0)
        self.bar_ram.setTextVisible(False)
        self.bar_ram.setFixedHeight(5)
        self.bar_ram.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.bar_ram)

        self.spark_ram = SparklineWidget(
            parent=card,
            maxlen=60,
            min_val=0.0,
            max_val=100.0,
            fixed_color="#10b981",
            line_width=1.5,
            fill_opacity=0.2,
            show_beacon=False,
            show_grid=False,
            auto_scale=False,
        )
        self.spark_ram.setMinimumHeight(38)
        layout.addWidget(self.spark_ram)

        lbl_sub = QLabel("High-Speed Channel", card)
        lbl_sub.setProperty("class", "noc-card-subtext")
        lbl_sub.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(lbl_sub)

        return card

    # --------------------------------------------------------------------------
    # 5. NOC Grid: Network Traffic & Ping
    # --------------------------------------------------------------------------

    def _create_network_card(self) -> QFrame:
        card = QFrame(self)
        card.setProperty("class", "noc-card")
        card.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        t_row = QHBoxLayout()
        lbl_title = QLabel("NETWORK & PING", card)
        lbl_title.setProperty("class", "noc-card-title")
        lbl_title.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_row.addWidget(lbl_title)
        t_row.addStretch()

        self.lbl_net_ping = QLabel("● -- ms", card)
        self.lbl_net_ping.setStyleSheet("color: #22c55e; font-weight: 700; font-size: 11px;")
        self.lbl_net_ping.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_row.addWidget(self.lbl_net_ping)
        layout.addLayout(t_row)

        self.val_net_rx = QLabel("↓ 0.0 KB/s", card)
        self.val_net_rx.setProperty("class", "noc-card-val-big")
        self.val_net_rx.setStyleSheet("color: #38bdf8;")
        self.val_net_rx.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.val_net_rx)

        self.val_net_tx = QLabel("↑ 0.0 KB/s", card)
        self.val_net_tx.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; font-family: monospace;")
        self.val_net_tx.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.val_net_tx)

        self.spark_net = SparklineWidget(
            parent=card,
            maxlen=60,
            fixed_color="#38bdf8",
            line_width=1.5,
            fill_opacity=0.2,
            show_beacon=False,
            show_grid=False,
            auto_scale=True,
        )
        self.spark_net.setMinimumHeight(38)
        layout.addWidget(self.spark_net)

        lbl_sub = QLabel("DNS 1.1.1.1 Gateway", card)
        lbl_sub.setProperty("class", "noc-card-subtext")
        lbl_sub.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(lbl_sub)

        return card

    # --------------------------------------------------------------------------
    # 6. NOC Grid: NVMe Storage
    # --------------------------------------------------------------------------

    def _create_storage_card(self) -> QFrame:
        card = QFrame(self)
        card.setProperty("class", "noc-card")
        card.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        t_row = QHBoxLayout()
        lbl_title = QLabel("NVME STORAGE", card)
        lbl_title.setProperty("class", "noc-card-title")
        lbl_title.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_row.addWidget(lbl_title)
        t_row.addStretch()

        self.lbl_storage_temp = QLabel("--°C", card)
        self.lbl_storage_temp.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px;")
        self.lbl_storage_temp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_row.addWidget(self.lbl_storage_temp)
        layout.addLayout(t_row)

        self.val_storage_name = QLabel("NVMe SSD", card)
        self.val_storage_name.setProperty("class", "noc-card-val-big")
        self.val_storage_name.setStyleSheet("font-size: 14px; color: #f1f5f9;")
        self.val_storage_name.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.val_storage_name)

        act_row = QHBoxLayout()
        lbl_act = QLabel("ACTIVITY", card)
        lbl_act.setProperty("class", "hero-chip-key")
        self.val_storage_act = QLabel("0%", card)
        self.val_storage_act.setProperty("class", "hero-chip-val")
        act_row.addWidget(lbl_act)
        act_row.addStretch()
        act_row.addWidget(self.val_storage_act)
        layout.addLayout(act_row)

        self.bar_storage = QProgressBar(card)
        self.bar_storage.setProperty("class", "noc-progress")
        self.bar_storage.setRange(0, 100)
        self.bar_storage.setValue(0)
        self.bar_storage.setTextVisible(False)
        self.bar_storage.setFixedHeight(5)
        self.bar_storage.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.bar_storage)

        self.spark_storage = SparklineWidget(
            parent=card,
            maxlen=60,
            min_val=20.0,
            max_val=80.0,
            fixed_color="#f59e0b",
            line_width=1.5,
            fill_opacity=0.2,
            show_beacon=False,
            show_grid=False,
            auto_scale=False,
        )
        self.spark_storage.setMinimumHeight(38)
        layout.addWidget(self.spark_storage)

        lbl_sub = QLabel("PCIe Gen4 Direct IO", card)
        lbl_sub.setProperty("class", "noc-card-subtext")
        lbl_sub.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(lbl_sub)

        return card

    # --------------------------------------------------------------------------
    # 7. NOC Grid: Chassis & Motherboard
    # --------------------------------------------------------------------------

    def _create_chassis_card(self) -> QFrame:
        card = QFrame(self)
        card.setProperty("class", "noc-card")
        card.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        t_row = QHBoxLayout()
        lbl_title = QLabel("CHASSIS & MB", card)
        lbl_title.setProperty("class", "noc-card-title")
        lbl_title.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_row.addWidget(lbl_title)
        t_row.addStretch()

        self.lbl_vrm_temp = QLabel("VRM: --°C", card)
        self.lbl_vrm_temp.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 11px;")
        self.lbl_vrm_temp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t_row.addWidget(self.lbl_vrm_temp)
        layout.addLayout(t_row)

        self.val_chassis_fans = QLabel("FAN: -- RPM", card)
        self.val_chassis_fans.setProperty("class", "noc-card-val-big")
        self.val_chassis_fans.setStyleSheet("font-size: 15px; color: #f8fafc;")
        self.val_chassis_fans.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.val_chassis_fans)

        self.val_chassis_subfans = QLabel("Chassis Coolers Active", card)
        self.val_chassis_subfans.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        self.val_chassis_subfans.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.val_chassis_subfans)

        layout.addStretch()

        self.lbl_cooling_status = QLabel("● OPTIMAL AIRFLOW", card)
        self.lbl_cooling_status.setStyleSheet(
            "color: #10b981; font-weight: 800; font-size: 10px; letter-spacing: 0.5px;"
        )
        self.lbl_cooling_status.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.lbl_cooling_status)

        lbl_sub = QLabel("Super I/O Hardware Bus", card)
        lbl_sub.setProperty("class", "noc-card-subtext")
        lbl_sub.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(lbl_sub)

        return card

    # --------------------------------------------------------------------------
    # Обработка и приём телеметрии
    # --------------------------------------------------------------------------

    @Slot(object)
    def update_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        """
        Основной метод обновления UI по снимку TelemetrySnapshot.
        Выполняется в GUI-потоке PySide6 через Qt сигнал-слот.
        """
        if not isinstance(snapshot, TelemetrySnapshot):
            return

        # Запись в кольцевой буфер истории
        self._history.add_snapshot(snapshot)

        # 1. Header Bar
        if snapshot.is_lhm_active:
            self.lbl_lhm_status.setText("● LibreHardwareMonitor (Direct Ring0)")
            self.lbl_lhm_status.setProperty("class", "header-badge badge-lhm-active")
        else:
            self.lbl_lhm_status.setText("● Hardware Telemetry (OS Fallback)")
            self.lbl_lhm_status.setProperty("class", "header-badge badge-lhm-fallback")
        self.lbl_lhm_status.style().unpolish(self.lbl_lhm_status)
        self.lbl_lhm_status.style().polish(self.lbl_lhm_status)

        if snapshot.is_admin:
            self.lbl_uac_status.setText("[UAC: ADMIN]")
            self.lbl_uac_status.setProperty("class", "header-badge badge-uac-admin")
        else:
            self.lbl_uac_status.setText("[UAC: USER]")
            self.lbl_uac_status.setProperty("class", "header-badge badge-uac-user")
        self.lbl_uac_status.style().unpolish(self.lbl_uac_status)
        self.lbl_uac_status.style().polish(self.lbl_uac_status)

        self.lbl_uptime.setText(f"UPTIME: {_format_uptime(snapshot.uptime_seconds)}")

        # 2. CPU Master
        if snapshot.cpu_name:
            self.lbl_cpu_name.setText(snapshot.cpu_name)
        if snapshot.cpu_power > 0:
            self.lbl_cpu_power_badge.setText(f"{snapshot.cpu_power:.1f} W")
        else:
            self.lbl_cpu_power_badge.setText("-- W")

        cpu_temp = snapshot.cpu_temp
        if cpu_temp > 0:
            self.lbl_cpu_temp.setText(f"{cpu_temp:.1f}°C")
            self.lbl_cpu_temp.setStyleSheet(f"color: {_temp_color_hex(cpu_temp)};")
            self.spark_cpu.add_value(cpu_temp)
        else:
            self.lbl_cpu_temp.setText("--.-°C")

        self.val_cpu_load.setText(f"{snapshot.cpu_load:.1f}%")
        self.bar_cpu_load.setValue(int(min(100.0, max(0.0, snapshot.cpu_load))))

        if snapshot.cpu_clock > 0:
            if snapshot.cpu_clock >= 1000.0:
                self.val_cpu_clock.setText(f"{snapshot.cpu_clock / 1000.0:.2f} GHz")
            else:
                self.val_cpu_clock.setText(f"{snapshot.cpu_clock:.0f} MHz")
        else:
            self.val_cpu_clock.setText("-- GHz")

        if snapshot.cpu_fan_rpm > 0:
            self.val_cpu_fan.setText(f"{snapshot.cpu_fan_rpm} RPM")
        else:
            self.val_cpu_fan.setText("-- RPM")

        if snapshot.pump_rpm > 0:
            self.val_cpu_pump.setText(f"{snapshot.pump_rpm} RPM")
        else:
            self.val_cpu_pump.setText("-- RPM")

        # 3. GPU Master
        if snapshot.gpu_name:
            self.lbl_gpu_name.setText(snapshot.gpu_name)
        if snapshot.gpu_power > 0:
            self.lbl_gpu_power_badge.setText(f"{snapshot.gpu_power:.1f} W")
            self.val_gpu_power.setText(f"{snapshot.gpu_power:.0f} W")
        else:
            self.lbl_gpu_power_badge.setText("-- W")
            self.val_gpu_power.setText("-- W")

        gpu_temp = snapshot.gpu_temp
        if gpu_temp > 0:
            self.lbl_gpu_temp.setText(f"{gpu_temp:.1f}°C")
            self.lbl_gpu_temp.setStyleSheet(f"color: {_temp_color_hex(gpu_temp)};")
            self.spark_gpu.add_value(gpu_temp)
        else:
            self.lbl_gpu_temp.setText("--.-°C")

        if snapshot.gpu_hotspot > 0:
            self.lbl_gpu_hotspot.setText(f"HOTSPOT: {snapshot.gpu_hotspot:.1f}°C")
            if snapshot.gpu_hotspot >= 85.0:
                self.lbl_gpu_hotspot.setStyleSheet("color: #ef4444; font-weight: 700;")
            elif snapshot.gpu_hotspot >= 75.0:
                self.lbl_gpu_hotspot.setStyleSheet("color: #f59e0b; font-weight: 700;")
            else:
                self.lbl_gpu_hotspot.setStyleSheet("color: #64748b; font-weight: 600;")
        else:
            self.lbl_gpu_hotspot.setText("HOTSPOT: --.-°C")

        self.val_gpu_load.setText(f"{snapshot.gpu_load:.1f}%")

        if snapshot.gpu_vram_total > 0:
            used_gb = snapshot.gpu_vram_used / 1024.0
            tot_gb = snapshot.gpu_vram_total / 1024.0
            pct = snapshot.vram_percent
            self.val_gpu_vram.setText(f"{used_gb:.1f} / {tot_gb:.1f} GB")
            self.bar_gpu_vram.setValue(int(min(100.0, max(0.0, pct))))
        else:
            self.val_gpu_vram.setText("-- / -- GB")
            self.bar_gpu_vram.setValue(0)

        if snapshot.gpu_fan_rpm > 0:
            self.val_gpu_fan.setText(f"{snapshot.gpu_fan_rpm} RPM")
        else:
            self.val_gpu_fan.setText("-- RPM")

        # 4. RAM
        if snapshot.ram_total_gb > 0:
            self.val_ram_gb.setText(f"{snapshot.ram_used_gb:.1f} / {snapshot.ram_total_gb:.1f} GB")
        else:
            self.val_ram_gb.setText("-- / -- GB")
        ram_pct = int(min(100.0, max(0.0, snapshot.ram_load_pct)))
        self.lbl_ram_pct.setText(f"{ram_pct}%")
        self.bar_ram.setValue(ram_pct)
        self.spark_ram.add_value(snapshot.ram_load_pct)

        # 5. Network & Ping
        if snapshot.ping_ms >= 0:
            self.lbl_net_ping.setText(f"● {snapshot.ping_ms:.0f} ms")
            if snapshot.ping_ms < 50:
                self.lbl_net_ping.setStyleSheet("color: #22c55e; font-weight: 700; font-size: 11px;")
            elif snapshot.ping_ms < 100:
                self.lbl_net_ping.setStyleSheet("color: #f59e0b; font-weight: 700; font-size: 11px;")
            else:
                self.lbl_net_ping.setStyleSheet("color: #ef4444; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_net_ping.setText("● DISCONNECTED")
            self.lbl_net_ping.setStyleSheet("color: #ef4444; font-weight: 700; font-size: 11px;")

        self.val_net_rx.setText(f"↓ {_format_net_speed(snapshot.net_rx_kbps)}")
        self.val_net_tx.setText(f"↑ {_format_net_speed(snapshot.net_tx_kbps)}")
        self.spark_net.add_value(snapshot.net_rx_kbps / 1024.0)

        # 6. NVMe Storage
        if snapshot.storage_name:
            self.val_storage_name.setText(snapshot.storage_name[:24])
        if snapshot.storage_temp > 0:
            self.lbl_storage_temp.setText(f"{snapshot.storage_temp:.0f}°C")
            self.lbl_storage_temp.setStyleSheet(f"color: {_temp_color_hex(snapshot.storage_temp)};")
            self.spark_storage.add_value(snapshot.storage_temp)
        else:
            self.lbl_storage_temp.setText("--°C")
        st_act = int(min(100.0, max(0.0, snapshot.storage_activity)))
        self.val_storage_act.setText(f"{st_act}%")
        self.bar_storage.setValue(st_act)

        # 7. Chassis & Motherboard
        if snapshot.vrm_temp > 0:
            self.lbl_vrm_temp.setText(f"VRM: {snapshot.vrm_temp:.0f}°C")
        else:
            self.lbl_vrm_temp.setText("VRM: --°C")

        if snapshot.chassis_fans_rpm:
            max_fan = max(snapshot.chassis_fans_rpm)
            self.val_chassis_fans.setText(f"FAN: {max_fan} RPM")
            fan_chips = ", ".join(f"{rpm}" for rpm in snapshot.chassis_fans_rpm[:3])
            self.val_chassis_subfans.setText(f"Fans: {fan_chips} RPM")
        elif snapshot.cpu_fan_rpm > 0:
            self.val_chassis_fans.setText(f"FAN: {snapshot.cpu_fan_rpm} RPM")
            self.val_chassis_subfans.setText("CPU Fan Active")
        else:
            self.val_chassis_fans.setText("FAN: -- RPM")
            self.val_chassis_subfans.setText("Passive Cooling")

    @Slot(dict)
    def _on_bus_sensors_updated(self, data: dict) -> None:
        """Слот приёма данных из шины EventBus (словарь)."""
        if not isinstance(data, dict):
            return
        snapshot = TelemetrySnapshot.from_dict(data)
        self.update_snapshot(snapshot)

    def refresh_sensors(self) -> None:
        """
        Метод ручного обновления (для обратной совместимости со старым интерфейсом AIDA64).
        """
        if self._worker and self._worker.last_snapshot:
            self.update_snapshot(self._worker.last_snapshot)

    def cleanup(self) -> None:
        """
        Безопасная остановка фонового сборщика при закрытии приложения.
        """
        if self._owns_worker and self._worker is not None:
            try:
                self._worker.stop(timeout_ms=1000)
            except Exception:
                pass
            self._worker = None

    def close(self):
        self.cleanup()
        return super().close()

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)
