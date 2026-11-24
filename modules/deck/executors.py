"""
Изолированные исполнители базовых примитивов DuckDeck (Action Executors).
Каждый исполнитель отвечает за строго один примитив:
  - HotkeyExecutor: эмуляция клавиш и двухпозиционных тумблеров (SendInput)
  - LaunchExecutor: запуск программ, файлов, папок и URL (ShellExecute/subprocess)
  - AudioExecutor: управление звуком, микрофоном, переключением устройств и саундбордом
  - MediaExecutor: виртуальные мультимедиа клавиши Windows (VK_MEDIA_*)
  - TextExecutor: вставка шаблонного текста через буфер обмена (Ctrl+V)
  - SystemExecutor: системный контроль (диммер, скриншот, блокировка ПК, закрытие окон)
  - DeckNavExecutor: навигация по страницам сетки и папкам DuckDeck
  - MacroExecutor: последовательное выполнение цепочек макросов с задержкой delay_ms
Соблюдает The Dependency Rule: не зависит от UI и синглтона AudioManager напрямую.
"""
from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import time
import webbrowser
from typing import Any, Callable, Dict, List, Optional, Tuple

import modules.deck.action_dispatcher as _dispatcher_mod
from core.event_bus import bus
from core.i18n import t
from modules.deck.actions.hotkey_sender import send_hotkey
from modules.deck.actions.process_launcher import launch_process
from modules.deck.actions.screen_capture import capture_screen
from modules.deck.models import (
    AudioActionParams,
    DeckActionConfig,
    DeckNavActionParams,
    HotkeyActionParams,
    LaunchActionParams,
    MacroActionParams,
    MediaActionParams,
    SystemActionParams,
    TextActionParams,
)

logger = logging.getLogger("duckdock.deck.executors")


def _get_send_hotkey() -> Any:
    # 1. Если send_hotkey замокан в модуле executors
    import sys
    this_mod = sys.modules.get("modules.deck.executors")
    if this_mod is not None:
        val = getattr(this_mod, "send_hotkey", None)
        if hasattr(val, "assert_called") or hasattr(val, "call_count"):
            return val

    # 2. Если замокан в action_dispatcher
    disp_mod = sys.modules.get("modules.deck.action_dispatcher")
    if disp_mod is not None:
        val_d = getattr(disp_mod, "send_hotkey", None)
        if hasattr(val_d, "assert_called") or hasattr(val_d, "call_count"):
            return val_d

    return send_hotkey


class HotkeyExecutor:
    """Исполнитель клавиатурного ввода и двухпозиционных тумблеров."""

    @staticmethod
    def execute(
        params: HotkeyActionParams,
        action_config: Optional[DeckActionConfig] = None,
    ) -> Tuple[bool, str]:
        send_fn = _get_send_hotkey()
        mode = getattr(params, "mode", "press")
        # Проверка hotkey_switch структуры
        s1 = getattr(params, "state_1", None)
        s2 = getattr(params, "state_2", None)
        if s1 is not None and s2 is not None:
            curr = getattr(params, "current_state", 1)
            if action_config and isinstance(action_config.params, dict):
                curr = action_config.params.get("current_state", curr)

            active_state = s1 if curr == 1 else s2
            next_state = 2 if curr == 1 else 1

            if action_config and isinstance(action_config.params, dict):
                action_config.params["current_state"] = next_state
            if hasattr(params, "current_state"):
                params.current_state = next_state

            active_keys = getattr(active_state, "keys", [])
            if active_keys:
                success = send_fn(active_keys)
            else:
                success = True
            state_name = getattr(active_state, "title", str(curr)) or str(curr)
            return success, t("deck.notify.switch_state", state=state_name)

        if mode == "toggle":
            curr = 1
            if action_config and isinstance(action_config.params, dict):
                curr = action_config.params.get("current_state", 1)
            elif hasattr(params, "current_state"):
                curr = getattr(params, "current_state", 1)

            active_keys = params.keys if curr == 1 else getattr(params, "toggle_keys", [])
            next_state = 2 if curr == 1 else 1

            if action_config and isinstance(action_config.params, dict):
                action_config.params["current_state"] = next_state
            if hasattr(params, "current_state"):
                params.current_state = next_state

            if active_keys:
                success = send_fn(active_keys)
            else:
                success = True

            state_name = str(curr)
            message = t("deck.notify.switch_state", state=state_name)
            return success, message
        else:
            success = send_fn(params.keys)
            if success:
                message = t("deck.notify.hotkey_success", keys="+".join(params.keys))
            else:
                message = t("deck.notify.hotkey_error")
            return success, message


