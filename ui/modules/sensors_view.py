"""
Виджет отображения аппаратной телеметрии (AIDA64 / psutil) для экрана 720x600.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QProgressBar
)
from PySide6.QtCore import Qt, QTimer
from core.aida_reader import AidaReader
from core.event_bus import bus

SENSORS_QSS = """
QFrame.sensor-card {
    background-color: #161b26;
    border: 1px solid #232b3e;
    border-radius: 12px;
    padding: 12px;
}

QLabel.card-title {
    color: #64748b;
    font-size: 13px;
    font-weight: bold;
    text-transform: uppercase;
}

QLabel.card-value {
    color: #38bdf8;
    font-size: 32px;
    font-weight: bold;
}

QLabel.card-subtext {
    color: #94a3b8;
    font-size: 12px;
}

QProgressBar {
    background-color: #1e293b;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 4px;
}
"""

class SensorsView(QWidget):
    """Экран телеметрии процессора, видеокарты и памяти."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reader = AidaReader()
        self.setStyleSheet(SENSORS_QSS)

        self._init_ui()

        # Таймер обновления датчиков раз в секунду
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_sensors)
        self.timer.start(1000)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Заголовок секции
        header_layout = QHBoxLayout()
        title = QLabel("АППАРАТНАЯ ТЕЛЕМЕТРИЯ (7\" DASHBOARD)")
        title.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)

        self.lbl_status = QLabel("● Live")
        self.lbl_status.setStyleSheet("color: #22c55e; font-size: 12px; font-weight: bold;")
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_status)
        main_layout.addLayout(header_layout)

        # Сетка карточек датчиков (2x2)
        grid = QGridLayout()
        grid.setSpacing(12)

        # 1. CPU Температура
        self.card_cpu, self.val_cpu, self.sub_cpu, self.bar_cpu = self._create_sensor_card(
            "CPU TEMPERATURE", "48°C", "AMD Ryzen 7 7700 (iGPU)", 48
        )
        grid.addWidget(self.card_cpu, 0, 0)

        # 2. CPU / iGPU Загрузка
        self.card_load, self.val_load, self.sub_load, self.bar_load = self._create_sensor_card(
            "CPU USAGE", "15%", "8 Cores / 16 Threads", 15
        )
        grid.addWidget(self.card_load, 0, 1)

        # 3. GPU Температура (dGPU)
        self.card_gpu, self.val_gpu, self.sub_gpu, self.bar_gpu = self._create_sensor_card(
            "GPU TEMPERATURE", "52°C", "Primary Discrete GPU", 52
        )
        grid.addWidget(self.card_gpu, 1, 0)

        # 4. RAM Использование
        self.card_ram, self.val_ram, self.sub_ram, self.bar_ram = self._create_sensor_card(
            "RAM USAGE", "42%", "DDR5 High Speed", 42
        )
        grid.addWidget(self.card_ram, 1, 1)

        main_layout.addLayout(grid)
        main_layout.addStretch()

    def _create_sensor_card(self, title: str, value: str, subtext: str, bar_val: int):
        card = QFrame()
        card.setProperty("class", "sensor-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "card-title")
        layout.addWidget(lbl_title)

        lbl_val = QLabel(value)
        lbl_val.setProperty("class", "card-value")
        layout.addWidget(lbl_val)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(bar_val)
        bar.setTextVisible(False)
        layout.addWidget(bar)

        lbl_sub = QLabel(subtext)
        lbl_sub.setProperty("class", "card-subtext")
        layout.addWidget(lbl_sub)

        return card, lbl_val, lbl_sub, bar

    def refresh_sensors(self):
        data = self.reader.read_sensors()

        # CPU Temp
        cpu_temp = data.get("PCPUTEMP", data.get("TCPU", "48"))
        try:
            val_int = int(float(cpu_temp))
            self.val_cpu.setText(f"{val_int}°C")
            self.bar_cpu.setValue(val_int)
        except Exception:
            pass

        # CPU Usage
        cpu_load = data.get("TCPU", "15")
        try:
            val_int = int(float(cpu_load))
            self.val_load.setText(f"{val_int}%")
            self.bar_load.setValue(val_int)
        except Exception:
            pass

        # GPU Temp
        gpu_temp = data.get("TGPU1", "52")
        try:
            val_int = int(float(gpu_temp))
            self.val_gpu.setText(f"{val_int}°C")
            self.bar_gpu.setValue(val_int)
        except Exception:
            pass

        # RAM Usage
        ram_usage = data.get("SMEMUSAGE", "40")
        try:
            val_int = int(float(ram_usage))
            self.val_ram.setText(f"{val_int}%")
            self.bar_ram.setValue(val_int)
        except Exception:
            pass

        bus.sensors_updated.emit(data)
