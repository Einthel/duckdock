"""
Декларативные Pydantic v2 модели и схемы конфигурации макро-панели DuckDeck.
Поддерживает 8 ортогональных базовых примитивов и прозрачную нормализацию legacy-конфигураций.
"""
import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ValidationError, model_validator

from modules.audio.models import AudioDeviceInfo

logger = logging.getLogger("duckdock.deck.models")

# -------------------------------------------------------------
# 8 Базовых ортогональных примитивов DuckDeck
# -------------------------------------------------------------
ActionType = Literal[
    "hotkey",    # Клавиатурный ввод и двухпозиционные тумблеры
    "launch",    # Запуск процессов, файлов, папок и веб-ссылок
    "audio",     # Громкость, микрофон, переключение устройств и саундборд
    "media",     # Мультимедийные клавиши Windows
    "text",      # Текстовые сниппеты с авто-вставкой
    "system",    # Системные функции (диммер, скриншот, блокировка)
    "deck_nav",  # Навигация по страницам и папкам макро-панели
    "macro",     # Последовательные цепочки действий
]

ActionCategory = Literal[
    "system",         # Системные операции (звук, микрофон, скриншот, диммер, папки)
    "shortcut",       # Клавиатурные сочетания и хоткеи
    "program",        # Запуск внешних программ и скриптов
    "api",            # REST API запросы к сторонним сервисам
    "navigation",     # Навигация (страницы, профили, папки)
    "soundboard",     # Саундборд (воспроизведение и остановка аудио)
    "stream_deck",    # Управление стримдеком и экраном
    "multi_action",   # Мульти-действия и макро-цепочки
]


# -------------------------------------------------------------
# Типизированные Pydantic v2 модели параметров для 8 примитивов
# -------------------------------------------------------------
class HotkeyActionParams(BaseModel):
    """Параметры симуляции горячих клавиш и двухпозиционных тумблеров."""
    keys: List[str] = Field(default_factory=list, description="Список клавиш (например ['ctrl', 'shift', 'd'])")
    mode: Literal["press", "toggle"] = Field(default="press", description="Режим: press (одиночный) или toggle (тумблер)")
    toggle_keys: List[str] = Field(default_factory=list, description="Вторая комбинация клавиш для тумблера")


class LaunchActionParams(BaseModel):
    """Параметры запуска процессов, файлов, папок и веб-ссылок."""
    target: str = Field(default="", description="Путь к .exe, файлу, папке или URL")
    args: List[str] = Field(default_factory=list, description="Аргументы командной строки")
    working_dir: Optional[str] = Field(default=None, description="Рабочая директория")
    kind: Literal["auto", "app", "file", "url"] = Field(default="auto", description="Тип запускаемой цели")
    detached: bool = Field(default=True, description="Запуск в фоновом изолированном процессе")

    @property
    def path(self) -> str:
        return self.target

    @path.setter
    def path(self, val: str) -> None:
        self.target = val


class AudioActionParams(BaseModel):
    """Параметры аудиоподсистемы (микшер, устройства, микрофон, саундборд)."""
    target: Literal["master", "focus_app", "mic", "device", "soundboard"] = Field(
        default="master", description="Цель управления звуком"
    )
    command: Literal["toggle_mute", "step", "set_level", "toggle_device", "play_sound", "stop_sound"] = Field(
        default="toggle_mute", description="Команда аудиоподсистемы"
    )
    step_percent: int = Field(default=5, description="Шаг изменения громкости в процентах")
    devices: List[str] = Field(
        default_factory=lambda: ["Наушники", "Динамики"],
        description="Ключевые слова или имена устройств для переключения",
    )
    file_path: str = Field(default="", description="Путь к аудиофайлу для саундборда")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Громкость воспроизведения звука (0.0..1.0)")
    stop_others: bool = Field(default=False, description="Останавливать ли другие звуки саундборда")
    mode: Literal["toggle", "set", "cycle"] = Field(default="toggle", description="Режим переключения устройств")
    target_device_id: Optional[str] = Field(default=None, description="Точный ID устройства для режима 'set'")


class MediaActionParams(BaseModel):
    """Параметры мультимедийного управления Windows."""
    command: Literal[
        "play_pause",
        "next_track",
        "prev_track",
        "stop",
        "volume_up",
        "volume_down",
    ] = Field(default="play_pause", description="Мультимедийная команда")


