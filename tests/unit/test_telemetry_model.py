"""
Модульные тесты для строго типизированной модели TelemetrySnapshot.
"""
import time
from core.telemetry_model import TelemetrySnapshot


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


def test_telemetry_snapshot_vram_percent():
    """Проверка вычисления процента видеопамяти."""
    snap = TelemetrySnapshot(gpu_vram_used=3072.0, gpu_vram_total=12288.0)
    assert snap.vram_percent == 25.0

    # Проверка деления на ноль при отсутствии dGPU
    snap_zero = TelemetrySnapshot(gpu_vram_used=0.0, gpu_vram_total=0.0)
    assert snap_zero.vram_percent == 0.0
