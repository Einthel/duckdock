"""
Модуль интеграции LibreHardwareMonitorLib.dll для прямого аппаратного мониторинга (Ring 0 / UAC).
Обеспечивает опрос датчиков CPU (Ryzen Tctl/Tdie), dGPU (RTX 3080 Core/Hotspot/VRAM/Power/Fan),
RAM, Storage, Motherboard Super I/O и сетевого стека с мягким fallback на psutil при отсутствии прав или сборки.
"""
import ctypes
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

from core.telemetry_model import TelemetrySnapshot

logger = logging.getLogger(__name__)

# Попытка импорта pythonnet и LibreHardwareMonitor
_PYTHONNET_AVAILABLE = False
_LHM_AVAILABLE = False
_ComputerClass = None
_IVisitorClass = None
_HardwareType = None
_SensorType = None

def is_admin() -> bool:
    """Проверка прав Администратора (Windows UAC)."""
    try:
        if sys.platform == "win32":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        return False
    except Exception:
        return False

def _resolve_dll_path(custom_path: Optional[str] = None) -> Path:
    """Определение абсолютного пути к LibreHardwareMonitorLib.dll."""
    if custom_path:
        return Path(custom_path)
    
    # Режим сборки PyInstaller
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            base_dir = Path(sys._MEIPASS)
            candidate = base_dir / "resources" / "bin" / "LibreHardwareMonitorLib.dll"
            if candidate.is_file():
                return candidate
        exe_dir = Path(sys.executable).resolve().parent
        candidate = exe_dir / "resources" / "bin" / "LibreHardwareMonitorLib.dll"
        if candidate.is_file():
            return candidate

    # Режим разработки
    root_dir = Path(__file__).resolve().parent.parent
    candidate = root_dir / "resources" / "bin" / "LibreHardwareMonitorLib.dll"
    if candidate.is_file():
        return candidate

    # Системный путь RTSS (если установлен)
    rtss_path = Path("C:/Program Files (x86)/RivaTuner Statistics Server/Plugins/Client/LHMDataProvider/LibreHardwareMonitorLib.dll")
    if rtss_path.is_file():
        return rtss_path

    return candidate

def _init_lhm(dll_path: Optional[str] = None) -> bool:
    """Динамическая инициализация pythonnet и загрузка сборки LibreHardwareMonitorLib."""
    global _PYTHONNET_AVAILABLE, _LHM_AVAILABLE
    global _ComputerClass, _IVisitorClass, _HardwareType, _SensorType

    if _LHM_AVAILABLE:
        return True

    target_dll = _resolve_dll_path(dll_path)
    if not target_dll.is_file():
        logger.warning(f"LibreHardwareMonitorLib.dll не найдена по пути: {target_dll}")
        return False

    try:
        import clr
        _PYTHONNET_AVAILABLE = True
        clr.AddReference(str(target_dll))

        from LibreHardwareMonitor.Hardware import Computer, IVisitor, HardwareType, SensorType
        _ComputerClass = Computer
        _IVisitorClass = IVisitor
        _HardwareType = HardwareType
        _SensorType = SensorType
        _LHM_AVAILABLE = True
        logger.info(f"LibreHardwareMonitorLib успешно загружена: {target_dll}")
        return True
    except Exception as e:
        logger.warning(f"Не удалось инициализировать LibreHardwareMonitorLib: {e}")
        return False


# Определение класса UpdateVisitor при доступности IVisitor
class _BaseVisitor:
    pass

if _init_lhm():
    class UpdateVisitor(_IVisitorClass):
        __namespace__ = "LibreHardwareMonitor.Hardware"

        def VisitComputer(self, computer):
            computer.Traverse(self)

        def VisitHardware(self, hardware):
            hardware.Update()
            for sub in hardware.SubHardware:
                sub.Accept(self)

        def VisitSensor(self, sensor):
            pass

        def VisitParameter(self, parameter):
            pass
else:
    class UpdateVisitor(_BaseVisitor):
        pass


