"""
Модульные тесты для модуля прямого аппаратного мониторинга HardwareMonitor.
"""
from unittest.mock import MagicMock, PropertyMock, patch
import pytest

from core.hardware_monitor import HardwareMonitor, is_admin
from core.telemetry_model import TelemetrySnapshot


def test_is_admin():
    """Проверка определения прав UAC (возвращает bool)."""
    res = is_admin()
    assert isinstance(res, bool)


def test_hardware_monitor_lifecycle():
    """Проверка жизненного цикла open / close и контекстного менеджера."""
    monitor = HardwareMonitor()
    assert not monitor.is_open

    with monitor:
        assert monitor.is_open
        snapshot = monitor.sample(ping_ms=10.0)
        assert isinstance(snapshot, TelemetrySnapshot)
        assert snapshot.ping_ms == 10.0
        assert snapshot.uptime_seconds >= 0

    assert not monitor.is_open


def test_hardware_monitor_network_rate_calculation():
    """Проверка вычисления дельты сетевого трафика (RX/TX)."""
    monitor = HardwareMonitor()
    snap = TelemetrySnapshot()

    # Имитация первого замера
    with patch("psutil.net_io_counters") as mock_net:
        mock_net.return_value = MagicMock(bytes_recv=1000000, bytes_sent=500000)
        monitor._update_network_rates(snap)
        assert snap.net_rx_kbps == 0.0
        assert snap.net_tx_kbps == 0.0

        # Имитация второго замера через 1 секунду (+100 KB recv, +50 KB sent)
        mock_net.return_value = MagicMock(bytes_recv=1102400, bytes_sent=551200)
        monitor._last_net_time -= 1.0  # Сдвигаем время на 1с назад
        monitor._update_network_rates(snap)

        assert snap.net_rx_kbps > 0.0
        assert snap.net_tx_kbps > 0.0


def test_hardware_monitor_fallback_when_lhm_unavailable():
    """Проверка работы в режиме чистого fallback psutil."""
    monitor = HardwareMonitor()
    monitor._computer = None
    monitor._is_open = True

    snapshot = monitor.sample(ping_ms=25.0)
    assert isinstance(snapshot, TelemetrySnapshot)
    assert snapshot.is_lhm_active is False
    assert snapshot.ping_ms == 25.0
    assert snapshot.cpu_load >= 0.0
    assert snapshot.ram_total_gb > 0.0


def test_hardware_monitor_mocked_lhm_sensors():
    """Проверка парсинга структуры датчиков LHM (CPU, dGPU, RAM, Motherboard)."""
    monitor = HardwareMonitor()

    def make_sensor(name, stype, val):
        s = MagicMock()
        s.Name = name
        s.SensorType = stype
        s.Value = val
        return s

    def make_hardware(name, htype, sensors, subhardware=None):
        h = MagicMock()
        h.Name = name
        h.HardwareType = htype
        h.Sensors = sensors
        h.SubHardware = subhardware or []
        return h

    cpu_sensors = [
        make_sensor("Core (Tctl/Tdie)", "Temperature", 55.4),
        make_sensor("CPU Total", "Load", 28.5),
        make_sensor("Cores (Average)", "Clock", 4500.0),
        make_sensor("Package", "Power", 75.2),
    ]
    cpu_hw = make_hardware("AMD Ryzen 7 7700", "Cpu", cpu_sensors)

    gpu_sensors = [
        make_sensor("GPU Core", "Temperature", 62.0),
        make_sensor("GPU Hot Spot", "Temperature", 71.5),
        make_sensor("GPU Core", "Load", 65.0),
        make_sensor("GPU Memory Used", "SmallData", 4096.0),
        make_sensor("GPU Memory Total", "SmallData", 12288.0),
        make_sensor("GPU Package", "Power", 220.0),
        make_sensor("GPU Fan 1", "Fan", 1450.0),
    ]
    gpu_hw = make_hardware("NVIDIA GeForce RTX 3080", "GpuNvidia", gpu_sensors)

    ram_sensors = [
        make_sensor("Memory Used", "Data", 16.5),
        make_sensor("Memory Available", "Data", 15.5),
        make_sensor("Memory", "Load", 51.5),
    ]
    ram_hw = make_hardware("Generic Memory", "Memory", ram_sensors)

    super_io = make_hardware(
        "Nuvoton NCT6799D", "SuperIO",
        [
            make_sensor("CPU Fan", "Fan", 980.0),
            make_sensor("Pump Fan", "Fan", 2400.0),
            make_sensor("System Fan #1", "Fan", 800.0),
        ]
    )
    mb_hw = make_hardware("MSI B650M", "Motherboard", [], [super_io])

    fake_computer = MagicMock()
    fake_computer.Hardware = [cpu_hw, gpu_hw, ram_hw, mb_hw]

    monitor._computer = fake_computer
    monitor._is_open = True
    monitor._visitor = MagicMock()

    with patch.object(HardwareMonitor, "is_available", new_callable=PropertyMock, return_value=True):
        snapshot = monitor.sample(ping_ms=5.0)

    assert snapshot.is_lhm_active is True
    assert snapshot.cpu_name == "AMD Ryzen 7 7700"
    assert snapshot.cpu_temp == 55.4
    assert snapshot.cpu_load == 28.5
    assert snapshot.cpu_clock == 4500.0
    assert snapshot.cpu_power == 75.2

    assert snapshot.gpu_name == "NVIDIA GeForce RTX 3080"
    assert snapshot.gpu_temp == 62.0
    assert snapshot.gpu_hotspot == 71.5
    assert snapshot.gpu_load == 65.0
    assert snapshot.gpu_vram_used == 4096.0
    assert snapshot.gpu_vram_total == 12288.0
    assert snapshot.gpu_power == 220.0
    assert snapshot.gpu_fan_rpm == 1450

    assert snapshot.ram_used_gb == 16.5
    assert snapshot.ram_total_gb == 32.0
    assert snapshot.ram_load_pct == 51.5

    assert snapshot.cpu_fan_rpm == 980
    assert snapshot.pump_rpm == 2400
    assert 800 in snapshot.chassis_fans_rpm