class TextActionParams(BaseModel):
    """Параметры текстового макроса."""
    text: str = Field(default="", description="Вставляемый текст")
    send_enter: bool = Field(default=False, description="Отправить Enter после вставки")


class SystemActionParams(BaseModel):
    """Параметры системного контроля (Windows и DuckDock)."""
    command: Literal[
        "dimmer",
        "screenshot",
        "lock_pc",
        "sleep_display",
        "close_window",
        "toggle_dimmer",
        "lock_workstation",
        "toggle_mic_mute",
        "toggle_master_mute",
        "toggle_playback_device",
    ] = Field(default="dimmer", description="Системная команда")
    screenshot_target: Literal["primary", "active_window"] = Field(
        default="primary", description="Цель скриншота"
    )
    clipboard: bool = Field(default=True, description="Поместить результат в буфер обмена")
    save_path: Optional[str] = Field(default=None, description="Опциональный путь для сохранения файла")


class DeckNavActionParams(BaseModel):
    """Параметры навигации DuckDeck."""
    target: Literal["next_page", "prev_page", "goto_page", "folder_open", "folder_back"] = Field(
        default="next_page", description="Цель навигации"
    )
    page_id: Optional[str] = Field(default=None, description="ID целевой страницы профиля")

    @property
    def target_page_id(self) -> str:
        return self.page_id or "default"

    @target_page_id.setter
    def target_page_id(self, val: str) -> None:
        self.page_id = val


class MacroActionParams(BaseModel):
    """Параметры макро-цепочки действий."""
    steps: List["DeckActionConfig"] = Field(default_factory=list, description="Последовательные шаги макроса")
    delay_ms: int = Field(default=50, ge=0, le=5000, description="Задержка между шагами в миллисекундах")


class ActionPresetDefinition(BaseModel):
    """Декларативное описание готового шаблона (пресета) действия DuckDeck."""
    id: str = Field(description="Уникальный ID пресета (например 'discord_mute')")
    category: str = Field(description="ID категории из таксономии ('audio_comm')")
    title_key: str = Field(description="Ключ локализации названия")
    desc_key: str = Field(description="Ключ локализации описания/тултипа")
    icon: str = Field(description="Эмодзи или иконка по умолчанию")
    color_accent: str = Field(description="Неоновый цвет акцента по умолчанию")
    status_source: Optional[str] = Field(default=None, description="Источник Live-статуса ('mic_mute', 'audio_device', 'dimmer')")
    base_action: "DeckActionConfig" = Field(description="Сконфигурированный базовый примитив")
    keywords: List[str] = Field(default_factory=list, description="Двуязычные поисковые теги (RU/EN)")


# -------------------------------------------------------------
# Устаревшие модели параметров (Backward Compatibility Shims)
# -------------------------------------------------------------
HotkeyParams = HotkeyActionParams
LaunchParams = LaunchActionParams
AudioDeviceParams = AudioActionParams
MultimediaParams = MediaActionParams
TextMacroParams = TextActionParams
SystemParams = SystemActionParams
NavigationParams = DeckNavActionParams


class HotkeySwitchState(BaseModel):
    title: str = Field(default="", description="Название состояния")
    keys: List[str] = Field(default_factory=list, description="Список клавиш")
    icon: Optional[str] = Field(default=None, description="Иконка состояния")


class HotkeySwitchParams(HotkeyActionParams):
    state_1: HotkeySwitchState = Field(default_factory=HotkeySwitchState, description="Состояние 1")
    state_2: HotkeySwitchState = Field(default_factory=HotkeySwitchState, description="Состояние 2")
    current_state: int = Field(default=1, ge=1, le=2, description="Текущее активное состояние")
    mode: Literal["press", "toggle"] = "toggle"

    @model_validator(mode="before")
    @classmethod
    def _sync_switch(cls, data: Any) -> Any:
        if isinstance(data, dict):
            s1 = data.get("state_1")
            s2 = data.get("state_2")
            if isinstance(s1, dict):
                data.setdefault("keys", s1.get("keys", []))
            if isinstance(s2, dict):
                data.setdefault("toggle_keys", s2.get("keys", []))
            if "keys" in data and not s1:
                data["state_1"] = HotkeySwitchState(title="S1", keys=data["keys"])
            if "toggle_keys" in data and not s2:
                data["state_2"] = HotkeySwitchState(title="S2", keys=data["toggle_keys"])
            data["mode"] = "toggle"
        return data