class HardwareMonitor:
    """
    Фасад прямого аппаратного мониторинга на базе LibreHardwareMonitorLib.
    Управляет жизненным циклом Computer (Open/Close) и формирует строгие TelemetrySnapshot.
    """

    def __init__(self, dll_path: Optional[str] = None):
        self._dll_path = dll_path
        self._computer = None
        self._visitor = None
        self._is_open = False
        self._is_admin = is_admin()

        # Состояние для расчета сетевого трафика (RX/TX)
        self._last_net_bytes: Optional[Tuple[int, int]] = None
        self._last_net_time: float = time.time()

        # Инициализация LHM сборки
        self._lhm_loaded = _init_lhm(self._dll_path)

    @property
    def is_available(self) -> bool:
        """Доступен ли LibreHardwareMonitor в системе."""
        return self._lhm_loaded and _ComputerClass is not None

    @property
    def is_open(self) -> bool:
        """Открыт ли контекст Computer."""
        return self._is_open

    def open(self) -> bool:
        """Открытие аппаратных интерфейсов LibreHardwareMonitor."""
        if not self.is_available:
            logger.info("HardwareMonitor: запуск в fallback-режиме psutil (LHM недоступен)")
            self._is_open = True
            return True

        if self._is_open:
            return True

        try:
            self._computer = _ComputerClass()
            self._computer.IsCpuEnabled = True
            self._computer.IsGpuEnabled = True
            self._computer.IsMemoryEnabled = True
            self._computer.IsMotherboardEnabled = True
            self._computer.IsStorageEnabled = True
            self._computer.IsNetworkEnabled = True
            self._computer.Open()

            self._visitor = UpdateVisitor()
            self._is_open = True
            logger.info(f"HardwareMonitor: LHM Computer открыт (Admin UAC: {self._is_admin})")
            return True
        except Exception as e:
            logger.error(f"HardwareMonitor: ошибка открытия Computer: {e}", exc_info=True)
            self._computer = None
            self._is_open = False
            return False

    def close(self) -> None:
        """Освобождение аппаратных драйверов и закрытие Computer."""
        if self._computer is not None:
            try:
                self._computer.Close()
                logger.info("HardwareMonitor: LHM Computer закрыт")
            except Exception as e:
                logger.warning(f"HardwareMonitor: ошибка при закрытии Computer: {e}")
            finally:
                self._computer = None
        self._is_open = False

    def __enter__(self) -> "HardwareMonitor":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def sample(self, ping_ms: float = -1.0) -> TelemetrySnapshot:
        """
        Полный синхронный срез аппаратной телеметрии.
        Возвращает нормализованный объект TelemetrySnapshot.
        """
        snapshot = TelemetrySnapshot(
            is_lhm_active=False,
            is_admin=self._is_admin,
            ping_ms=ping_ms,
            timestamp=time.time(),
        )

        # Расчет сетевого трафика через psutil (высокая точность)
        self._update_network_rates(snapshot)

        # Системный Uptime
        try:
            snapshot.uptime_seconds = int(time.time() - psutil.boot_time())
        except Exception:
            snapshot.uptime_seconds = 0

        # Если LHM недоступен или не открыт — собираем чистый psutil
        if not self.is_available or not self._is_open or self._computer is None:
            self._collect_psutil_fallback(snapshot)
            return snapshot

        # Обход сенсоров через Visitor
        try:
            self._computer.Accept(self._visitor)
            snapshot.is_lhm_active = True
        except Exception as e:
            logger.warning(f"HardwareMonitor: ошибка обхода IVisitor: {e}")
            self._collect_psutil_fallback(snapshot)
            return snapshot

        try:
            self._extract_lhm_telemetry(snapshot)
        except Exception as e:
            logger.error(f"HardwareMonitor: ошибка извлечения телеметрии LHM: {e}", exc_info=True)
            self._collect_psutil_fallback(snapshot)

        return snapshot

    def _update_network_rates(self, snapshot: TelemetrySnapshot) -> None:
        """Расчет скорости передачи данных сети (KB/s)."""
        now = time.time()
        try:
            net_io = psutil.net_io_counters()
            current_bytes = (net_io.bytes_recv, net_io.bytes_sent)

            if self._last_net_bytes is not None:
                dt = max(0.1, now - self._last_net_time)
                rx_delta = max(0, current_bytes[0] - self._last_net_bytes[0])
                tx_delta = max(0, current_bytes[1] - self._last_net_bytes[1])
                snapshot.net_rx_kbps = round(rx_delta / 1024.0 / dt, 1)
                snapshot.net_tx_kbps = round(tx_delta / 1024.0 / dt, 1)

            self._last_net_bytes = current_bytes
            self._last_net_time = now
        except Exception:
            pass

    def _collect_psutil_fallback(self, snapshot: TelemetrySnapshot) -> None:
        """Заполнение базовой телеметрии из psutil."""
        try:
            snapshot.cpu_load = round(psutil.cpu_percent(interval=None), 1)
        except Exception:
            pass

        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                snapshot.cpu_clock = round(cpu_freq.current, 0)
        except Exception:
            pass

        try:
            mem = psutil.virtual_memory()
            snapshot.ram_total_gb = round(mem.total / (1024**3), 2)
            snapshot.ram_used_gb = round(mem.used / (1024**3), 2)
            snapshot.ram_load_pct = round(mem.percent, 1)
        except Exception:
            pass

        try:
            disk = psutil.disk_usage("C:\\")
            snapshot.storage_name = "System (C:)"
            snapshot.storage_activity = round(disk.percent, 1)
        except Exception:
            pass

    def _extract_lhm_telemetry(self, snapshot: TelemetrySnapshot) -> None:
        """Парсинг сенсоров LibreHardwareMonitor и наполнение снимка."""
        dgpu_hardware = None
        igpu_hardware = None

        # Первый проход: сбор CPU, RAM, GPU, Motherboard, Storage
        for h in self._computer.Hardware:
            htype_str = str(h.HardwareType)

            if "Cpu" in htype_str:
                self._parse_cpu(h, snapshot)
            elif "Memory" in htype_str:
                self._parse_memory(h, snapshot)
            elif "Gpu" in htype_str:
                # Разделение дискретной и интегрированной графики
                h_name_lower = str(h.Name).lower()
                if "nvidia" in h_name_lower or "geforce" in h_name_lower or "rtx" in h_name_lower:
                    dgpu_hardware = h
                elif "radeon" in h_name_lower and "graphics" in h_name_lower:
                    igpu_hardware = h
                else:
                    if dgpu_hardware is None:
                        dgpu_hardware = h
            elif "Motherboard" in htype_str:
                self._parse_motherboard(h, snapshot)
            elif "Storage" in htype_str:
                self._parse_storage(h, snapshot)

        # Обработка GPU: приоритет отдаем dGPU (RTX 3080)
        target_gpu = dgpu_hardware or igpu_hardware
        if target_gpu:
            self._parse_gpu(target_gpu, snapshot)

        # Fallback по полям, если LHM в user-mode вернул 0.0 или пустые значения
        if snapshot.cpu_load == 0.0:
            snapshot.cpu_load = round(psutil.cpu_percent(interval=None), 1)

        if snapshot.cpu_clock == 0.0:
            try:
                freq = psutil.cpu_freq()
                if freq:
                    snapshot.cpu_clock = round(freq.current, 0)
            except Exception:
                pass

        if snapshot.ram_total_gb == 0.0:
            mem = psutil.virtual_memory()
            snapshot.ram_total_gb = round(mem.total / (1024**3), 2)
            snapshot.ram_used_gb = round(mem.used / (1024**3), 2)
            snapshot.ram_load_pct = round(mem.percent, 1)

        if not snapshot.storage_name:
            try:
                disk = psutil.disk_usage("C:\\")
                snapshot.storage_name = "System (C:)"
                snapshot.storage_activity = round(disk.percent, 1)
            except Exception:
                pass

    def _parse_cpu(self, h: Any, snapshot: TelemetrySnapshot) -> None:
        """Извлечение датчиков процессора."""
        snapshot.cpu_name = str(h.Name)
        max_core_temp = 0.0
        core_clocks = []

        for s in h.Sensors:
            s_val = float(s.Value) if s.Value is not None else None
            if s_val is None:
                continue

            stype = str(s.SensorType)
            sname = str(s.Name)

            if stype == "Temperature":
                if "Tctl" in sname or "Package" in sname:
                    snapshot.cpu_temp = round(s_val, 1)
                elif "Core #" in sname:
                    max_core_temp = max(max_core_temp, s_val)
            elif stype == "Load":
                if sname == "CPU Total":
                    snapshot.cpu_load = round(s_val, 1)
            elif stype == "Clock":
                if "Average" in sname:
                    snapshot.cpu_clock = round(s_val, 0)
                elif "Core #" in sname:
                    core_clocks.append(s_val)
            elif stype == "Power":
                if "Package" in sname:
                    snapshot.cpu_power = round(s_val, 1)

        # Если Tctl/Tdie не найден, берем максимум ядер
        if snapshot.cpu_temp == 0.0 and max_core_temp > 0.0:
            snapshot.cpu_temp = round(max_core_temp, 1)

        # Если средняя частота не найдена, считаем среднее по ядрам
        if snapshot.cpu_clock == 0.0 and core_clocks:
            snapshot.cpu_clock = round(sum(core_clocks) / len(core_clocks), 0)

    def _parse_gpu(self, h: Any, snapshot: TelemetrySnapshot) -> None:
        """Извлечение датчиков видеокарты."""
        snapshot.gpu_name = str(h.Name)

        for s in h.Sensors:
            s_val = float(s.Value) if s.Value is not None else None
            if s_val is None:
                continue

            stype = str(s.SensorType)
            sname = str(s.Name)

            if stype == "Temperature":
                if sname == "GPU Core":
                    snapshot.gpu_temp = round(s_val, 1)
                elif "Hot Spot" in sname or "Junction" in sname:
                    snapshot.gpu_hotspot = round(s_val, 1)
            elif stype == "Load":
                if sname == "GPU Core":
                    snapshot.gpu_load = round(s_val, 1)
            elif stype == "SmallData":
                if sname == "GPU Memory Used" or sname == "D3D Dedicated Memory Used":
                    snapshot.gpu_vram_used = round(s_val, 0)
                elif sname == "GPU Memory Total" or sname == "D3D Dedicated Memory Total":
                    snapshot.gpu_vram_total = round(s_val, 0)
            elif stype == "Power":
                if "Package" in sname or "Power" in sname:
                    snapshot.gpu_power = round(s_val, 1)
            elif stype == "Fan":
                if s_val > snapshot.gpu_fan_rpm:
                    snapshot.gpu_fan_rpm = int(s_val)

        # Если хотспот не поддерживается, приравниваем к Core
        if snapshot.gpu_hotspot == 0.0 and snapshot.gpu_temp > 0.0:
            snapshot.gpu_hotspot = snapshot.gpu_temp

    def _parse_memory(self, h: Any, snapshot: TelemetrySnapshot) -> None:
        """Извлечение датчиков оперативной памяти."""
        for s in h.Sensors:
            s_val = float(s.Value) if s.Value is not None else None
            if s_val is None:
                continue

            sname = str(s.Name)
            stype = str(s.SensorType)

            if stype == "Data" and sname == "Memory Used":
                snapshot.ram_used_gb = round(s_val, 2)
            elif stype == "Data" and sname == "Memory Available":
                # Total = Used + Available
                if snapshot.ram_used_gb > 0:
                    snapshot.ram_total_gb = round(snapshot.ram_used_gb + s_val, 2)
            elif stype == "Load" and sname == "Memory":
                snapshot.ram_load_pct = round(s_val, 1)

    def _parse_motherboard(self, h: Any, snapshot: TelemetrySnapshot) -> None:
        """Извлечение кулеров, помпы и VRM датчиков материнской платы."""
        def extract_fans(hardware_obj):
            for s in hardware_obj.Sensors:
                s_val = float(s.Value) if s.Value is not None else None
                if s_val is None:
                    continue
                stype = str(s.SensorType)
                sname = str(s.Name).lower()

                if stype == "Fan":
                    rpm = int(s_val)
                    if "cpu" in sname:
                        snapshot.cpu_fan_rpm = rpm
                    elif "pump" in sname:
                        snapshot.pump_rpm = rpm
                    else:
                        if rpm > 0:
                            snapshot.chassis_fans_rpm.append(rpm)
                elif stype == "Temperature" and ("vrm" in sname or "mos" in sname):
                    snapshot.vrm_temp = round(s_val, 1)

            for sub in hardware_obj.SubHardware:
                extract_fans(sub)

        extract_fans(h)

    def _parse_storage(self, h: Any, snapshot: TelemetrySnapshot) -> None:
        """Извлечение телеметрии накопителей (NVMe / SSD)."""
        if not snapshot.storage_name:
            snapshot.storage_name = str(h.Name)

        for s in h.Sensors:
            s_val = float(s.Value) if s.Value is not None else None
            if s_val is None:
                continue
            stype = str(s.SensorType)
            sname = str(s.Name)

            if stype == "Temperature" and snapshot.storage_temp == 0.0:
                snapshot.storage_temp = round(s_val, 1)
            elif stype == "Load" and ("Activity" in sname or "Total" in sname):
                snapshot.storage_activity = round(s_val, 1)