def test_hardware_monitor_update_visitor_execution():
    """Проверка логики IVisitor (UpdateVisitor): вызов Update и рекурсивный обход SubHardware."""
    from core.hardware_monitor import UpdateVisitor

    visitor = UpdateVisitor()

    # 1. VisitComputer вызывает Traverse
    mock_computer = MagicMock()
    visitor.VisitComputer(mock_computer)
    mock_computer.Traverse.assert_called_once_with(visitor)

    # 2. VisitHardware вызывает hardware.Update() и sub.Accept(visitor) для каждого SubHardware
    mock_sub = MagicMock()
    mock_hw = MagicMock()
    mock_hw.SubHardware = [mock_sub]

    visitor.VisitHardware(mock_hw)
    mock_hw.Update.assert_called_once()
    mock_sub.Accept.assert_called_once_with(visitor)

    # 3. VisitSensor и VisitParameter безопасны (no-op)
    visitor.VisitSensor(MagicMock())
    visitor.VisitParameter(MagicMock())


def test_hardware_monitor_visitor_exception_fallback():
    """Проверка корректной деградации в psutil при ошибке выполнения IVisitor."""
    monitor = HardwareMonitor()
    fake_computer = MagicMock()
    fake_computer.Accept.side_effect = RuntimeError("Access Denied Ring 0 driver fault")

    monitor._computer = fake_computer
    monitor._is_open = True
    monitor._visitor = MagicMock()

    with patch.object(HardwareMonitor, "is_available", new_callable=PropertyMock, return_value=True):
        snapshot = monitor.sample(ping_ms=12.0)

    # Должен сработать fallback без падения процесса
    assert isinstance(snapshot, TelemetrySnapshot)
    assert snapshot.is_lhm_active is False
    assert snapshot.ping_ms == 12.0
    assert snapshot.cpu_load >= 0.0
    assert snapshot.ram_total_gb > 0.0


def test_hardware_monitor_fallback_when_not_admin():
    """Проверка поведения при отсутствии прав Администратора (non-admin fallback)."""
    with patch("core.hardware_monitor.is_admin", return_value=False):
        monitor = HardwareMonitor()
        assert monitor._is_admin is False

        # Имитируем сбой открытия Ring0 драйвера из-за отсутствия UAC
        with patch("core.hardware_monitor._ComputerClass", side_effect=PermissionError("Ring 0 driver requires UAC")):
            with patch.object(HardwareMonitor, "is_available", new_callable=PropertyMock, return_value=True):
                opened = monitor.open()
                assert opened is False
                assert not monitor.is_open

        # Срез телеметрии возвращает snapshot со статусом is_admin=False и is_lhm_active=False
        snapshot = monitor.sample(ping_ms=18.5)
        assert isinstance(snapshot, TelemetrySnapshot)
        assert snapshot.is_admin is False
        assert snapshot.is_lhm_active is False
        assert snapshot.ping_ms == 18.5
        assert snapshot.cpu_load >= 0.0
        assert snapshot.ram_total_gb > 0.0


