"""
Асинхронный рабочий поток сбора аппаратной телеметрии (TelemetryWorker).
Запускается в изолированном QThread с интервалом 1000 мс, гарантируя 0% нагрузки
на GUI-поток PySide6, отсутствие микрофризов и плавный рендеринг 60 FPS на 7" экране.
"""
import logging
import socket
import time
from typing import List, Optional

from PySide6.QtCore import QThread, Signal

from core.event_bus import bus
from modules.telemetry.hardware_monitor import HardwareMonitor
from modules.telemetry.models import TelemetrySnapshot

logger = logging.getLogger(__name__)


def measure_network_latency(hosts: Optional[List[str]] = None, timeout: float = 0.25) -> float:
    """
    Быстрый замер задержки сети (TCP Connect к DNS 53 / Ping) без необходимости UAC/Raw Sockets.
    Возвращает задержку в мс или -1.0 при отсутствии связи.
    """
    target_hosts = hosts or ["1.1.1.1", "8.8.8.8"]
    for host in target_hosts:
        t0 = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((host, 53))
            s.close()
            return round((time.perf_counter() - t0) * 1000.0, 1)
        except Exception:
            try:
                s.close()
            except Exception:
                pass
            continue
    return -1.0


class TelemetryWorker(QThread):
    """
    Фоновый сборщик телеметрии LHM в QThread.
    Опрашивает датчики HardwareMonitor и замеряет сетевой пинг с тактом 1000 мс.
    """
    snapshot_ready = Signal(object)  # Эмиссия строго типизированного TelemetrySnapshot

    def __init__(self, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self._interval_ms = max(250, interval_ms)
        self._running = False
        self._monitor: Optional[HardwareMonitor] = None
        self._last_snapshot: Optional[TelemetrySnapshot] = None

    @property
    def is_running(self) -> bool:
        """Активен ли цикл сбора."""
        return self._running

    def start(self, priority: QThread.Priority = QThread.Priority.InheritPriority) -> None:
        """Запуск фонового потока."""
        self._running = True
        super().start(priority)

    @property
    def last_snapshot(self) -> Optional[TelemetrySnapshot]:
        """Последний собранный снимок телеметрии."""
        return self._last_snapshot

    def run(self) -> None:
        """Главный рабочий цикл фонового потока."""
        self._running = True
        logger.info(f"TelemetryWorker: поток запущен (интервал {self._interval_ms} мс)")

        self._monitor = HardwareMonitor()
        try:
            self._monitor.open()
        except Exception as e:
            logger.error(f"TelemetryWorker: ошибка открытия HardwareMonitor: {e}")

        while self._running:
            t0 = time.perf_counter()

            try:
                # 1. Замер сетевой задержки (DNS TCP ping, ~0.5-25ms)
                ping_ms = measure_network_latency()

                # 2. Опрос датчиков LibreHardwareMonitor / psutil
                if self._monitor:
                    snapshot = self._monitor.sample(ping_ms=ping_ms)
                else:
                    snapshot = TelemetrySnapshot(ping_ms=ping_ms)

                self._last_snapshot = snapshot

                # 3. Эмиссия типизированного сигнала для подписчиков
                self.snapshot_ready.emit(snapshot)

                # 4. Эмиссия в общую шину событий DuckDock (для совместимости)
                bus.sensors_updated.emit(snapshot.to_dict())

            except Exception as e:
                logger.error(f"TelemetryWorker: ошибка в цикле опроса: {e}", exc_info=True)

            # Точный расчет времени сна до следующего такта
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            remaining_ms = self._interval_ms - elapsed_ms

            if remaining_ms > 0:
                # Дробный сон порциями по 50 мс для мгновенной реакции на stop()
                sleep_chunks = int(remaining_ms // 50)
                rem = remaining_ms % 50
                for _ in range(sleep_chunks):
                    if not self._running:
                        break
                    self.msleep(50)
                if self._running and rem > 0:
                    self.msleep(int(rem))

        # Завершение работы: освобождение Ring 0 драйверов LHM
        if self._monitor:
            try:
                self._monitor.close()
            except Exception as e:
                logger.warning(f"TelemetryWorker: ошибка при закрытии монитора: {e}")
            finally:
                self._monitor = None

        logger.info("TelemetryWorker: поток корректно остановлен")

    def stop(self, timeout_ms: int = 2000) -> None:
        """
        Безопасная остановка фонового потока без зависания GUI.
        """
        self._running = False
        self.wait(timeout_ms)