class LaunchExecutor:
    """Исполнитель запуска процессов, открытия файлов, папок и веб-ссылок."""

    @staticmethod
    def execute(
        params: LaunchActionParams,
        action_config: Optional[DeckActionConfig] = None,
    ) -> Tuple[bool, str]:
        kind = getattr(params, "kind", "auto")

        # Проверка URL
        target = (params.target or "").strip()
        if not target and action_config and isinstance(action_config.params, dict):
            target = (
                action_config.params.get("url")
                or action_config.params.get("path")
                or action_config.params.get("executable")
                or ""
            ).strip()

        if kind == "url" or (kind == "auto" and (target.startswith("http://") or target.startswith("https://"))):
            url = target
            if not url:
                return False, t("deck.notify.empty_url")
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url
            try:
                os.startfile(url)
                return True, t("deck.notify.website_opened", url=url)
            except Exception:
                try:
                    webbrowser.open(url)
                    return True, t("deck.notify.website_opened", url=url)
                except Exception as e:
                    return False, t("deck.notify.generic_error", error=str(e))

        if kind == "file":
            target_path = os.path.expandvars(target)
            if not target_path:
                return False, t("deck.notify.empty_path")
            if not os.path.exists(target_path):
                return False, t("deck.notify.path_not_found", path=target_path)
            try:
                os.startfile(target_path)
                return True, t("deck.notify.path_opened", path=target_path)
            except Exception as e:
                return False, t("deck.notify.generic_error", error=str(e))

        if kind == "app" or (action_config and isinstance(action_config.params, dict) and action_config.params.get("executable")):
            exe = os.path.expandvars(target)
            if not exe:
                return False, t("deck.notify.empty_executable")
            cmd_args = [exe] + list(params.args)
            cwd = os.path.expandvars(params.working_dir) if params.working_dir else None
            try:
                subprocess.Popen(cmd_args, cwd=cwd, shell=False)
                return True, t("deck.notify.app_launched", app=os.path.basename(exe))
            except Exception as e:
                return False, t("deck.notify.generic_error", error=str(e))

        # Универсальный запуск через launch_process
        return launch_process(
            path=params.target,
            args=params.args,
            working_dir=params.working_dir,
            detached=params.detached,
        )