def test_hardware_monitor_gpu_prioritization_dgpu_over_igpu():
    """Проверка приоритизации дискретной видеокарты (dGPU NVIDIA) над iGPU (AMD Radeon)."""
    monitor = HardwareMonitor()

    def make_sensor(name, stype, val):
        s = MagicMock()
        s.Name = name
        s.SensorType = stype
        s.Value = val
        return s

    def make_hardware(name, htype, sensors):
        h = MagicMock()
        h.Name = name
        h.HardwareType = htype
        h.Sensors = sensors
        h.SubHardware = []
        return h

    # Встроенный iGPU (AMD Radeon Graphics)
    igpu_sensors = [
        make_sensor("GPU Core", "Temperature", 42.0),
        make_sensor("GPU Core", "Load", 5.0),
    ]
    igpu_hw = make_hardware("AMD Radeon(TM) Graphics", "GpuAmd", igpu_sensors)

    # Дискретный dGPU (NVIDIA GeForce RTX 3080)
    dgpu_sensors = [
        make_sensor("GPU Core", "Temperature", 68.0),
        make_sensor("GPU Hot Spot", "Temperature", 79.0),
        make_sensor("GPU Core", "Load", 88.0),
    ]
    dgpu_hw = make_hardware("NVIDIA GeForce RTX 3080", "GpuNvidia", dgpu_sensors)

    fake_computer = MagicMock()
    # iGPU идет первым в списке, dGPU вторым
    fake_computer.Hardware = [igpu_hw, dgpu_hw]

    monitor._computer = fake_computer
    monitor._is_open = True
    monitor._visitor = MagicMock()

    with patch.object(HardwareMonitor, "is_available", new_callable=PropertyMock, return_value=True):
        snapshot = monitor.sample()

    # Обязан быть выбран dGPU
    assert snapshot.gpu_name == "NVIDIA GeForce RTX 3080"
    assert snapshot.gpu_temp == 68.0
    assert snapshot.gpu_hotspot == 79.0
    assert snapshot.gpu_load == 88.0


def test_hardware_monitor_cpu_parsing_fallbacks():
    """Проверка fallback-парсинга ядер процессора при отсутствии датчиков Tctl/Tdie и Average Clock."""
    monitor = HardwareMonitor()

    def make_sensor(name, stype, val):
        s = MagicMock()
        s.Name = name
        s.SensorType = stype
        s.Value = val
        return s

    def make_hardware(name, htype, sensors):
        h = MagicMock()
        h.Name = name
        h.HardwareType = htype
        h.Sensors = sensors
        h.SubHardware = []
        return h

    cpu_sensors = [
        make_sensor("Core #1", "Temperature", 48.0),
        make_sensor("Core #2", "Temperature", 56.0),
        make_sensor("Core #1", "Clock", 4200.0),
        make_sensor("Core #2", "Clock", 4400.0),
        make_sensor("CPU Total", "Load", 40.0),
    ]
    cpu_hw = make_hardware("Generic CPU", "Cpu", cpu_sensors)

    fake_computer = MagicMock()
    fake_computer.Hardware = [cpu_hw]

    monitor._computer = fake_computer
    monitor._is_open = True
    monitor._visitor = MagicMock()

    with patch.object(HardwareMonitor, "is_available", new_callable=PropertyMock, return_value=True):
        snapshot = monitor.sample()

    # Температура должна быть максимальной среди ядер (56.0)
    assert snapshot.cpu_temp == 56.0
    # Частота должна быть средней среди ядер ((4200 + 4400) / 2 = 4300.0)
    assert snapshot.cpu_clock == 4300.0
    assert snapshot.cpu_load == 40.0


def test_hardware_monitor_storage_parsing():
    """Проверка парсинга датчиков NVMe SSD накопителя."""
    monitor = HardwareMonitor()

    def make_sensor(name, stype, val):
        s = MagicMock()
        s.Name = name
        s.SensorType = stype
        s.Value = val
        return s

    def make_hardware(name, htype, sensors):
        h = MagicMock()
        h.Name = name
        h.HardwareType = htype
        h.Sensors = sensors
        h.SubHardware = []
        return h

    storage_sensors = [
        make_sensor("Temperature", "Temperature", 44.0),
        make_sensor("Total Activity", "Load", 15.5),
    ]
    storage_hw = make_hardware("Samsung SSD 980 PRO 1TB", "Storage", storage_sensors)

    fake_computer = MagicMock()
    fake_computer.Hardware = [storage_hw]

    monitor._computer = fake_computer
    monitor._is_open = True
    monitor._visitor = MagicMock()

    with patch.object(HardwareMonitor, "is_available", new_callable=PropertyMock, return_value=True):
        snapshot = monitor.sample()

    assert snapshot.storage_name == "Samsung SSD 980 PRO 1TB"
    assert snapshot.storage_temp == 44.0
    assert snapshot.storage_activity == 15.5

