"""
Буфер истории метрик телеметрии (RingBuffer) для дашборда DuckDock.
Обеспечивает хранение 60-секундного скользящего окна данных для Sparkline-графиков
без утечек памяти и с минимальной нагрузкой на CPU.
"""
from collections import deque
from typing import Dict, List, Optional, Union, Any
from core.telemetry_model import TelemetrySnapshot


class RingBuffer:
    """
    Кольцевой буфер фиксированного размера на базе collections.deque.
    Гарантирует O(1) добавление и константный объем памяти.
    """
    def __init__(self, maxlen: int = 60, default_value: Optional[float] = None):
        self._maxlen = max(1, maxlen)
        self._data: deque = deque(maxlen=self._maxlen)
        if default_value is not None:
            for _ in range(self._maxlen):
                self._data.append(default_value)

    def append(self, value: float) -> None:
        """Добавление значения в буфер."""
        try:
            val = float(value)
        except (ValueError, TypeError):
            val = 0.0
        self._data.append(val)

    def to_list(self) -> List[float]:
        """Возвращает текущую последовательность значений в виде списка."""
        return list(self._data)

    def latest(self) -> float:
        """Последнее добавленное значение."""
        return self._data[-1] if self._data else 0.0

    def min_val(self) -> float:
        """Минимальное значение в буфере."""
        return min(self._data) if self._data else 0.0

    def max_val(self) -> float:
        """Максимальное значение в буфере."""
        return max(self._data) if self._data else 0.0

    def avg_val(self) -> float:
        """Среднее значение в буфере."""
        if not self._data:
            return 0.0
        return sum(self._data) / len(self._data)

    def clear(self) -> None:
        """Очистить буфер."""
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, index: int) -> float:
        return self._data[index]


class TelemetryHistory:
    """
    Менеджер кольцевых буферов для ключевых метрик телеметрии.
    Хранит 60-секундную историю для Sparkline-графиков UI.
    """
    TRACKED_METRICS = (
        "cpu_temp",
        "cpu_load",
        "cpu_power",
        "gpu_temp",
        "gpu_hotspot",
        "gpu_load",
        "gpu_power",
        "ram_load_pct",
        "net_rx_kbps",
        "net_tx_kbps",
        "ping_ms",
    )

    def __init__(self, maxlen: int = 60):
        self._maxlen = maxlen
        self._buffers: Dict[str, RingBuffer] = {
            metric: RingBuffer(maxlen=maxlen) for metric in self.TRACKED_METRICS
        }

    def add_snapshot(self, snapshot: Union[TelemetrySnapshot, Dict[str, Any]]) -> None:
        """
        Добавляет метрики из снимка в соответствующие кольцевые буферы.
        Поддерживает как объект TelemetrySnapshot, так и dict.
        """
        if isinstance(snapshot, TelemetrySnapshot):
            data = snapshot.to_dict()
        elif isinstance(snapshot, dict):
            data = snapshot
        else:
            return

        for metric in self.TRACKED_METRICS:
            if metric in data:
                val = data[metric]
                # Игнорируем некорректный ping при расчете графиков
                if metric == "ping_ms" and val < 0:
                    val = 0.0
                self._buffers[metric].append(val)

    def get_series(self, metric: str) -> List[float]:
        """Возвращает временной ряд для указанной метрики."""
        buffer = self._buffers.get(metric)
        if buffer is not None:
            return buffer.to_list()
        return []

    def get_buffer(self, metric: str) -> Optional[RingBuffer]:
        """Возвращает прямой доступ к объекту RingBuffer."""
        return self._buffers.get(metric)

    def get_summary(self, metric: str) -> Dict[str, float]:
        """
        Возвращает статистику по метрике:
        {'current': float, 'min': float, 'max': float, 'avg': float}
        """
        buf = self._buffers.get(metric)
        if not buf or len(buf) == 0:
            return {"current": 0.0, "min": 0.0, "max": 0.0, "avg": 0.0}

        return {
            "current": round(buf.latest(), 2),
            "min": round(buf.min_val(), 2),
            "max": round(buf.max_val(), 2),
            "avg": round(buf.avg_val(), 2),
        }

    def clear(self) -> None:
        """Сброс всех буферов."""
        for buf in self._buffers.values():
            buf.clear()