class WebsiteParams(LaunchActionParams):
    url: str = Field(default="", description="URL адрес сайта")
    kind: Literal["auto", "app", "file", "url"] = "url"

    @model_validator(mode="before")
    @classmethod
    def _sync_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url_val = data.get("url") or data.get("target", "")
            data["target"] = url_val
            data["url"] = url_val
            data["kind"] = "url"
        return data


class OpenPathParams(LaunchActionParams):
    kind: Literal["auto", "app", "file", "url"] = "file"

    @model_validator(mode="before")
    @classmethod
    def _sync_path(cls, data: Any) -> Any:
        if isinstance(data, dict):
            path_val = data.get("path") or data.get("target", "")
            data["target"] = path_val
            data["kind"] = "file"
        return data


class OpenAppParams(LaunchActionParams):
    executable: str = Field(default="", description="Путь к исполняемому файлу")
    kind: Literal["auto", "app", "file", "url"] = "app"

    @model_validator(mode="before")
    @classmethod
    def _sync_exe(cls, data: Any) -> Any:
        if isinstance(data, dict):
            exe_val = data.get("executable") or data.get("path") or data.get("target", "")
            data["target"] = exe_val
            data["executable"] = exe_val
            data["kind"] = "app"
        return data


class CloseWindowParams(SystemActionParams):
    command: Literal[
        "dimmer",
        "screenshot",
        "lock_pc",
        "sleep_display",
        "close_window",
        "toggle_dimmer",
        "lock_workstation",
        "toggle_mic_mute",
        "toggle_master_mute",
        "toggle_playback_device",
    ] = "close_window"
    target: Literal["active_window", "by_process"] = Field(default="active_window", description="Цель закрытия")
    process_name: Optional[str] = Field(default=None, description="Имя процесса")


class VolumeControlParams(AudioActionParams):
    command: Literal[
        "toggle_mute",
        "step",
        "set_level",
        "toggle_device",
        "play_sound",
        "stop_sound",
        "volume_up",
        "volume_down",
    ] = "toggle_mute"


class HttpRequestParams(LaunchActionParams):
    url: str = Field(default="", description="URL запроса")
    method: Literal["GET", "POST", "PUT"] = Field(default="POST", description="HTTP метод")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP заголовки")
    json_body: Optional[Dict[str, Any]] = Field(default=None, description="Тело запроса")
    timeout_sec: float = Field(default=1.5, ge=0.1, le=30.0, description="Таймаут в секундах")
    kind: Literal["auto", "app", "file", "url"] = "url"

    @model_validator(mode="before")
    @classmethod
    def _sync_http(cls, data: Any) -> Any:
        if isinstance(data, dict):
            u = data.get("url") or data.get("target", "")
            data["target"] = u
            data["url"] = u
            data["kind"] = "url"
        return data


