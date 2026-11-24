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
    "stream_deck",    # Управление стримдеком и экраном
    "multi_action",   # Мульти-действия и макро-цепочки
]


# -------------------------------------------------------------
# Типизированные Pydantic v2 модели параметров для 8 примитивов
# -------------------------------------------------------------
class HotkeyActionParams(BaseModel):
    """Параметры симуляции горячих клавиш и двухпозиционных тумблеров."""
    mode: Literal["press", "toggle"] = Field(default="press", description="Режим: press (одиночный) или toggle (тумблер)")
    keys: List[str] = Field(default_factory=list, description="Список клавиш (например ['ctrl', 'shift', 'd'])")
    toggle_keys: List[str] = Field(default_factory=list, description="Вторая комбинация клавиш для тумблера")


class LaunchActionParams(BaseModel):
    """Параметры запуска процессов, файлов, папок и веб-ссылок."""
    target: str = Field(default="", description="Путь к .exe, файлу, папке или URL")
    args: List[str] = Field(default_factory=list, description="Аргументы командной строки")
    working_dir: Optional[str] = Field(default=None, description="Рабочая директория")
    kind: Literal["app", "file", "url"] = Field(default="app", description="Тип запускаемой цели")
    detached: bool = Field(default=True, description="Запуск в фоновом изолированном процессе")

    @property
    def path(self) -> str:
        return self.target

    @path.setter
    def path(self, val: str) -> None:
        self.target = val


class AudioActionParams(BaseModel):
    """Параметры аудиоподсистемы (микшер, устройства, микрофон)."""
    target: Literal["master", "mic", "focus_app", "device"] = Field(
        default="master", description="Цель управления звуком"
    )
    command: Literal["toggle_mute", "volume_up", "volume_down", "toggle_device", "set_device"] = Field(
        default="toggle_mute", description="Команда аудиоподсистемы"
    )
    step_percent: int = Field(default=5, description="Шаг изменения громкости в процентах")
    devices: Optional[List[str]] = Field(
        default=None,
        description="Ключевые слова или имена устройств для переключения",
    )
    mode: Literal["toggle", "set"] = Field(default="toggle", description="Режим переключения устройств")
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
        "toggle_dimmer",
        "screenshot",
        "lock_workstation",
        "sleep_display",
        "close_window",
    ] = Field(default="toggle_dimmer", description="Системная команда")
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
    is_wip: bool = Field(default=False, description="Флаг незавершенного функционала (В разработке)")
    is_enabled: bool = Field(default=True, description="Флаг доступности пресета для выбора")


# -------------------------------------------------------------
# Псевдонимы для обратной совместимости имён (Type Aliases)
# -------------------------------------------------------------
HotkeyParams = HotkeyActionParams
LaunchParams = LaunchActionParams
AudioDeviceParams = AudioActionParams
MultimediaParams = MediaActionParams
TextMacroParams = TextActionParams
SystemParams = SystemActionParams
NavigationParams = DeckNavActionParams