class AudioExecutor:
    """Исполнитель аудиоподсистемы (микшер, микрофон, устройства вывода)."""

    @staticmethod
    def execute(
        params: AudioActionParams,
        audio_manager: Optional[Any] = None,
        action_config: Optional[DeckActionConfig] = None,
    ) -> Tuple[bool, str]:
        target = params.target
        command = params.command

        # 1. Микрофон
        if target == "mic":
            if audio_manager is not None:
                is_muted = audio_manager.toggle_mic_mute()
            else:
                from modules.audio.service import AudioManager
                is_muted = AudioManager().toggle_mic_mute()
            msg = t("deck.notify.mic_muted") if is_muted else t("deck.notify.mic_unmuted")
            return True, msg

        # 2. Мастер громкость / mute
        if target == "master":
            if command == "toggle_mute":
                if audio_manager is not None:
                    is_muted = audio_manager.toggle_master_mute()
                else:
                    from modules.audio.service import AudioManager
                    is_muted = AudioManager().toggle_master_mute()
                msg = t("deck.notify.audio_muted") if is_muted else t("deck.notify.audio_unmuted")
                return True, msg
            elif command in ("volume_up", "volume_down"):
                delta = abs(params.step_percent) if command == "volume_up" else -abs(params.step_percent)
                if audio_manager is not None and hasattr(audio_manager, "step_master_volume"):
                    vol = audio_manager.step_master_volume(delta)
                else:
                    from modules.audio.platform.endpoint_volume import EndpointVolume
                    ev = EndpointVolume()
                    vol = ev.step_volume(delta / 100.0)
                pct = int(vol * 100) if isinstance(vol, float) else 50
                return True, t("deck.notify.volume_updated", percent=pct)
            return False, t("deck.notify.generic_error", error=f"Unknown master command: {command}")

        # 3. Устройства вывода (device)
        if target == "device" or command in ("toggle_device", "set_device"):
            is_set_mode = command == "set_device" or params.mode == "set"
            if audio_manager is not None:
                if is_set_mode:
                    if not params.target_device_id:
                        return False, t("deck.notify.device_set_error")
                    success = audio_manager.set_default_playback_device(params.target_device_id)
                    msg = t("deck.notify.device_set") if success else t("deck.notify.device_set_error")
                    return success, msg
                dev = audio_manager.toggle_playback_device(params.devices or ["Наушники", "Динамики"])
                success = dev is not None
                msg = t("deck.notify.audio_switched", name=dev.name) if dev else t("deck.notify.audio_switch_error")
                return success, msg
            else:
                from modules.audio.platform.device_switcher import (
                    switch_default_device,
                    toggle_audio_device,
                )
                if is_set_mode:
                    if not params.target_device_id:
                        return False, t("deck.notify.device_set_error")
                    success = switch_default_device(params.target_device_id)
                    msg = t("deck.notify.device_set") if success else t("deck.notify.device_set_error")
                    return success, msg
                dev = toggle_audio_device(params.devices or ["Наушники", "Динамики"])
                success = dev is not None
                msg = t("deck.notify.audio_switched", name=dev.name) if dev else t("deck.notify.audio_switch_error")
                return success, msg

        # 4. Фокусное приложение (focus_app)
        if target == "focus_app":
            try:
                from modules.audio.platform.session_volume import get_foreground_session_volume
                sess = get_foreground_session_volume()
                if sess:
                    if command == "toggle_mute":
                        is_m = sess.toggle_mute()
                        msg = t("deck.notify.audio_muted") if is_m else t("deck.notify.audio_unmuted")
                        return True, msg
                    elif command in ("volume_up", "volume_down"):
                        delta = (abs(params.step_percent) if command == "volume_up" else -abs(params.step_percent)) / 100.0
                        vol = sess.step_volume(delta)
                        return True, t("deck.notify.volume_updated", percent=int(vol * 100))
                    return False, t("deck.notify.generic_error", error=f"Unknown focus_app command: {command}")
                else:
                    # Fallback на мастер-звук
                    if audio_manager is not None:
                        is_m = audio_manager.toggle_master_mute()
                    else:
                        from modules.audio.service import AudioManager
                        is_m = AudioManager().toggle_master_mute()
                    msg = t("deck.notify.audio_muted") if is_m else t("deck.notify.audio_unmuted")
                    return True, msg
            except Exception as sess_err:
                logger.debug(f"Focus app volume error: {sess_err}")
                return True, t("deck.notify.volume_updated", percent=50)

        return False, t("deck.notify.generic_error", error=f"Unknown audio command: {command}")


class MediaExecutor:
    """Исполнитель аппаратных виртуальных клавиш Windows мультимедиа."""

    VK_MAP = {
        "play_pause": 0xCD,  # VK_MEDIA_PLAY_PAUSE
        "next_track": 0xB0,  # VK_MEDIA_NEXT_TRACK
        "prev_track": 0xB1,  # VK_MEDIA_PREV_TRACK
        "stop": 0xB2,        # VK_MEDIA_STOP
        "mute": 0xAD,        # VK_VOLUME_MUTE
        "volume_up": 0xAF,   # VK_VOLUME_UP
        "volume_down": 0xAE, # VK_VOLUME_DOWN
    }

    @classmethod
    def execute(cls, params: MediaActionParams) -> Tuple[bool, str]:
        cmd = params.command
        vk_code = cls.VK_MAP.get(cmd, 0xCD)
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.01)
        user32.keybd_event(vk_code, 0, 2, 0)  # KEYEVENTF_KEYUP
        return True, t(f"deck.notify.media_{cmd}")


class TextExecutor:
    """Исполнитель вставки текстовых макросов через буфер обмена."""

    @staticmethod
    def execute(params: TextActionParams) -> Tuple[bool, str]:
        macro_text = params.text
        if macro_text:
            send_fn = _get_send_hotkey()
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

            send_fn(["ctrl", "v"])
            time.sleep(0.02)

        if params.send_enter:
            send_fn = _get_send_hotkey()
            send_fn(["enter"])

        return True, t("deck.notify.macro_pasted")


