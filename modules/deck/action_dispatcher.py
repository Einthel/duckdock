"""
Диспетчер выполнения действий макро-панели DuckDeck (Action Dispatcher).
Выполняет I/O операции в неблокирующем пуле потоков QThreadPool с защитой от
дребезга сенсорного экрана (cooldown 250 мс) и возвратом сигналов в главный поток Qt.
Изолирован от AudioManager через Dependency Injection и platform device switcher.
"""
import ctypes
import logging
import time
from typing import Any, Dict, Optional, Tuple

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from modules.deck.actions.hotkey_sender import send_hotkey
from modules.deck.actions.http_client import execute_http_request
from modules.deck.actions.process_launcher import launch_process
from modules.deck.actions.screen_capture import capture_screen
from modules.deck.models import (
    AudioDeviceParams,
    DeckActionConfig,
    HotkeyParams,
    HttpRequestParams,
    LaunchParams,
    NavigationParams,
    ScreenshotParams,
    SystemParams,
)
from core.event_bus import bus

logger = logging.getLogger("duckdock.deck.dispatcher")


class WorkerSignals(QObject):
    """
    Сигналы возврата результатов выполнения действия в главный GUI поток.
    """
    started = Signal(str)              # button_id
    finished = Signal(str, bool, str)  # button_id, success, message

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)


class ActionRunnable(QRunnable):
    """
    Асинхронная задача выполнения действия в пуле потоков QThreadPool.
    """

    def __init__(
        self,
        button_id: str,
        action_config: DeckActionConfig,
        signals: WorkerSignals,
        audio_manager: Optional[Any] = None,
    ):
        super().__init__()
        self.button_id = button_id
        self.action_config = action_config
        self.signals = signals
        self.audio_manager = audio_manager
        self.setAutoDelete(True)

    def run(self) -> None:
        # Инициализация COM для рабочего потока пула
        com_inited = False
        try:
            import comtypes
            comtypes.CoInitialize()
            com_inited = True
        except Exception:
            pass

        try:
            self.signals.started.emit(self.button_id)
        except Exception:
            pass

        action_type = self.action_config.action_type
        success = False
        message = ""

        try:
            typed_params = self.action_config.get_typed_params()

            if action_type == "hotkey":
                params: HotkeyParams = typed_params
                success = send_hotkey(params.keys)
                message = f"Хоткей {'+'.join(params.keys)}" if success else "Ошибка симуляции хоткея"

            elif action_type == "audio_device":
                params: AudioDeviceParams = typed_params
                if self.audio_manager is not None:
                    if params.mode == "set" and params.target_device_id:
                        success = self.audio_manager.set_default_playback_device(params.target_device_id)
                        message = "Устройство установлено" if success else "Ошибка переключения"
                    else:
                        dev = self.audio_manager.toggle_playback_device(params.devices)
                        success = dev is not None
                        message = f"Аудио: {dev.name}" if dev else "Ошибка переключения аудио"
                else:
                    from modules.audio.platform.device_switcher import (
                        switch_default_device,
                        toggle_audio_device,
                    )
                    if params.mode == "set" and params.target_device_id:
                        success = switch_default_device(params.target_device_id)
                        message = "Устройство установлено" if success else "Ошибка переключения"
                    else:
                        dev = toggle_audio_device(params.devices)
                        success = dev is not None
                        message = f"Аудио: {dev.name}" if dev else "Ошибка переключения аудио"

            elif action_type == "launch":
                params: LaunchParams = typed_params
                success, message = launch_process(
                    path=params.path,
                    args=params.args,
                    working_dir=params.working_dir,
                    detached=params.detached,
                )

            elif action_type == "http_request":
                params: HttpRequestParams = typed_params
                success, code, body = execute_http_request(
                    url=params.url,
                    method=params.method,
                    headers=params.headers,
                    json_body=params.json_body,
                    timeout_sec=params.timeout_sec,
                )
                message = f"HTTP {code}" if success else f"HTTP {code}: {body[:80]}"

            elif action_type == "screenshot":
                params: ScreenshotParams = typed_params
                success, message = capture_screen(
                    target=params.target,
                    clipboard=params.clipboard,
                    save_path=params.save_path,
                )

            elif action_type == "system":
                params: SystemParams = typed_params
                cmd = params.command

                if cmd == "toggle_mic_mute":
                    if self.audio_manager is not None:
                        is_muted = self.audio_manager.toggle_mic_mute()
                    else:
                        from modules.audio.service import AudioManager
                        is_muted = AudioManager().toggle_mic_mute()
                    success = True
                    message = "Микрофон выключен" if is_muted else "Микрофон включен"

                elif cmd == "toggle_master_mute":
                    if self.audio_manager is not None:
                        is_muted = self.audio_manager.toggle_master_mute()
                    else:
                        from modules.audio.service import AudioManager
                        is_muted = AudioManager().toggle_master_mute()
                    success = True
                    message = "Звук выключен" if is_muted else "Звук включен"

                elif cmd == "toggle_playback_device":
                    if self.audio_manager is not None:
                        dev = self.audio_manager.toggle_playback_device()
                    else:
                        from modules.audio.platform.device_switcher import toggle_audio_device
                        dev = toggle_audio_device()
                    success = dev is not None
                    message = f"Аудио: {dev.name}" if dev else "Ошибка переключения аудио"

                elif cmd == "lock_workstation":
                    try:
                        res = ctypes.windll.user32.LockWorkStation()
                        success = bool(res)
                        message = "ПК заблокирован" if success else "Ошибка блокировки"
                    except Exception as lock_err:
                        success = False
                        message = f"Ошибка LockWorkStation: {lock_err}"

                elif cmd == "toggle_dimmer":
                    try:
                        bus.dimmer_toggle_requested.emit()
                        success = True
                        message = "Ночной режим"
                    except Exception as dim_err:
                        success = False
                        message = f"Ошибка диммера: {dim_err}"

                else:
                    success = False
                    message = f"Неизвестная команда: {cmd}"

            elif action_type == "navigation":
                params: NavigationParams = typed_params
                success = True
                message = f"Переход на страницу: {params.target_page_id}"

            else:
                success = False
                message = f"Неподдерживаемый тип действия: {action_type}"

        except Exception as e:
            logger.error(f"Необработанная ошибка выполнения действия '{action_type}': {e}")
            success = False
            message = f"Ошибка: {e}"

        finally:
            try:
                self.signals.finished.emit(self.button_id, success, message)
            except Exception as sig_err:
                logger.debug(f"Ошибка эмиссии finished: {sig_err}")
            if com_inited:
                try:
                    import comtypes
                    comtypes.CoUninitialize()
                except Exception:
                    pass


