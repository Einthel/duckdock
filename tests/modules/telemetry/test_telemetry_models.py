"""
Модульные тесты для структур данных телеметрии (TelemetrySnapshot, RingBuffer, TelemetryHistory).
"""
import time
import pytest

from modules.telemetry.models import TelemetrySnapshot
from modules.telemetry.history import RingBuffer, TelemetryHistory


# =============================================================================
# 1. Тестирование модели TelemetrySnapshot
# =============================================================================

@pytest.mark.unit
def test_telemetry_snapshot_default_values():
    """Проверка значений по умолчанию модели TelemetrySnapshot."""
    snap = TelemetrySnapshot()

    assert snap.cpu_name == ""
    assert snap.cpu_temp == 0.0
    assert snap.cpu_load == 0.0
    assert snap.cpu_clock == 0.0
    assert snap.cpu_power == 0.0

    assert snap.gpu_name == ""
    assert snap.gpu_temp == 0.0
    assert snap.gpu_hotspot == 0.0
    assert snap.gpu_load == 0.0
    assert snap.gpu_vram_used == 0.0
    assert snap.gpu_vram_total == 0.0
    assert snap.gpu_power == 0.0
    assert snap.gpu_fan_rpm == 0

    assert snap.ram_used_gb == 0.0
    assert snap.ram_total_gb == 0.0
    assert snap.ram_load_pct == 0.0

    assert snap.storage_name == ""
    assert snap.storage_temp == 0.0
    assert snap.storage_activity == 0.0

    assert snap.chassis_fans_rpm == []
    assert snap.cpu_fan_rpm == 0
    assert snap.pump_rpm == 0
    assert snap.vrm_temp == 0.0

    assert snap.net_rx_kbps == 0.0
    assert snap.net_tx_kbps == 0.0
    assert snap.ping_ms == -1.0

    assert snap.uptime_seconds == 0
    assert snap.is_lhm_active is False
    assert snap.is_admin is False
    assert snap.timestamp > 0.0


@pytest.mark.unit
def test_telemetry_snapshot_to_and_from_dict():
    """Проверка сериализации в dict и десериализации из dict."""
    snap = TelemetrySnapshot(
        cpu_name="AMD Ryzen 7 7700",
        cpu_temp=48.5,
        cpu_load=35.0,
        gpu_name="NVIDIA GeForce RTX 3080",
        gpu_temp=58.2,
        gpu_hotspot=65.0,
        gpu_vram_used=4096.0,
        gpu_vram_total=12288.0,
        ram_used_gb=18.5,
        ram_total_gb=32.0,
        ping_ms=15.2,
        is_lhm_active=True,
        is_admin=True,
    )

    data = snap.to_dict()
    assert isinstance(data, dict)
    assert data["cpu_name"] == "AMD Ryzen 7 7700"
    assert data["cpu_temp"] == 48.5
    assert data["gpu_temp"] == 58.2
    assert data["is_lhm_active"] is True
    assert data["is_admin"] is True

    # Добавляем неизвестные поля для проверки фильтрации
    data["unknown_legacy_field"] = "unexpected"
    restored = TelemetrySnapshot.from_dict(data)

    assert restored.cpu_name == "AMD Ryzen 7 7700"
    assert restored.cpu_temp == 48.5
    assert restored.gpu_temp == 58.2
    assert restored.gpu_vram_used == 4096.0
    assert not hasattr(restored, "unknown_legacy_field")


@pytest.mark.unit
def test_telemetry_snapshot_vram_percent():
    """Проверка вычисления процента видеопамяти."""
    snap = TelemetrySnapshot(gpu_vram_used=3072.0, gpu_vram_total=12288.0)
    assert snap.vram_percent == 25.0

    # Проверка деления на ноль при отсутствии dGPU
    snap_zero = TelemetrySnapshot(gpu_vram_used=0.0, gpu_vram_total=0.0)
    assert snap_zero.vram_percent == 0.0


# =============================================================================
# 2. Тестирование кольцевого буфера RingBuffer
# =============================================================================

