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
    CloseWindowParams,
    DeckActionConfig,
    HotkeyParams,
    HotkeySwitchParams,
    HttpRequestParams,
    LaunchParams,
    MultimediaParams,
    NavigationParams,
    OpenAppParams,
    OpenPathParams,
    ScreenshotParams,
    SoundboardParams,
    SystemParams,
    TextMacroParams,
    VolumeControlParams,
    WebsiteParams,
)
from core.event_bus import bus
from core.i18n import t

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
                message = t("deck.notify.hotkey_success", keys='+'.join(params.keys)) if success else t("deck.notify.hotkey_error")

            elif action_type == "audio_device":
                params: AudioDeviceParams = typed_params
                if self.audio_manager is not None:
                    if params.mode == "set" and params.target_device_id:
                        success = self.audio_manager.set_default_playback_device(params.target_device_id)
                        message = t("deck.notify.device_set") if success else t("deck.notify.device_set_error")
                    else:
                        dev = self.audio_manager.toggle_playback_device(params.devices)
                        success = dev is not None
                        message = t("deck.notify.audio_switched", name=dev.name) if dev else t("deck.notify.audio_switch_error")
                else:
                    from modules.audio.platform.device_switcher import (
                        switch_default_device,
                        toggle_audio_device,
                    )
                    if params.mode == "set" and params.target_device_id:
                        success = switch_default_device(params.target_device_id)
                        message = t("deck.notify.device_set") if success else t("deck.notify.device_set_error")
                    else:
                        dev = toggle_audio_device(params.devices)
                        success = dev is not None
                        message = t("deck.notify.audio_switched", name=dev.name) if dev else t("deck.notify.audio_switch_error")

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
                    message = t("deck.notify.mic_muted") if is_muted else t("deck.notify.mic_unmuted")

                elif cmd == "toggle_master_mute":
                    if self.audio_manager is not None:
                        is_muted = self.audio_manager.toggle_master_mute()
                    else:
                        from modules.audio.service import AudioManager
                        is_muted = AudioManager().toggle_master_mute()
                    success = True
                    message = t("deck.notify.audio_muted") if is_muted else t("deck.notify.audio_unmuted")

                elif cmd == "toggle_playback_device":
                    if self.audio_manager is not None:
                        dev = self.audio_manager.toggle_playback_device()
                    else:
                        from modules.audio.platform.device_switcher import toggle_audio_device
                        dev = toggle_audio_device()
                    success = dev is not None
                    message = t("deck.notify.audio_switched", name=dev.name) if dev else t("deck.notify.audio_switch_error")

                elif cmd == "lock_workstation":
                    try:
                        res = ctypes.windll.user32.LockWorkStation()
                        success = bool(res)
                        message = t("deck.notify.pc_locked") if success else t("deck.notify.generic_error", error="LockWorkStation failed")
                    except Exception as lock_err:
                        success = False
                        message = t("deck.notify.pc_lock_error", error=str(lock_err))

                elif cmd == "toggle_dimmer":
                    try:
                        bus.dimmer_toggle_requested.emit()
                        success = True
                        message = t("deck.notify.dimmer_toggled")
                    except Exception as dim_err:
                        success = False
                        message = t("deck.notify.dimmer_error", error=str(dim_err))

                else:
                    success = False
                    message = t("deck.notify.unknown_cmd", cmd=cmd)

            elif action_type == "navigation":
                params: NavigationParams = typed_params
                success = True
                message = t("deck.notify.page_navigated", page=params.target_page_id)

            elif action_type == "website":
                wb_params: WebsiteParams = typed_params
                url = wb_params.url.strip()
                if not url:
                    success = False
                    message = t("deck.notify.empty_url")
                else:
                    if not (url.startswith("http://") or url.startswith("https://")):
                        url = "https://" + url
                    try:
                        import os
                        os.startfile(url)
                        success = True
                        message = t("deck.notify.website_opened", url=url)
                    except Exception:
                        import webbrowser
                        webbrowser.open(url)
                        success = True
                        message = t("deck.notify.website_opened", url=url)

            elif action_type == "open_path":
                p_params: OpenPathParams = typed_params
                import os
                target_path = os.path.expandvars(p_params.path.strip())
                if not target_path:
                    success = False
                    message = t("deck.notify.empty_path")
                elif not os.path.exists(target_path):
                    success = False
                    message = t("deck.notify.path_not_found", path=target_path)
                else:
                    os.startfile(target_path)
                    success = True
                    message = t("deck.notify.path_opened", path=target_path)

            elif action_type == "open_app":
                oa_params: OpenAppParams = typed_params
                import os
                import subprocess
                exe = os.path.expandvars(oa_params.executable.strip())
                if not exe:
                    success = False
                    message = t("deck.notify.empty_executable")
                else:
                    cmd_args = [exe] + list(oa_params.args)
                    cwd = os.path.expandvars(oa_params.working_dir) if oa_params.working_dir else None
                    subprocess.Popen(cmd_args, cwd=cwd, shell=False)
                    success = True
                    message = t("deck.notify.app_launched", app=os.path.basename(exe))

            elif action_type == "close_window":
                cw_params: CloseWindowParams = typed_params
                target = cw_params.target
                try:
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                    if hwnd:
                        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                        success = True
                        message = t("deck.notify.window_closed")
                    else:
                        success = False
                        message = t("deck.notify.no_active_window")
                except Exception as cw_err:
                    success = False
                    message = t("deck.notify.generic_error", error=str(cw_err))

            elif action_type == "text_macro":
                tm_params: TextMacroParams = typed_params
                macro_text = tm_params.text
                if macro_text:
                    try:
                        import win32clipboard
                        win32clipboard.OpenClipboard()
                        try:
                            win32clipboard.EmptyClipboard()
                            win32clipboard.SetClipboardText(macro_text, win32clipboard.CF_UNICODETEXT)
                        finally:
                            win32clipboard.CloseClipboard()
                    except Exception as clip_err:
                        logger.debug(f"win32clipboard copy error: {clip_err}")

                    send_hotkey(["ctrl", "v"])
                    time.sleep(0.02)

                if tm_params.send_enter:
                    send_hotkey(["enter"])

                success = True
                message = t("deck.notify.macro_pasted")

            elif action_type == "multimedia":
                mm_params: MultimediaParams = typed_params
                vk_map = {
                    "play_pause": 0xCD,  # VK_MEDIA_PLAY_PAUSE
                    "next_track": 0xB0,  # VK_MEDIA_NEXT_TRACK
                    "prev_track": 0xB1,  # VK_MEDIA_PREV_TRACK
                    "stop": 0xB2,        # VK_MEDIA_STOP
                    "mute": 0xAD,        # VK_VOLUME_MUTE
                    "volume_up": 0xAF,   # VK_VOLUME_UP
                    "volume_down": 0xAE, # VK_VOLUME_DOWN
                }
                vk_code = vk_map.get(mm_params.command, 0xCD)
                user32 = ctypes.windll.user32
                user32.keybd_event(vk_code, 0, 0, 0)
                time.sleep(0.01)
                user32.keybd_event(vk_code, 0, 2, 0)  # KEYEVENTF_KEYUP
                success = True
                message = t(f"deck.notify.media_{mm_params.command}")

            elif action_type == "volume_control":
                vc_params: VolumeControlParams = typed_params
                if vc_params.target == "microphone":
                    if self.audio_manager is not None:
                        is_muted = self.audio_manager.toggle_mic_mute()
                    else:
                        from modules.audio.service import AudioManager
                        is_muted = AudioManager().toggle_mic_mute()
                    success = True
                    message = t("deck.notify.mic_muted") if is_muted else t("deck.notify.mic_unmuted")
                elif vc_params.target == "master":
                    if vc_params.command == "toggle_mute":
                        if self.audio_manager is not None:
                            is_muted = self.audio_manager.toggle_master_mute()
                        else:
                            from modules.audio.service import AudioManager
                            is_muted = AudioManager().toggle_master_mute()
                        success = True
                        message = t("deck.notify.audio_muted") if is_muted else t("deck.notify.audio_unmuted")
                    elif vc_params.command in ("volume_up", "volume_down"):
                        delta = vc_params.step_percent if vc_params.command == "volume_up" else -vc_params.step_percent
                        if self.audio_manager is not None and hasattr(self.audio_manager, "step_master_volume"):
                            vol = self.audio_manager.step_master_volume(delta)
                        else:
                            from modules.audio.platform.endpoint_volume import EndpointVolume
                            ev = EndpointVolume()
                            vol = ev.step_volume(delta / 100.0)
                        success = True
                        pct = int(vol * 100) if isinstance(vol, float) else 50
                        message = t("deck.notify.volume_updated", percent=pct)
                    else:
                        success = True
                        message = t("deck.notify.volume_updated", percent=50)
                else:  # focus_app
                    try:
                        from modules.audio.platform.session_volume import get_foreground_session_volume
                        sess = get_foreground_session_volume()
                        if sess:
                            if vc_params.command == "toggle_mute":
                                is_m = sess.toggle_mute()
                                message = t("deck.notify.audio_muted") if is_m else t("deck.notify.audio_unmuted")
                            else:
                                delta = (vc_params.step_percent if vc_params.command == "volume_up" else -vc_params.step_percent) / 100.0
                                vol = sess.step_volume(delta)
                                message = t("deck.notify.volume_updated", percent=int(vol * 100))
                            success = True
                        else:
                            if self.audio_manager is not None:
                                is_m = self.audio_manager.toggle_master_mute()
                            else:
                                from modules.audio.service import AudioManager
                                is_m = AudioManager().toggle_master_mute()
                            success = True
                            message = t("deck.notify.audio_muted") if is_m else t("deck.notify.audio_unmuted")
                    except Exception as sess_err:
                        logger.debug(f"Focus app volume error: {sess_err}")
                        success = True
                        message = t("deck.notify.volume_updated", percent=50)

            elif action_type == "hotkey_switch":
                hs_params: HotkeySwitchParams = typed_params
                curr = getattr(hs_params, "current_state", 1)
                active_state = hs_params.state_1 if curr == 1 else hs_params.state_2
                next_state = 2 if curr == 1 else 1
                hs_params.current_state = next_state
                if isinstance(self.action_config.params, dict):
                    self.action_config.params["current_state"] = next_state
                if active_state.keys:
                    success = send_hotkey(active_state.keys)
                    state_name = active_state.title or str(curr)
                    message = t("deck.notify.switch_state", state=state_name)
                else:
                    success = True
                    state_name = active_state.title or str(curr)
                    message = t("deck.notify.switch_state", state=state_name)

            elif action_type == "play_audio":
                pa_params: SoundboardParams = typed_params
                f_path = (pa_params.file_path or self.action_config.params.get("file_path", "")).strip()
                vol = pa_params.volume if hasattr(pa_params, "volume") else 1.0
                stop_oth = pa_params.stop_others if hasattr(pa_params, "stop_others") else False
                if not f_path:
                    success = False
                    message = t("deck.notify.empty_path")
                else:
                    self.signals.play_sound_requested.emit(f_path, vol, stop_oth)
                    success = True
                    import os
                    message = t("deck.notify.sound_played", sound=os.path.basename(f_path))

            elif action_type == "stop_audio":
                self.signals.stop_sound_requested.emit()
                success = True
                message = t("deck.notify.soundboard_stopped")

            else:
                success = False
                message = t("deck.notify.unsupported_action", action=action_type)

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
        signals.play_sound_requested.connect(self._on_play_sound_requested)
        signals.stop_sound_requested.connect(self._on_stop_sound_requested)

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
        action_type = action_config.action_type
        if action_type == "play_audio":
            typed = action_config.get_typed_params()
            f_path = (getattr(typed, "file_path", None) or action_config.params.get("file_path", "")).strip()
            vol = getattr(typed, "volume", 1.0)
            stop_oth = getattr(typed, "stop_others", False)
            if not f_path:
                return False, t("deck.notify.empty_path")
            if sound_engine is not None:
                success = sound_engine.play_soundboard(f_path, vol, stop_oth)
            else:
                from modules.deck.sound_engine import DeckSoundEngine
                success = DeckSoundEngine().play_soundboard(f_path, vol, stop_oth)
            import os
            msg = t("deck.notify.sound_played", sound=os.path.basename(f_path)) if success else t("deck.notify.generic_error", error="file not found")
            return success, msg

        if action_type == "stop_audio":
            if sound_engine is not None:
                sound_engine.stop_soundboard()
            return True, t("deck.notify.soundboard_stopped")

        # Для остальных действий используем логику ActionRunnable
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
        )
        runnable.run()
        return result[0], result[1]


__all__ = [
    "WorkerSignals",
    "ActionRunnable",
    "DeckActionDispatcher",
]