class DeckActionDispatcher(QObject):
    """
    Центральный диспетчер действий DuckDeck.
    Управляет антидребезгом и распределением задач по потокам с защитой от сборщика мусора.
    """
    action_started = Signal(str)              # button_id
    action_finished = Signal(str, bool, str)  # button_id, success, message

    def __init__(
        self,
        audio_manager: Optional[Any] = None,
        debounce_ms: int = 250,
        thread_pool: Optional[QThreadPool] = None,
        parent: Optional[QObject] = None,
        simulation_mode: bool = False,
    ):
        super().__init__(parent)
        self.audio_manager = audio_manager
        self.debounce_ms = debounce_ms
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._simulation_mode: bool = bool(simulation_mode)
        self._last_trigger_times: Dict[str, float] = {}
        # Защита от преждевременного удаления объектов сборщиком мусора Python (GC)
        self._active_tasks: Dict[str, Tuple[ActionRunnable, WorkerSignals]] = {}
        self.action_finished.connect(self._on_action_finished_cleanup)

    @property
    def simulation_mode(self) -> bool:
        """Режим симуляции (Stubs Mode) без запуска фоновых задач."""
        return self._simulation_mode

    @simulation_mode.setter
    def simulation_mode(self, value: bool) -> None:
        self._simulation_mode = bool(value)

    def _on_action_finished_cleanup(self, button_id: str, success: bool, message: str) -> None:
        """Освобождение сильной ссылки на завершенную задачу."""
        self._active_tasks.pop(button_id, None)

    def dispatch(
        self,
        button_id: Any,
        action_config: DeckActionConfig,
        button_title: Optional[str] = None,
    ) -> bool:
        """
        Отправляет действие на исполнение в пул потоков с защитой от дребезга.
        В режиме simulation_mode воспроизводит тактильный цикл кнопки и эмиттит
        bus.deck_notification без запуска фоновых потоков (сохраняя боевые экшены).
        Возвращает True, если действие принято в обработку, False при срабатывании cooldown.
        """
        # Поддержка передачи объекта кнопки или строки
        if hasattr(button_id, "id"):
            btn_obj = button_id
            button_id = getattr(btn_obj, "id")
            if button_title is None and hasattr(btn_obj, "title"):
                button_title = getattr(btn_obj, "title")

        button_id_str = str(button_id)

        now = time.monotonic()
        last_time = self._last_trigger_times.get(button_id_str, 0.0)
        cooldown_sec = self.debounce_ms / 1000.0

        if now - last_time < cooldown_sec:
            logger.debug(f"Дребезг нажатия кнопки '{button_id_str}' отклонен ({now - last_time:.3f}s < {cooldown_sec}s)")
            return False

        self._last_trigger_times[button_id_str] = now

        # Режим заглушек (Stubs Mode): тактильный цикл + deck_notification без запуска ActionRunnable
        if self._simulation_mode:
            title = button_title if button_title else button_id_str
            stub_msg = f"[Stub Action] {title} (ID: {button_id_str})"
            logger.info("Simulation mode: %s", stub_msg)

            # Воспроизведение тактильного цикла кнопки
            self.action_started.emit(button_id_str)
            self.action_finished.emit(button_id_str, True, stub_msg)

            try:
                bus.deck_notification.emit(stub_msg)
            except Exception as e:
                logger.debug(f"Ошибка эмиссии deck_notification: {e}")

            return True

        # Боевой режим: исполнение в фоновом пуле потоков QThreadPool
        # Создаем сигналы с привязкой родителя к главному объекту диспетчера
        signals = WorkerSignals(self)
        signals.started.connect(self.action_started.emit)
        signals.finished.connect(self.action_finished.emit)

        runnable = ActionRunnable(
            button_id=button_id_str,
            action_config=action_config,
            signals=signals,
            audio_manager=self.audio_manager,
        )

        # Сохраняем сильную ссылку на задачу до ее завершения в главном потоке
        self._active_tasks[button_id_str] = (runnable, signals)
        self.thread_pool.start(runnable)
        return True


__all__ = [
    "WorkerSignals",
    "ActionRunnable",
    "DeckActionDispatcher",
]