@pytest.mark.unit
def test_ring_buffer_basics():
    """Базовые операции добавления, ограничения емкости и получения данных."""
    buf = RingBuffer(maxlen=3)
    assert len(buf) == 0
    assert buf.to_list() == []
    assert buf.latest() == 0.0

    buf.append(10.0)
    buf.append(20.0)
    assert len(buf) == 2
    assert buf.to_list() == [10.0, 20.0]
    assert buf.latest() == 20.0
    assert buf.min_val() == 10.0
    assert buf.max_val() == 20.0
    assert buf.avg_val() == 15.0

    # Переполнение кольцевого буфера
    buf.append(30.0)
    buf.append(40.0)
    assert len(buf) == 3
    assert buf.to_list() == [20.0, 30.0, 40.0]
    assert buf.latest() == 40.0
    assert buf.min_val() == 20.0
    assert buf.max_val() == 40.0
    assert buf.avg_val() == 30.0

    # Очистка
    buf.clear()
    assert len(buf) == 0
    assert buf.latest() == 0.0
    assert buf.min_val() == 0.0
    assert buf.avg_val() == 0.0


@pytest.mark.unit
def test_ring_buffer_invalid_values():
    """Обработка некорректных типов данных без исключений."""
    buf = RingBuffer(maxlen=5)
    buf.append("invalid")
    buf.append(None)
    buf.append(42)

    assert len(buf) == 3
    assert buf.to_list() == [0.0, 0.0, 42.0]


@pytest.mark.unit
def test_ring_buffer_memory_stability_and_no_leak():
    """
    Проверка буфера RingBuffer на отсутствие утечек памяти и строгую фиксацию maxlen.
    При 100 000 добавлениях размер очереди остается ровно maxlen, исключая неконтролируемый рост.
    """
    buf = RingBuffer(maxlen=60)

    for i in range(100_000):
        buf.append(float(i % 100))

    # Длина строго ограничена maxlen
    assert len(buf) == 60
    assert len(buf.to_list()) == 60

    # Проверка корректности последних 60 значений
    expected_last_60 = [float(i % 100) for i in range(100_000 - 60, 100_000)]
    assert buf.to_list() == expected_last_60
    assert buf.latest() == expected_last_60[-1]


# =============================================================================
# 3. Тестирование агрегатора TelemetryHistory
# =============================================================================

@pytest.mark.unit
def test_telemetry_history_snapshot_ingestion():
    """Добавление данных через TelemetrySnapshot и словарь."""
    history = TelemetryHistory(maxlen=10)

    snap = TelemetrySnapshot(
        cpu_temp=50.0,
        cpu_load=25.0,
        gpu_temp=60.0,
        gpu_load=80.0,
        ram_load_pct=55.0,
        net_rx_kbps=1024.0,
        ping_ms=15.0,
    )
    history.add_snapshot(snap)

    assert history.get_series("cpu_temp") == [50.0]
    assert history.get_series("gpu_temp") == [60.0]
    assert history.get_series("ping_ms") == [15.0]

    # Добавление словаря
    dict_data = {
        "cpu_temp": 52.0,
        "cpu_load": 30.0,
        "gpu_temp": 62.0,
        "gpu_load": 85.0,
        "ping_ms": -1.0,  # Отрицательный пинг нормализуется в 0.0
    }
    history.add_snapshot(dict_data)

    assert history.get_series("cpu_temp") == [50.0, 52.0]
    assert history.get_series("ping_ms") == [15.0, 0.0]

    # Сводная статистика
    summary = history.get_summary("cpu_temp")
    assert summary["current"] == 52.0
    assert summary["min"] == 50.0
    assert summary["max"] == 52.0
    assert summary["avg"] == 51.0

    # Несуществующая метрика
    assert history.get_series("unknown_metric") == []
    assert history.get_summary("unknown_metric")["current"] == 0.0

    # Очистка
    history.clear()
    assert history.get_series("cpu_temp") == []


@pytest.mark.unit
def test_telemetry_history_long_run_memory_stability():
    """
    Проверка TelemetryHistory на долгосрочный поток данных (10 000 срезов).
    Все внутренние буферы метрик строго сохраняют размер maxlen=60.
    """
    history = TelemetryHistory(maxlen=60)

    snap = TelemetrySnapshot(
        cpu_temp=65.0,
        cpu_load=30.0,
        cpu_power=75.0,
        gpu_temp=70.0,
        gpu_hotspot=82.0,
        gpu_load=75.0,
        gpu_power=220.0,
        ram_load_pct=40.0,
        net_rx_kbps=512.0,
        net_tx_kbps=128.0,
        ping_ms=12.0,
    )

    for _ in range(10_000):
        history.add_snapshot(snap)

    for metric_name in history.TRACKED_METRICS:
        series = history.get_series(metric_name)
        assert len(series) == 60
        summary = history.get_summary(metric_name)
        assert summary["current"] > 0
        assert summary["min"] > 0
