"""
Модульные тесты для асинхронного рабочего потока TelemetryWorker.
"""
import time
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QCoreApplication
import pytest

from core.event_bus import bus
from core.telemetry_model import TelemetrySnapshot
from core.telemetry_worker import TelemetryWorker, measure_network_latency


def test_measure_network_latency():
    """Проверка функции замера задержки сети."""
    # Тест с валидным подключением
    val = measure_network_latency(["1.1.1.1", "8.8.8.8"], timeout=0.5)
    assert isinstance(val, float)

    # Тест с недоступным адресом (должен вернуть -1.0)
    with patch("socket.socket.connect", side_effect=OSError("Unreachable")):
        val_fail = measure_network_latency(["192.0.2.1"], timeout=0.1)
        assert val_fail == -1.0


def test_telemetry_worker_lifecycle(qapp):
    """Проверка запуска, сигналов и остановки TelemetryWorker."""
    worker = TelemetryWorker(interval_ms=100)
    assert not worker.is_running
    assert worker.last_snapshot is None

    received_snapshots = []
    received_bus_dicts = []

    def on_snapshot(s):
        received_snapshots.append(s)

    def on_bus_event(d):
        received_bus_dicts.append(d)

    worker.snapshot_ready.connect(on_snapshot)
    bus.sensors_updated.connect(on_bus_event)

    fake_snap = TelemetrySnapshot(
        cpu_name="Mock CPU",
        cpu_temp=50.0,
        gpu_name="Mock GPU",
        gpu_temp=60.0,
    )

    with patch("core.telemetry_worker.HardwareMonitor") as MockHM, \
         patch("core.telemetry_worker.measure_network_latency", return_value=12.5):
        mock_instance = MagicMock()
        mock_instance.sample.return_value = fake_snap
        MockHM.return_value = mock_instance

        worker.start()
        assert worker.is_running

        # Ожидаем появления хотя бы одного снимка с обработкой событий Qt
        for _ in range(30):
            time.sleep(0.05)
            qapp.processEvents()
            if len(received_snapshots) > 0:
                break

        worker.stop()
        assert not worker.is_running

    assert len(received_snapshots) >= 1
    assert received_snapshots[0].cpu_name == "Mock CPU"
    assert received_snapshots[0].gpu_name == "Mock GPU"

    assert len(received_bus_dicts) >= 1
    assert received_bus_dicts[0]["cpu_temp"] == 50.0

    # Отключаем слот от синглтона bus, чтобы не аффектить другие тесты
    bus.sensors_updated.disconnect(on_bus_event)
