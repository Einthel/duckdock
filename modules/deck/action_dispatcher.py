"""
Диспетчер выполнения действий макро-панели DuckDeck (Action Dispatcher).
Выполняет I/O операции в неблокирующем пуле потоков QThreadPool с защитой от
дребезга сенсорного экрана (cooldown 250 мс) и возвратом сигналов в главный поток Qt.
Делегирует исполнение примитивов изолированным исполнителям слоя executors.
Изолирован от AudioManager через Dependency Injection и platform device switcher.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from core.event_bus import bus
from core.i18n import t
from modules.deck.actions.hotkey_sender import send_hotkey
from modules.deck.actions.http_client import execute_http_request
from modules.deck.actions.process_launcher import launch_process
from modules.deck.actions.screen_capture import capture_screen
from modules.deck.executors import (
    AudioExecutor,
    DeckNavExecutor,
    HotkeyExecutor,
    LaunchExecutor,
    MacroExecutor,
    MediaExecutor,
    SystemExecutor,
    TextExecutor,
)
from modules.deck.models import (
    AudioActionParams,
    AudioDeviceParams,
    CloseWindowParams,
    DeckActionConfig,
    DeckNavActionParams,
    HotkeyActionParams,
    HotkeySwitchParams,
    HttpRequestParams,
    LaunchActionParams,
    LaunchParams,
    MacroActionParams,
    MediaActionParams,
    MultimediaParams,
    NavigationParams,
    OpenAppParams,
    OpenPathParams,
    ScreenshotParams,
    SoundboardParams,
    SystemActionParams,
    SystemParams,
    TextActionParams,
    TextMacroParams,
    VolumeControlParams,
    WebsiteParams,
)

logger = logging.getLogger("duckdock.deck.dispatcher")


class WorkerSignals(QObject):
    """
    Сигналы возврата результатов выполнения действия в главный GUI поток.
    """
    started = Signal(str)              # button_id
    finished = Signal(str, bool, str)  # button_id, success, message
    play_sound_requested = Signal(str, float, bool)  # file_path, volume, stop_others
    stop_sound_requested = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)


class ActionRunnable(QRunnable):
    """
    Асинхронная задача выполнения действия в пуле потоков QThreadPool.
    Использует строгий match-case по 8 базовым примитивам, делегируя исполнение в executors.
    """

    def __init__(
        self,
        button_id: str,
        action_config: DeckActionConfig,
        signals: WorkerSignals,
        audio_manager: Optional[Any] = None,
        sound_engine: Optional[Any] = None,
    ):
        super().__init__()
        self.button_id = button_id
        self.action_config = action_config
        self.signals = signals
        self.audio_manager = audio_manager
        self.sound_engine = sound_engine
        self.setAutoDelete(True)

    def _execute_sub_action(self, action_config: DeckActionConfig) -> Tuple[bool, str]:
        """Исполняет одиночное действие внутри того же потока (для цепочек макросов)."""
        return self._run_action_config(action_config)

    def _run_action_config(self, cfg: DeckActionConfig) -> Tuple[bool, str]:
        action_type = cfg.action_type
        typed_params = cfg.get_typed_params()

        match action_type:
            case "hotkey":
                return HotkeyExecutor.execute(typed_params, action_config=cfg)

            case "launch":
                return LaunchExecutor.execute(typed_params, action_config=cfg)

            case "audio" | "audio_device" | "volume_control":
                # Конвертация VolumeControlParams в AudioActionParams если необходимо
                if isinstance(typed_params, VolumeControlParams):
                    cmd_val = "toggle_mute" if typed_params.command == "toggle_mute" else "step"
                    step_val = typed_params.step_percent if typed_params.command == "volume_up" else -typed_params.step_percent
                    target_val = "mic" if typed_params.target in ("mic", "microphone") else ("focus_app" if typed_params.target == "focus_app" else "master")
                    audio_p = AudioActionParams(
                        target=target_val,
                        command=cmd_val,
                        step_percent=step_val,
                    )
                else:
                    audio_p = typed_params
                return AudioExecutor.execute(
                    params=audio_p,
                    audio_manager=self.audio_manager,
                    sound_engine=self.sound_engine,
                    play_sound_emitter=self.signals.play_sound_requested.emit,
                    stop_sound_emitter=self.signals.stop_sound_requested.emit,
                    action_config=cfg,
                )

            case "media" | "multimedia":
                return MediaExecutor.execute(typed_params)

            case "text" | "text_macro":
                return TextExecutor.execute(typed_params)

            case "system":
                return SystemExecutor.execute(typed_params, audio_manager=self.audio_manager)

            case "deck_nav" | "navigation":
                return DeckNavExecutor.execute(typed_params)

            case "macro":
                return MacroExecutor.execute(typed_params, single_action_runner=self._execute_sub_action)

            # Legacy fallback cases для абсолютной обратной совместимости
            case "hotkey_switch":
                return HotkeyExecutor.execute(typed_params, action_config=cfg)

            case "website" | "open_path" | "open_app":
                return LaunchExecutor.execute(typed_params, action_config=cfg)

            case "screenshot":
                p: ScreenshotParams = typed_params
                return capture_screen(
                    target=p.target,
                    clipboard=p.clipboard,
                    save_path=p.save_path,
                )

            case "close_window":
                p_cw: CloseWindowParams = typed_params
                return SystemExecutor.execute(
                    SystemActionParams(command="close_window"),
                    audio_manager=self.audio_manager,
                )

            case "play_audio":
                p_sb: SoundboardParams = typed_params
                f_path = (p_sb.file_path or cfg.params.get("file_path", "")).strip()
                vol = getattr(p_sb, "volume", 1.0)
                stop_oth = getattr(p_sb, "stop_others", False)
                return AudioExecutor.execute(
                    params=AudioActionParams(
                        target="soundboard",
                        command="play_sound",
                        file_path=f_path,
                        volume=vol,
                        stop_others=stop_oth,
                    ),
                    audio_manager=self.audio_manager,
                    sound_engine=self.sound_engine,
                    play_sound_emitter=self.signals.play_sound_requested.emit,
                    stop_sound_emitter=self.signals.stop_sound_requested.emit,
                    action_config=cfg,
                )

            case "stop_audio":
                return AudioExecutor.execute(
                    params=AudioActionParams(
                        target="soundboard",
                        command="stop_sound",
                    ),
                    audio_manager=self.audio_manager,
                    sound_engine=self.sound_engine,
                    play_sound_emitter=self.signals.play_sound_requested.emit,
                    stop_sound_emitter=self.signals.stop_sound_requested.emit,
                    action_config=cfg,
                )

            case "http_request":
                hr_params: HttpRequestParams = typed_params
                success, code, body = execute_http_request(
                    url=hr_params.url,
                    method=hr_params.method,
                    headers=hr_params.headers,
                    json_body=hr_params.json_body,
                    timeout_sec=hr_params.timeout_sec,
                )
                msg = f"HTTP {code}" if success else f"HTTP {code}: {body[:80]}"
                return success, msg

            case _:
                return False, t("deck.notify.unsupported_action", action=action_type)

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
            success, message = self._run_action_config(self.action_config)
        except Exception as e:
            logger.error(f"Необработанная ошибка выполнения действия '{action_type}': {e}")
            success = False
            message = t("deck.notify.generic_error", error=str(e))
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
        sound_engine: Optional[Any] = None,
        debounce_ms: int = 250,
        thread_pool: Optional[QThreadPool] = None,
        parent: Optional[QObject] = None,
        simulation_mode: bool = False,
    ):
        super().__init__(parent)
        self.audio_manager = audio_manager
        self.sound_engine = sound_engine
        self.debounce_ms = debounce_ms
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._simulation_mode: bool = bool(simulation_mode)
        self._last_trigger_times: Dict[str, float] = {}
        # Защита от преждевременного удаления объектов сборщиком мусора Python (GC)
        self._active_tasks: Dict[str, Tuple[ActionRunnable, WorkerSignals]] = {}
        self.action_finished.connect(self._on_action_finished_cleanup)

    def _on_play_sound_requested(self, file_path: str, volume: float, stop_others: bool) -> None:
        """Слот воспроизведения звука саундборда в главном UI потоке."""
        if self.sound_engine is not None:
            self.sound_engine.play_soundboard(file_path, volume, stop_others)

    def _on_stop_sound_requested(self) -> None:
        """Слот остановки саундборда в главном UI потоке."""
        if self.sound_engine is not None:
            self.sound_engine.stop_soundboard()

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
        Возвращает True, если действие принято в обработку, False при срабатывании cooldown.
        """
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

        # Режим заглушек (Stubs Mode)
        if self._simulation_mode:
            title = button_title if button_title else button_id_str
            stub_msg = f"[Stub Action] {title} (ID: {button_id_str})"
            logger.info("Simulation mode: %s", stub_msg)

            self.action_started.emit(button_id_str)
            self.action_finished.emit(button_id_str, True, stub_msg)

            try:
                bus.deck_notification.emit(stub_msg)
            except Exception as e:
                logger.debug(f"Ошибка эмиссии deck_notification: {e}")

            return True

        # Боевой режим
        signals = WorkerSignals(self)
        signals.started.connect(self.action_started.emit)
        signals.finished.connect(self.action_finished.emit)
        signals.play_sound_requested.connect(self._on_play_sound_requested)
        signals.stop_sound_requested.connect(self._on_stop_sound_requested)

        runnable = ActionRunnable(
            button_id=button_id_str,
            action_config=action_config,
            signals=signals,
            audio_manager=self.audio_manager,
            sound_engine=self.sound_engine,
        )

        self._active_tasks[button_id_str] = (runnable, signals)
        self.thread_pool.start(runnable)
        return True

    @classmethod
    def execute_action(
        cls,
        action_config: DeckActionConfig,
        audio_manager: Optional[Any] = None,
        sound_engine: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """
        Синхронный запуск действия кнопки (для быстрого тестирования '▶ Тест' из инспектора).
        """
        class SyncSignals(QObject):
            started = Signal(str)
            finished = Signal(str, bool, str)
            play_sound_requested = Signal(str, float, bool)
            stop_sound_requested = Signal()

        sig = SyncSignals()
        result = [False, ""]

        def on_finished(bid, ok, msg):
            result[0] = ok
            result[1] = msg

        sig.finished.connect(on_finished)
        if sound_engine is not None:
            sig.play_sound_requested.connect(sound_engine.play_soundboard)
            sig.stop_sound_requested.connect(sound_engine.stop_soundboard)

        runnable = ActionRunnable(
            button_id="test_run",
            action_config=action_config,
            signals=sig,
            audio_manager=audio_manager,
            sound_engine=sound_engine,
        )
        runnable.run()
        return result[0], result[1]


__all__ = [
    "WorkerSignals",
    "ActionRunnable",
    "DeckActionDispatcher",
]