class ScreenshotParams(SystemActionParams):
    command: Literal[
        "dimmer",
        "screenshot",
        "lock_pc",
        "sleep_display",
        "close_window",
        "toggle_dimmer",
        "lock_workstation",
        "toggle_mic_mute",
        "toggle_master_mute",
        "toggle_playback_device",
    ] = "screenshot"
    target: Literal["primary_screen", "active_window"] = Field(default="primary_screen", description="Цель")

    @model_validator(mode="before")
    @classmethod
    def _sync_shot(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["command"] = "screenshot"
            t = data.get("target") or data.get("screenshot_target", "primary")
            data["target"] = "primary_screen" if t in ("primary", "primary_screen") else "active_window"
            data["screenshot_target"] = "primary" if t in ("primary", "primary_screen") else "active_window"
        return data


class SoundboardParams(AudioActionParams):
    target: Literal["master", "focus_app", "mic", "device", "soundboard"] = "soundboard"
    command: Literal["toggle_mute", "step", "set_level", "toggle_device", "play_sound", "stop_sound"] = "play_sound"
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Громкость")
    stop_others: bool = Field(default=False, description="Остановить другие")


# -------------------------------------------------------------
# Нормализатор действий DeckActionNormalizer (Zero-Downtime)
# -------------------------------------------------------------
class DeckActionNormalizer:
    """
    Нормализатор устаревших конфигураций действий DuckDeck (Zero-Downtime Migration).
    Прозрачно преобразует 26 устаревших типов действий и их специфические параметры
    в 8 ортогональных базовых примитивов Pydantic v2.
    """

    @classmethod
    def normalize_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Нормализует конфигурационный словарь в канонический формат примитива."""
        if not isinstance(data, dict):
            return data

        raw_type = data.get("action_type")
        raw_params = data.get("params")
        params = dict(raw_params) if isinstance(raw_params, dict) else {}
        for k, v in data.items():
            if k not in ("action_type", "params") and k not in params:
                params[k] = v

        # 1. hotkey / hotkey_switch
        if raw_type in ("hotkey", "shortcut"):
            return {
                "action_type": "hotkey",
                "params": {
                    "keys": params.get("keys", []),
                    "mode": params.get("mode", "press"),
                    "toggle_keys": params.get("toggle_keys", []),
                },
            }
        if raw_type in ("hotkey_switch", "switch", "toggle_state"):
            s1 = params.get("state_1", {}) if isinstance(params.get("state_1"), dict) else {}
            s2 = params.get("state_2", {}) if isinstance(params.get("state_2"), dict) else {}
            return {
                "action_type": "hotkey",
                "params": {
                    "keys": s1.get("keys", []),
                    "mode": "toggle",
                    "toggle_keys": s2.get("keys", []),
                    "state_1": s1,
                    "state_2": s2,
                    "current_state": params.get("current_state", 1),
                },
            }

        # 2. launch / website / open_path / open_app / http_request
        if raw_type in ("website", "open_website", "web", "url", "browser"):
            target_url = params.get("url") or params.get("target", "")
            return {
                "action_type": "launch",
                "params": {
                    "target": target_url,
                    "args": params.get("args", []),
                    "working_dir": params.get("working_dir"),
                    "kind": "url",
                    "detached": True,
                },
            }
        if raw_type in ("open_path", "path", "folder", "open_folder"):
            target_path = params.get("path") or params.get("target", "")
            return {
                "action_type": "launch",
                "params": {
                    "target": target_path,
                    "args": params.get("args", []),
                    "working_dir": params.get("working_dir"),
                    "kind": "file",
                    "detached": True,
                },
            }
        if raw_type in ("open_app", "open_application", "program", "launch_app"):
            target_exe = params.get("executable") or params.get("path") or params.get("target", "")
            return {
                "action_type": "launch",
                "params": {
                    "target": target_exe,
                    "args": params.get("args", []),
                    "working_dir": params.get("working_dir"),
                    "kind": "app",
                    "detached": params.get("detached", True),
                },
            }
        if raw_type == "launch":
            target = params.get("target") or params.get("path") or params.get("executable", "")
            kind = params.get("kind", "auto")
            return {
                "action_type": "launch",
                "params": {
                    "target": target,
                    "args": params.get("args", []),
                    "working_dir": params.get("working_dir"),
                    "kind": kind,
                    "detached": params.get("detached", True),
                },
            }
        if raw_type in ("http_request", "api", "rest"):
            url = params.get("url") or params.get("target", "")
            return {
                "action_type": "launch",
                "params": {
                    "target": url,
                    "url": url,
                    "args": params.get("args", []),
                    "working_dir": params.get("working_dir"),
                    "kind": "url",
                    "is_http": True,
                    "method": params.get("method", "POST"),
                    "headers": params.get("headers", {}),
                    "json_body": params.get("json_body"),
                    "timeout_sec": params.get("timeout_sec", 1.5),
                    "detached": True,
                },
            }

        # 3. audio / volume_control / audio_device / play_audio / stop_audio
        if raw_type in ("audio_device", "toggle_device"):
            return {
                "action_type": "audio",
                "params": {
                    "target": "device",
                    "command": "toggle_device",
                    "step_percent": 5,
                    "devices": params.get("devices", ["Наушники", "Динамики"]),
                    "file_path": "",
                    "mode": params.get("mode", "toggle"),
                    "target_device_id": params.get("target_device_id"),
                },
            }
        if raw_type in ("volume_control", "volume", "auto_software_vol", "master_volume_control", "mic_mute_control"):
            tgt = params.get("target", "master")
            if tgt in ("microphone", "mic"):
                mapped_target = "mic"
            elif tgt in ("focus_app", "master", "device"):
                mapped_target = tgt
            else:
                mapped_target = "master"

            cmd = params.get("command", "toggle_mute")
            step = params.get("step_percent", 5)
            if cmd == "volume_up":
                mapped_cmd = "step"
                step_val = abs(step)
            elif cmd == "volume_down":
                mapped_cmd = "step"
                step_val = -abs(step)
            elif cmd in ("step", "toggle_mute", "set_level", "toggle_device"):
                mapped_cmd = cmd
                step_val = step
            else:
                mapped_cmd = "toggle_mute"
                step_val = 5

            return {
                "action_type": "audio",
                "params": {
                    "target": mapped_target,
                    "command": mapped_cmd,
                    "step_percent": step_val,
                    "devices": params.get("devices", ["Наушники", "Динамики"]),
                    "file_path": "",
                    "mode": "toggle",
                },
            }
        if raw_type in ("play_audio", "soundboard"):
            return {
                "action_type": "audio",
                "params": {
                    "target": "soundboard",
                    "command": "play_sound",
                    "step_percent": 5,
                    "devices": [],
                    "file_path": params.get("file_path", ""),
                    "volume": float(params.get("volume", 1.0)),
                    "stop_others": bool(params.get("stop_others", False)),
                    "mode": "toggle",
                },
            }
        if raw_type in ("stop_audio", "soundboard_stop"):
            return {
                "action_type": "audio",
                "params": {
                    "target": "soundboard",
                    "command": "stop_sound",
                    "step_percent": 5,
                    "devices": [],
                    "file_path": "",
                    "volume": 1.0,
                    "stop_others": False,
                    "mode": "toggle",
                },
            }
        if raw_type == "audio":
            return {
                "action_type": "audio",
                "params": {
                    "target": params.get("target", "master"),
                    "command": params.get("command", "toggle_mute"),
                    "step_percent": params.get("step_percent", 5),
                    "devices": params.get("devices", ["Наушники", "Динамики"]),
                    "file_path": params.get("file_path", ""),
                    "volume": float(params.get("volume", 1.0)),
                    "stop_others": bool(params.get("stop_others", False)),
                    "mode": params.get("mode", "toggle"),
                    "target_device_id": params.get("target_device_id"),
                },
            }

        # 4. media / multimedia
        if raw_type in ("multimedia", "media", "media_control"):
            cmd = params.get("command", "play_pause")
            if cmd == "mute":
                return {
                    "action_type": "audio",
                    "params": {
                        "target": "master",
                        "command": "toggle_mute",
                        "step_percent": 5,
                        "devices": ["Наушники", "Динамики"],
                        "file_path": "",
                        "mode": "toggle",
                    },
                }
            elif cmd in ("play_pause", "next_track", "prev_track", "stop", "volume_up", "volume_down"):
                return {
                    "action_type": "media",
                    "params": {"command": cmd},
                }
            return {
                "action_type": "media",
                "params": {"command": "play_pause"},
            }

        # 5. text / text_macro
        if raw_type in ("text_macro", "text", "paste_text", "macro_text"):
            return {
                "action_type": "text",
                "params": {
                    "text": params.get("text", ""),
                    "send_enter": bool(params.get("send_enter", False)),
                },
            }

        # 6. system / screenshot / close_window / brightness / sleep_display
        if raw_type in ("screenshot", "screen"):
            tgt = params.get("target", "primary_screen")
            mapped_tgt = "primary" if tgt in ("primary_screen", "primary") else "active_window"
            return {
                "action_type": "system",
                "params": {
                    "command": "screenshot",
                    "screenshot_target": mapped_tgt,
                    "clipboard": params.get("clipboard", True),
                    "save_path": params.get("save_path"),
                },
            }
        if raw_type in ("close_window", "close", "kill_window"):
            return {
                "action_type": "system",
                "params": {
                    "command": "close_window",
                    "screenshot_target": "primary",
                },
            }
        if raw_type in ("brightness",):
            return {
                "action_type": "system",
                "params": {
                    "command": "dimmer",
                    "screenshot_target": "primary",
                },
            }
        if raw_type in ("sleep_display",):
            return {
                "action_type": "system",
                "params": {
                    "command": "sleep_display",
                    "screenshot_target": "primary",
                },
            }
        if raw_type in ("system", "system_command"):
            cmd = params.get("command", "dimmer")
            if cmd in ("toggle_dimmer", "dimmer"):
                return {
                    "action_type": "system",
                    "params": {"command": "dimmer", "screenshot_target": "primary"},
                }
            if cmd in ("lock_workstation", "lock_pc"):
                return {
                    "action_type": "system",
                    "params": {"command": "lock_pc", "screenshot_target": "primary"},
                }
            if cmd == "sleep_display":
                return {
                    "action_type": "system",
                    "params": {"command": "sleep_display", "screenshot_target": "primary"},
                }
            if cmd == "close_window":
                return {
                    "action_type": "system",
                    "params": {"command": "close_window", "screenshot_target": "primary"},
                }
            if cmd == "screenshot":
                mapped_tgt = "primary" if params.get("screenshot_target") in ("primary", "primary_screen") else "active_window"
                return {
                    "action_type": "system",
                    "params": {
                        "command": "screenshot",
                        "screenshot_target": mapped_tgt,
                        "clipboard": params.get("clipboard", True),
                        "save_path": params.get("save_path"),
                    },
                }
            if cmd in ("toggle_mic_mute", "toggle_master_mute", "toggle_playback_device"):
                return {
                    "action_type": "system",
                    "params": {"command": cmd, "screenshot_target": "primary"},
                }
            return {
                "action_type": "system",
                "params": {
                    "command": cmd if cmd in ("dimmer", "screenshot", "lock_pc", "sleep_display", "close_window") else "dimmer",
                    "screenshot_target": params.get("screenshot_target", "primary"),
                },
            }

        # 7. deck_nav / navigation / pages / folders
        if raw_type in ("navigation", "page", "switch_page"):
            page = params.get("target_page_id") or params.get("page_id")
            return {
                "action_type": "deck_nav",
                "params": {
                    "target": "goto_page",
                    "page_id": page,
                },
            }
        if raw_type in ("prev_page",):
            return {
                "action_type": "deck_nav",
                "params": {"target": "prev_page", "page_id": None},
            }
        if raw_type in ("next_page",):
            return {
                "action_type": "deck_nav",
                "params": {"target": "next_page", "page_id": None},
            }
        if raw_type in ("goto_page", "switch_profile", "page_indicator"):
            page = params.get("page_id") or params.get("target_page_id")
            return {
                "action_type": "deck_nav",
                "params": {"target": "goto_page", "page_id": page},
            }
        if raw_type in ("create_folder",):
            page = params.get("page_id") or params.get("target_page_id")
            return {
                "action_type": "deck_nav",
                "params": {"target": "folder_open", "page_id": page},
            }
        if raw_type == "deck_nav":
            return {
                "action_type": "deck_nav",
                "params": {
                    "target": params.get("target", "next_page"),
                    "page_id": params.get("page_id"),
                },
            }

        # 8. macro / multi_action
        if raw_type in ("multi_action", "multi_action_switch", "macro"):
            steps = params.get("steps") or params.get("actions", [])
            return {
                "action_type": "macro",
                "params": {
                    "steps": steps,
                    "delay_ms": params.get("delay_ms", 50),
                },
            }

        return data


# -------------------------------------------------------------
# Базовая конфигурация действия кнопки DeckActionConfig
# -------------------------------------------------------------
class DeckActionConfig(BaseModel):
    """Типизированная конфигурация действия кнопки с прозрачной нормализацией."""
    action_type: ActionType
    params: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_action(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return DeckActionNormalizer.normalize_dict(data)
        return data

    def get_typed_params(self) -> Union[
        HotkeyActionParams,
        LaunchActionParams,
        AudioActionParams,
        MediaActionParams,
        TextActionParams,
        SystemActionParams,
        DeckNavActionParams,
        MacroActionParams,
    ]:
        """Фабрика типизированных параметров базовых примитивов."""
        if self.action_type == "hotkey":
            if self.params.get("mode") == "toggle":
                return HotkeySwitchParams(**self.params)
            return HotkeyActionParams(**self.params)
        elif self.action_type == "launch":
            kind = self.params.get("kind", "auto")
            if "timeout_sec" in self.params or "method" in self.params or self.params.get("is_http"):
                return HttpRequestParams(**self.params)
            if kind == "url":
                return WebsiteParams(**self.params)
            if kind == "file":
                return OpenPathParams(**self.params)
            if kind == "app":
                return OpenAppParams(**self.params)
            return LaunchActionParams(**self.params)
        elif self.action_type == "audio":
            if self.params.get("target") == "soundboard":
                return SoundboardParams(**self.params)
            if self.params.get("command") == "toggle_device" or self.params.get("target") == "device":
                return AudioDeviceParams(**self.params)
            return VolumeControlParams(**self.params)
        elif self.action_type == "media":
            return MediaActionParams(**self.params)
        elif self.action_type == "text":
            return TextActionParams(**self.params)
        elif self.action_type == "system":
            cmd = self.params.get("command", "dimmer")
            if cmd == "screenshot":
                return ScreenshotParams(**self.params)
            if cmd == "close_window":
                return CloseWindowParams(**self.params)
            return SystemActionParams(**self.params)
        elif self.action_type == "deck_nav":
            return NavigationParams(**self.params)
        elif self.action_type == "macro":
            return MacroActionParams(**self.params)
        return self.params


# Пересборка рекурсивных моделей
MacroActionParams.model_rebuild()
ActionPresetDefinition.model_rebuild()


# -------------------------------------------------------------
# Конфигурация кнопок, страниц и корня
# -------------------------------------------------------------
class DeckButtonConfig(BaseModel):
    """Конфигурация отдельного сенсорного тайла макро-панели."""
    id: str = Field(description="Уникальный идентификатор кнопки")
    slot_index: int = Field(default=0, ge=0, le=9, description="Позиция кнопки в сетке 2x5 (0..9)")
    name: Optional[str] = Field(default=None, description="Имя кнопки для логирования и поиска")
    title: str = Field(description="Заголовок тайла")
    category: ActionCategory = Field(
        default="system",
        description="Категория действия: system, shortcut, program, api",
    )
    icon: str = Field(default="⚡", description="Символ Unicode, SVG имя или fallback-глиф")
    icon_path: Optional[str] = Field(default=None, description="Относительный или абсолютный путь к файлу иконки")
    icon_size: int = Field(default=48, ge=16, le=128, description="Целевой размер отрисовки иконки в пикселях")
    font_size: int = Field(default=11, ge=8, le=24, description="Размер шрифта заголовка в px")
    font_color: str = Field(default="#d4d4d8", description="Цвет шрифта заголовка (HEX)")
    text_alignment: Literal["bottom", "center", "top"] = Field(
        default="bottom", description="Положение текста относительно иконки"
    )
    hide_title: bool = Field(default=False, description="Скрыть текст заголовка (режим чистой иконки)")
    color_accent: str = Field(default="#38bdf8", description="Неоновый цвет акцента границы/иконки")
    background_color: str = Field(default="#161b26", description="Цвет фона кнопки")
    action: DeckActionConfig = Field(description="Основное действие по нажатию")
    toggle_action: Optional[DeckActionConfig] = Field(default=None, description="Второе действие для переключателей")
    status_source: Optional[str] = Field(
        default=None,
        description="Имя источника статуса в EventBus ('mic_mute', 'audio_device', 'dimmer')",
    )
    sound_override: Optional[str] = Field(
        default=None,
        description="Опциональный путь к WAV-файлу звука клика для данной кнопки",
    )


class SoundSettings(BaseModel):
    """Настройки звукового сопровождения интерфейса DuckDeck."""
    enabled: bool = Field(default=True, description="Флаг активации звуковых эффектов")
    volume: float = Field(default=0.8, ge=0.0, le=1.0, description="Громкость воспроизведения звуков от 0.0 до 1.0")
    default_tap_sound: str = Field(
        default="resources/deck/sounds/button_click.wav",
        description="Звук клика плитки по умолчанию",
    )
    page_switch_sound: str = Field(
        default="resources/deck/sounds/button_sw_page.wav",
        description="Звук смены страницы профиля",
    )
    error_sound: str = Field(
        default="resources/deck/sounds/button_offline.wav",
        description="Звук ошибки или заблокированного действия",
    )
    success_sound: Optional[str] = Field(
        default="resources/deck/sounds/button_online.wav",
        description="Звук успешного выполнения действия",
    )


class DeckPageConfig(BaseModel):
    """Страница кнопок (профиль или подпапка)."""
    id: str = Field(description="Идентификатор страницы")
    name: str = Field(description="Понятное название страницы")
    grid_rows: int = Field(default=2, ge=1, le=8, description="Число строк сетки")
    grid_cols: int = Field(default=5, ge=1, le=8, description="Число колонок сетки")
    buttons: List[DeckButtonConfig] = Field(default_factory=list, description="Список кнопок на странице")


class DeckRootConfig(BaseModel):
    """Корневая конфигурация макро-панели DuckDeck."""
    active_profile: str = Field(default="default", description="ID активной страницы")
    simulation_mode: bool = Field(
        default=False,
        description="Режим симуляции (Stubs Mode) без исполнения боевых действий",
    )
    sound_settings: SoundSettings = Field(
        default_factory=SoundSettings,
        description="Настройки звукового сопровождения интерфейса",
    )
    pages: List[DeckPageConfig] = Field(default_factory=list, description="Список страниц/профилей")


class DeckConfigLoader:
    """Безопасный загрузчик конфигурации с автоматическим fallback."""

    @staticmethod
    def get_default_config() -> DeckRootConfig:
        """Возвращает чистую конфигурацию по умолчанию с одной пустой страницей."""
        return DeckRootConfig(
            active_profile="default",
            simulation_mode=False,
            sound_settings=SoundSettings(),
            pages=[
                DeckPageConfig(
                    id="default",
                    name="Основной",
                    grid_rows=2,
                    grid_cols=5,
                    buttons=[],
                )
            ],
        )

    @classmethod
    def load_from_file(cls, path: str) -> DeckRootConfig:
        """
        Загружает конфигурацию из JSON-файла с валидацией.
        В случае отсутствия файла или ошибки парсинга возвращает дефолтную конфигурацию.
        """
        if not os.path.isfile(path):
            logger.info(f"Файл конфигурации DuckDeck '{path}' не найден. Создается дефолтная конфигурация.")
            default_cfg = cls.get_default_config()
            try:
                cls.save_to_file(default_cfg, path)
            except Exception as e:
                logger.warning(f"Не удалось сохранить дефолтную конфигурацию в '{path}': {e}")
            return default_cfg

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return DeckRootConfig.model_validate(data)
        except (json.JSONDecodeError, ValidationError, Exception) as e:
            logger.error(f"Ошибка загрузки конфигурации DuckDeck из '{path}': {e}. Используется дефолтная.")
            return cls.get_default_config()

    @staticmethod
    def save_to_file(config: DeckRootConfig, path: str) -> bool:
        """Сохраняет конфигурацию в JSON-файл."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(config.model_dump_json(indent=2))
            return True
        except Exception as e:
            logger.error(f"Не удалось сохранить конфигурацию DuckDeck в '{path}': {e}")
            return False


__all__ = [
    "ActionType",
    "ActionCategory",
    "HotkeyActionParams",
    "LaunchActionParams",
    "AudioActionParams",
    "MediaActionParams",
    "TextActionParams",
    "SystemActionParams",
    "DeckNavActionParams",
    "MacroActionParams",
    "ActionPresetDefinition",
    "DeckActionNormalizer",
    "HotkeyParams",
    "HotkeySwitchState",
    "HotkeySwitchParams",
    "WebsiteParams",
    "OpenPathParams",
    "OpenAppParams",
    "CloseWindowParams",
    "TextMacroParams",
    "MultimediaParams",
    "VolumeControlParams",
    "AudioDeviceParams",
    "LaunchParams",
    "HttpRequestParams",
    "ScreenshotParams",
    "SystemParams",
    "NavigationParams",
    "SoundboardParams",
    "AudioDeviceInfo",
    "DeckActionConfig",
    "DeckButtonConfig",
    "SoundSettings",
    "DeckPageConfig",
    "DeckRootConfig",
    "DeckConfigLoader",
]
