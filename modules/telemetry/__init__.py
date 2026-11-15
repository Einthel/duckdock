"""
Подсистема аппаратного мониторинга и телеметрии NOC DuckDock.
"""
from modules.telemetry.aida_reader import AidaReader
from modules.telemetry.hardware_monitor import HardwareMonitor, is_admin
from modules.telemetry.history import RingBuffer, TelemetryHistory
from modules.telemetry.models import TelemetrySnapshot
from modules.telemetry.view import SensorsView
from modules.telemetry.worker import TelemetryWorker, measure_network_latency

__all__ = [
    "AidaReader",
    "HardwareMonitor",
    "is_admin",
    "RingBuffer",
    "TelemetryHistory",
    "TelemetrySnapshot",
    "SensorsView",
    "TelemetryWorker",
    "measure_network_latency",
]
