"""
Строго типизированная модель аппаратной телеметрии (TelemetrySnapshot).
Используется как единый контракт данных между HardwareMonitor, TelemetryWorker,
историческим буфером и пользовательским интерфейсом дашборда 944x600.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List
import time


@dataclass
class TelemetrySnapshot:
    """
    Снимок аппаратной телеметрии ПК.
    Все числовые метрики строго типизированы и нормализованы.
    """
    # CPU
    cpu_name: str = ""
    cpu_temp: float = 0.0          # °C (Core Tctl/Tdie или Package)
    cpu_load: float = 0.0          # % (0.0 - 100.0)
    cpu_clock: float = 0.0         # MHz
    cpu_power: float = 0.0         # W (Package Power)

    # GPU (Discrete / Primary GPU)
    gpu_name: str = ""
    gpu_temp: float = 0.0          # °C (Core Temperature)
    gpu_hotspot: float = 0.0       # °C (Hot Spot Temperature)
    gpu_load: float = 0.0          # % (0.0 - 100.0)
    gpu_vram_used: float = 0.0     # MB
    gpu_vram_total: float = 0.0    # MB
    gpu_power: float = 0.0         # W
    gpu_fan_rpm: int = 0           # RPM

    # RAM
    ram_used_gb: float = 0.0       # GB
    ram_total_gb: float = 0.0      # GB
    ram_load_pct: float = 0.0      # % (0.0 - 100.0)

    # Storage (NVMe / SSD)
    storage_name: str = ""
    storage_temp: float = 0.0      # °C
    storage_activity: float = 0.0  # % (0.0 - 100.0)

    # Motherboard & Cooling
    chassis_fans_rpm: List[int] = field(default_factory=list)
    cpu_fan_rpm: int = 0           # RPM
    pump_rpm: int = 0              # RPM
    vrm_temp: float = 0.0          # °C

    # Network & Latency
    net_rx_kbps: float = 0.0       # KB/s
    net_tx_kbps: float = 0.0       # KB/s
    ping_ms: float = -1.0          # ms (-1.0 если недоступен)

    # System Status & Metadata
    uptime_seconds: int = 0        # Секунды с момента старта ОС
    is_lhm_active: bool = False    # True, если телеметрия собрана через LibreHardwareMonitor Ring 0
    is_admin: bool = False         # True, если процесс запущен с правами Администратора (UAC)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация снимка в плоский словарь для EventBus / JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetrySnapshot":
        """Создание снимка из словаря с фильтрацией неизвестных полей."""
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    @property
    def vram_percent(self) -> float:
        """Процент использования видеопамяти."""
        if self.gpu_vram_total > 0:
            return round((self.gpu_vram_used / self.gpu_vram_total) * 100.0, 1)
        return 0.0