# -------------------------------------------------------------
# Нормализатор действий DeckActionNormalizer (Zero-Downtime)
# -------------------------------------------------------------
class DeckActionNormalizer:
    """
    Нормализатор устаревших конфигураций действий DuckDeck (Zero-Downtime Migration).
    Прозрачно преобразует устаревшие типы действий и их специфические параметры
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
                    "keys": params.get("keys") or s1.get("keys", []),
                    "mode": "toggle",
                    "toggle_keys": params.get("toggle_keys") or s2.get("keys", []),
                },
            }

        # 2. launch / website / open_path / open_app / http_request
        if raw_type in ("website", "open_website", "web", "url", "browser", "http_request", "api", "rest"):
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
            target = params.get("target") or params.get("path") or params.get("executable") or params.get("url", "")
            raw_kind = params.get("kind", "app")
            if raw_kind not in ("app", "file", "url"):
                raw_kind = "url" if str(target).startswith(("http://", "https://")) else "app"
            return {
                "action_type": "launch",
                "params": {
                    "target": target,
                    "args": params.get("args", []),
                    "working_dir": params.get("working_dir"),
                    "kind": raw_kind,
                    "detached": params.get("detached", True),
                },
            }

        # 3. audio / volume_control / audio_device
        if raw_type in ("audio_device", "toggle_device"):
            raw_mode = params.get("mode", "toggle")
            mode = "set" if raw_mode == "set" else "toggle"
            cmd = "set_device" if mode == "set" else "toggle_device"
            norm_params: Dict[str, Any] = {
                "target": "device",
                "command": cmd,
                "mode": mode,
            }
            if params.get("devices") is not None:
                norm_params["devices"] = params["devices"]
            if params.get("target_device_id") is not None:
                norm_params["target_device_id"] = params["target_device_id"]
            return {"action_type": "audio", "params": norm_params}

        if raw_type in ("volume_control", "volume", "auto_software_vol", "master_volume_control", "mic_mute_control"):
            tgt = params.get("target", "master")
            if tgt in ("microphone", "mic"):
                mapped_target = "mic"
            elif tgt in ("focus_app", "master", "device"):
                mapped_target = tgt
            else:
                mapped_target = "master"

            cmd = params.get("command", "toggle_mute")
            step = int(params.get("step_percent", 5))
            if cmd == "volume_up" or (cmd == "step" and step >= 0):
                mapped_cmd = "volume_up"
                step_val = abs(step) if step != 0 else 5
            elif cmd == "volume_down" or (cmd == "step" and step < 0):
                mapped_cmd = "volume_down"
                step_val = abs(step)
            elif cmd in ("toggle_mute", "toggle_device", "set_device"):
                mapped_cmd = cmd
                step_val = abs(step) if step != 0 else 5
            else:
                mapped_cmd = "toggle_mute"
                step_val = 5

            return {
                "action_type": "audio",
                "params": {
                    "target": mapped_target,
                    "command": mapped_cmd,
                    "step_percent": step_val,
                },
            }

        if raw_type == "audio":
            tgt = params.get("target", "master")
            if tgt == "microphone":
                tgt = "mic"
            elif tgt not in ("master", "mic", "focus_app", "device"):
                tgt = "master"

            cmd = params.get("command", "toggle_mute")
            step = int(params.get("step_percent", 5))
            if cmd == "step":
                cmd = "volume_up" if step >= 0 else "volume_down"
                step = abs(step) if step != 0 else 5
            elif cmd not in ("toggle_mute", "volume_up", "volume_down", "toggle_device", "set_device"):
                cmd = "set_device" if (tgt == "device" and params.get("mode") == "set") else (
                    "toggle_device" if tgt == "device" else "toggle_mute"
                )

            raw_mode = params.get("mode", "toggle")
            mode = "set" if raw_mode == "set" else "toggle"

            norm_audio: Dict[str, Any] = {
                "target": tgt,
                "command": cmd,
                "step_percent": abs(step) if step != 0 else 5,
                "mode": mode,
            }
            if params.get("devices") is not None:
                norm_audio["devices"] = params["devices"]
            if params.get("target_device_id") is not None:
                norm_audio["target_device_id"] = params["target_device_id"]
            return {"action_type": "audio", "params": norm_audio}

        # 4. media / multimedia
        if raw_type in ("multimedia", "media", "media_control"):
            cmd = params.get("command", "play_pause")
            if cmd == "mute":
                return {
                    "action_type": "audio",
                    "params": {
                        "target": "master",
                        "command": "toggle_mute",
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
                    "command": "toggle_dimmer",
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
            cmd = params.get("command", "toggle_dimmer")
            if cmd in ("toggle_dimmer", "dimmer"):
                return {
                    "action_type": "system",
                    "params": {"command": "toggle_dimmer", "screenshot_target": "primary"},
                }
            if cmd in ("lock_workstation", "lock_pc"):
                return {
                    "action_type": "system",
                    "params": {"command": "lock_workstation", "screenshot_target": "primary"},
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
                raw_shot = params.get("screenshot_target") or params.get("target", "primary")
                mapped_tgt = "primary" if raw_shot in ("primary", "primary_screen") else "active_window"
                return {
                    "action_type": "system",
                    "params": {
                        "command": "screenshot",
                        "screenshot_target": mapped_tgt,
                        "clipboard": params.get("clipboard", True),
                        "save_path": params.get("save_path"),
                    },
                }
            if cmd == "toggle_mic_mute":
                return {
                    "action_type": "audio",
                    "params": {"target": "mic", "command": "toggle_mute"},
                }
            if cmd == "toggle_master_mute":
                return {
                    "action_type": "audio",
                    "params": {"target": "master", "command": "toggle_mute"},
                }
            if cmd == "toggle_playback_device":
                return {
                    "action_type": "audio",
                    "params": {"target": "device", "command": "toggle_device", "mode": "toggle"},
                }
            return {
                "action_type": "system",
                "params": {
                    "command": "toggle_dimmer",
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
        """Фабрика типизированных параметров 8 базовых примитивов."""
        if self.action_type == "hotkey":
            return HotkeyActionParams(**self.params)
        elif self.action_type == "launch":
            return LaunchActionParams(**self.params)
        elif self.action_type == "audio":
            return AudioActionParams(**self.params)
        elif self.action_type == "media":
            return MediaActionParams(**self.params)
        elif self.action_type == "text":
            return TextActionParams(**self.params)
        elif self.action_type == "system":
            return SystemActionParams(**self.params)
        elif self.action_type == "deck_nav":
            return DeckNavActionParams(**self.params)
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
    "LaunchParams",
    "AudioDeviceParams",
    "MultimediaParams",
    "TextMacroParams",
    "SystemParams",
    "NavigationParams",
    "AudioDeviceInfo",
    "DeckActionConfig",
    "DeckButtonConfig",
    "SoundSettings",
    "DeckPageConfig",
    "DeckRootConfig",
    "DeckConfigLoader",
]
