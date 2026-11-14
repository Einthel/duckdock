"""
Модульные тесты для буфера истории телеметрии RingBuffer и TelemetryHistory.
"""
from core.telemetry_history import RingBuffer, TelemetryHistory
from core.telemetry_model import TelemetrySnapshot


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


def test_ring_buffer_invalid_values():
    """Обработка некорректных типов данных без исключений."""
    buf = RingBuffer(maxlen=5)
    buf.append("invalid")
    buf.append(None)
    buf.append(42)

    assert len(buf) == 3
    assert buf.to_list() == [0.0, 0.0, 42.0]


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
        assert summary["max"] > 0