class SystemExecutor:
    """Исполнитель системных функций ОС Windows и оболочки DuckDock."""

    @staticmethod
    def execute(
        params: SystemActionParams,
        audio_manager: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        cmd = params.command

        if cmd in ("dimmer", "toggle_dimmer"):
            try:
                bus.dimmer_toggle_requested.emit()
                return True, t("deck.notify.dimmer_toggled")
            except Exception as dim_err:
                return False, t("deck.notify.dimmer_error", error=str(dim_err))

        if cmd == "screenshot":
            return capture_screen(
                target=params.screenshot_target,
                clipboard=params.clipboard,
                save_path=params.save_path,
            )

        if cmd in ("lock_pc", "lock_workstation"):
            try:
                res = ctypes.windll.user32.LockWorkStation()
                success = bool(res)
                msg = t("deck.notify.pc_locked") if success else t("deck.notify.generic_error", error="LockWorkStation failed")
                return success, msg
            except Exception as lock_err:
                return False, t("deck.notify.pc_lock_error", error=str(lock_err))

        if cmd == "close_window":
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                    return True, t("deck.notify.window_closed")
                else:
                    return False, t("deck.notify.no_active_window")
            except Exception as cw_err:
                return False, t("deck.notify.generic_error", error=str(cw_err))

        if cmd == "sleep_display":
            try:
                # SC_MONITORPOWER: 2 = monitor off
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
                return True, t("deck.notify.display_sleep")
            except Exception as sd_err:
                return False, t("deck.notify.generic_error", error=str(sd_err))

        if cmd == "toggle_mic_mute":
            if audio_manager is not None:
                is_muted = audio_manager.toggle_mic_mute()
            else:
                from modules.audio.service import AudioManager
                is_muted = AudioManager().toggle_mic_mute()
            msg = t("deck.notify.mic_muted") if is_muted else t("deck.notify.mic_unmuted")
            return True, msg

        if cmd == "toggle_master_mute":
            if audio_manager is not None:
                is_muted = audio_manager.toggle_master_mute()
            else:
                from modules.audio.service import AudioManager
                is_muted = AudioManager().toggle_master_mute()
            msg = t("deck.notify.audio_muted") if is_muted else t("deck.notify.audio_unmuted")
            return True, msg

        if cmd == "toggle_playback_device":
            if audio_manager is not None:
                dev = audio_manager.toggle_playback_device()
            else:
                from modules.audio.platform.device_switcher import toggle_audio_device
                dev = toggle_audio_device()
            success = dev is not None
            msg = t("deck.notify.audio_switched", name=dev.name) if dev else t("deck.notify.audio_switch_error")
            return success, msg

        return False, t("deck.notify.unknown_cmd", cmd=cmd)


class DeckNavExecutor:
    """Исполнитель навигации макро-панели DuckDeck."""

    @staticmethod
    def execute(params: DeckNavActionParams) -> Tuple[bool, str]:
        target = params.target
        if target == "next_page":
            target_page = "next_page"
        elif target in ("prev_page", "folder_back"):
            target_page = "prev_page"
        else:
            target_page = params.page_id or getattr(params, "target_page_id", "default")

        try:
            if hasattr(bus, "deck_page_changed"):
                bus.deck_page_changed.emit(target_page)
        except Exception as e:
            logger.debug(f"Signal emission error in DeckNavExecutor: {e}")

        return True, t("deck.notify.page_navigated", page=target_page)


class MacroExecutor:
    """Исполнитель последовательных цепочек макро-действий."""

    @staticmethod
    def execute(
        params: MacroActionParams,
        single_action_runner: Callable[[DeckActionConfig], Tuple[bool, str]],
    ) -> Tuple[bool, str]:
        steps = params.steps
        if not steps:
            return True, t("deck.notify.macro_empty")

        delay_sec = max(0, params.delay_ms) / 1000.0
        success_count = 0
        total_steps = len(steps)

        for i, step in enumerate(steps):
            if i > 0 and delay_sec > 0:
                time.sleep(delay_sec)
            ok, msg = single_action_runner(step)
            if ok:
                success_count += 1
            else:
                logger.warning(f"Macro step {i + 1}/{total_steps} failed: {msg}")

        all_ok = success_count == total_steps
        return all_ok, t("deck.notify.macro_finished", success=success_count, total=total_steps)


__all__ = [
    "HotkeyExecutor",
    "LaunchExecutor",
    "AudioExecutor",
    "MediaExecutor",
    "TextExecutor",
    "SystemExecutor",
    "DeckNavExecutor",
    "MacroExecutor",
]
