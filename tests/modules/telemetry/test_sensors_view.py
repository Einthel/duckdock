"""
Модульные тесты для двухуровневого NOC-дашборда (modules/telemetry/view.py).
Проверка инвариантов Stealth Focus, раскладки 944x600, форматирования метрик
и интеграции с TelemetrySnapshot и EventBus.
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from core.i18n import I18nManager
from modules.telemetry.history import TelemetryHistory
from modules.telemetry.models import TelemetrySnapshot
from modules.telemetry.view import SensorsView, _format_uptime, _format_net_speed, _temp_color_hex


def test_format_helpers():
    """Тестирование вспомогательных функций форматирования аптайма, скорости и цвета."""
    mgr = I18nManager()

    # 1. RU locale
    mgr.set_language("ru", emit_signal=False)
    assert _format_uptime(0) == "0с"
    assert _format_uptime(45) == "45с"
    assert _format_uptime(125) == "02м 05с"
    assert _format_uptime(3665) == "01ч 01м 05с"
    assert _format_uptime(90061) == "1д 01ч 01м 01с"

    assert _format_net_speed(512.0) == "512 КБ/с"
    assert _format_net_speed(1024.0) == "1.0 МБ/с"
    assert _format_net_speed(15360.0) == "15.0 МБ/с"

    # 2. EN locale
    mgr.set_language("en", emit_signal=False)
    assert _format_uptime(0) == "0s"
    assert _format_uptime(45) == "45s"
    assert _format_uptime(125) == "02m 05s"
    assert _format_uptime(3665) == "01h 01m 05s"
    assert _format_uptime(90061) == "1d 01h 01m 01s"

    assert _format_net_speed(512.0) == "512 KB/s"
    assert _format_net_speed(1024.0) == "1.0 MB/s"
    assert _format_net_speed(15360.0) == "15.0 MB/s"

    # Сброс обратно на RU
    mgr.set_language("ru", emit_signal=False)

    # Temp Color Hex
    assert _temp_color_hex(45.0) == "#38bdf8"   # <60 Cyan
    assert _temp_color_hex(68.5) == "#f59e0b"   # 60-78 Amber
    assert _temp_color_hex(84.0) == "#ef4444"   # >=80 Crimson


def test_sensors_view_stealth_focus_and_layout(qapp):
    """
    Инвариант Stealth Focus: все виджеты обязаны иметь Qt.NoFocus.
    Проверка наличия ключевых секций (Header Bar, Hero Cards, NOC Grid).
    """
    view = SensorsView(auto_start=False)

    # Корневой инвариант Stealth Focus
    assert view.focusPolicy() == Qt.FocusPolicy.NoFocus

    # Проверка дочерних виджетов
    assert view.cpu_card.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.gpu_card.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.ram_card.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.net_card.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.storage_card.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.chassis_card.focusPolicy() == Qt.FocusPolicy.NoFocus

    # Спарклайны также NoFocus
    assert view.spark_cpu.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.spark_gpu.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.spark_ram.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.spark_net.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert view.spark_storage.focusPolicy() == Qt.FocusPolicy.NoFocus

    view.cleanup()


def test_sensors_view_update_snapshot_cpu_gpu(qapp):
    """
    Проверка корректного обновления Hero-карточек CPU и GPU при получении TelemetrySnapshot.
    """
    view = SensorsView(auto_start=False)

    snap = TelemetrySnapshot(
        cpu_name="AMD Ryzen 7 7700",
        cpu_temp=54.2,
        cpu_load=28.5,
        cpu_clock=4850.0,
        cpu_power=65.4,
        cpu_fan_rpm=1420,
        pump_rpm=2400,
        gpu_name="NVIDIA GeForce RTX 4070",
        gpu_temp=58.6,
        gpu_hotspot=68.1,
        gpu_load=62.0,
        gpu_vram_used=6144.0,   # 6 GB
        gpu_vram_total=12288.0, # 12 GB
        gpu_power=185.0,
        gpu_fan_rpm=1600,
        uptime_seconds=3660,
        is_lhm_active=True,
        is_admin=True,
    )

    view.update_snapshot(snap)

    # Header Bar
    assert "Direct Ring0" in view.lbl_lhm_status.text()
    assert "[UAC: АДМИН]" in view.lbl_uac_status.text()
    assert "01ч 01м 00с" in view.lbl_uptime.text()

    # CPU Master
    assert view.lbl_cpu_name.text() == "AMD Ryzen 7 7700"
    assert "54.2°C" in view.lbl_cpu_temp.text()
    assert "28.5%" in view.val_cpu_load.text()
    assert "4.85 ГГц" in view.val_cpu_clock.text()
    assert "65.4 Вт" in view.lbl_cpu_power_badge.text()
    assert "1420 об/мин" in view.val_cpu_fan.text()
    assert "2400 об/мин" in view.val_cpu_pump.text()
    assert view.bar_cpu_load.value() == 28
    assert view.spark_cpu.latest_value == 54.2

    # GPU Master
    assert view.lbl_gpu_name.text() == "NVIDIA GeForce RTX 4070"
    assert "58.6°C" in view.lbl_gpu_temp.text()
    assert "68.1°C" in view.lbl_gpu_hotspot.text()
    assert "62.0%" in view.val_gpu_load.text()
    assert "6.0 / 12.0 ГБ" in view.val_gpu_vram.text()
    assert view.bar_gpu_vram.value() == 50
    assert "1600 об/мин" in view.val_gpu_fan.text()
    assert "185 Вт" in view.val_gpu_power.text()
    assert view.spark_gpu.latest_value == 58.6

    view.cleanup()


def test_sensors_view_update_snapshot_noc_grid(qapp):
    """
    Проверка нижнего яруса: RAM, Network & Ping, NVMe Storage, Chassis & Motherboard.
    """
    view = SensorsView(auto_start=False)

    snap = TelemetrySnapshot(
        ram_used_gb=18.4,
        ram_total_gb=32.0,
        ram_load_pct=57.5,
        net_rx_kbps=15360.0, # 15.0 MB/s
        net_tx_kbps=2048.0,  # 2.0 MB/s
        ping_ms=18.2,
        storage_name="Samsung 980 PRO 1TB",
        storage_temp=42.0,
        storage_activity=14.0,
        vrm_temp=46.0,
        chassis_fans_rpm=[950, 980, 1020],
        is_lhm_active=False,
        is_admin=False,
    )

    view.update_snapshot(snap)

    # Header Fallback & User
    assert "OS Fallback" in view.lbl_lhm_status.text()
    assert "[UAC: ПОЛЬЗОВАТЕЛЬ]" in view.lbl_uac_status.text()

    # RAM
    assert "18.4 / 32.0 ГБ" in view.val_ram_gb.text()
    assert view.lbl_ram_pct.text() == "57%"
    assert view.bar_ram.value() == 57
    assert view.spark_ram.latest_value == 57.5

    # Network
    assert "18 мс" in view.lbl_net_ping.text()
    assert "15.0 МБ/с" in view.val_net_rx.text()
    assert "2.0 МБ/с" in view.val_net_tx.text()
    assert view.spark_net.latest_value == 15.0

    # NVMe
    assert "Samsung 980 PRO" in view.val_storage_name.text()
    assert "42°C" in view.lbl_storage_temp.text()
    assert "14%" in view.val_storage_act.text()
    assert view.bar_storage.value() == 14

    # Chassis
    assert "VRM: 46°C" in view.lbl_vrm_temp.text()
    assert "1020 ОБ/МИН" in view.val_chassis_fans.text()
    assert "950, 980, 1020" in view.val_chassis_subfans.text()

    view.cleanup()


def test_sensors_view_eventbus_integration(qapp):
    """
    Проверка обновления виджета при эмиссии сигнала через bus.sensors_updated.
    """
    view = SensorsView(auto_start=False)

    data = {
        "cpu_name": "EventBus CPU",
        "cpu_temp": 49.0,
        "cpu_load": 15.0,
        "gpu_name": "EventBus GPU",
        "gpu_temp": 52.0,
        "ram_used_gb": 10.0,
        "ram_total_gb": 32.0,
        "ram_load_pct": 31.25,
        "is_lhm_active": True,
        "is_admin": True,
    }

    bus.sensors_updated.emit(data)
    qapp.processEvents()

    assert view.lbl_cpu_name.text() == "EventBus CPU"
    assert "49.0°C" in view.lbl_cpu_temp.text()
    assert view.lbl_gpu_name.text() == "EventBus GPU"
    assert "52.0°C" in view.lbl_gpu_temp.text()
    assert "10.0 / 32.0 ГБ" in view.val_ram_gb.text()

    view.cleanup()


def test_sensors_view_graceful_missing_data(qapp):
    """
    Проверка устойчивости при частично заполненном снимке телеметрии.
    """
    view = SensorsView(auto_start=False)

    empty_snap = TelemetrySnapshot()
    view.update_snapshot(empty_snap)

    assert view.lbl_cpu_temp.text() == "--.-°C"
    assert view.lbl_gpu_temp.text() == "--.-°C"
    assert view.val_cpu_clock.text() == "-- ГГц"
    assert view.val_cpu_fan.text() == "-- об/мин"
    assert view.val_gpu_vram.text() == "-- / -- ГБ"
    assert "ОТКЛЮЧЕНО" in view.lbl_net_ping.text()

    view.cleanup()


def test_sensors_view_retranslate_ui(qapp):
    """Проверка обновления текстов SensorsView при смене языка без прерывания воркера."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)

    view = SensorsView(auto_start=False)
    try:
        # Проверка русских надписей
        assert view.lbl_ram_title.text() == "ОЗУ DDR5"
        assert view.lbl_ram_sub.text() == "Высокоскоростной канал"
        assert view.lbl_storage_sub.text() == "Прямой ввод-вывод PCIe"
        assert view.lbl_cooling_status.text() == "● ОБДУВ В НОРМЕ"
        assert view.lbl_lhm_status.text() == "● LibreHardwareMonitor (Direct Ring0)"
        assert "ВРЕМЯ РАБОТЫ:" in view.lbl_uptime.text()
        assert view.lbl_cpu_tag.text() == "CPU MASTER"
        assert view.lbl_gpu_tag.text() == "GPU MASTER"
        assert view.lbl_k_cpu_load.text() == "НАГРУЗКА"
        assert view.lbl_k_cpu_clock.text() == "ЧАСТОТА"
        assert view.lbl_k_cpu_fan.text() == "КУЛЕР"
        assert view.lbl_k_cpu_pump.text() == "ПОМПА"
        assert view.lbl_k_gpu_power.text() == "МОЩНОСТЬ"

        # Применяем снимок с fallback статусом
        snapshot = TelemetrySnapshot(
            is_lhm_active=False,
            is_admin=False,
            uptime_seconds=3600,
            cpu_name="Ryzen 7 7700",
            cpu_temp=55.0,
            cpu_load=20.0,
            gpu_hotspot=65.0,
            ping_ms=-1,
            chassis_fans_rpm=[],
            cpu_fan_rpm=0,
        )
        view.update_snapshot(snapshot)

        assert view.lbl_lhm_status.text() == "● Аппаратная телеметрия (OS Fallback)"
        assert view.lbl_uac_status.text() == "[UAC: ПОЛЬЗОВАТЕЛЬ]"
        assert view.lbl_net_ping.text() == "● ОТКЛЮЧЕНО"
        assert view.val_chassis_subfans.text() == "Пассивное охлаждение"
        assert view.val_chassis_fans.text() == "ВЕНТИЛЯТОР: -- ОБ/МИН"

        # Горячая смена языка на английский
        mgr.set_language("en")
        # TouchModuleView автоматически вызывает retranslate_ui()

        assert view.lbl_ram_title.text() == "RAM DDR5"
        assert view.lbl_ram_sub.text() == "High-Speed Channel"
        assert view.lbl_storage_sub.text() == "PCIe Gen4 Direct IO"
        assert view.lbl_cooling_status.text() == "● OPTIMAL AIRFLOW"
        assert view.lbl_lhm_status.text() == "● Hardware Telemetry (OS Fallback)"
        assert view.lbl_uac_status.text() == "[UAC: USER]"
        assert view.val_chassis_subfans.text() == "Passive Cooling"
        assert view.val_chassis_fans.text() == "FAN: -- RPM"
        assert view.lbl_net_ping.text() == "● DISCONNECTED"
        assert view.lbl_k_cpu_load.text() == "LOAD"
        assert view.lbl_k_cpu_clock.text() == "CLOCK"
        assert view.lbl_k_cpu_fan.text() == "COOLER"
        assert view.lbl_k_cpu_pump.text() == "PUMP"
        assert view.lbl_k_gpu_power.text() == "POWER"

        # Переключение обратно на русский
        mgr.set_language("ru")
        assert view.lbl_ram_title.text() == "ОЗУ DDR5"
        assert view.lbl_ram_sub.text() == "Высокоскоростной канал"
        assert view.lbl_lhm_status.text() == "● Аппаратная телеметрия (OS Fallback)"
        assert view.lbl_uac_status.text() == "[UAC: ПОЛЬЗОВАТЕЛЬ]"
        assert view.val_chassis_subfans.text() == "Пассивное охлаждение"
        assert view.val_chassis_fans.text() == "ВЕНТИЛЯТОР: -- ОБ/МИН"
    finally:
        mgr.set_language("ru", emit_signal=False)
        view.cleanup()
        view.deleteLater()
