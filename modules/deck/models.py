"""
Декларативные Pydantic v2 модели и схемы конфигурации макро-панели DuckDeck.
"""
import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ValidationError

from modules.audio.models import AudioDeviceInfo

logger = logging.getLogger("duckdock.deck.models")

ActionType = Literal[
    "hotkey",         # Симуляция клавиш (SendInput)
    "hotkey_switch",  # Двухпозиционный переключатель хоткеев
    "audio_device",   # Переключение аудиоустройств вывода (Наушники/Динамики)
    "launch",         # Запуск программы / скрипта
    "website",        # Открытие URL веб-сайта
    "open_path",      # Открытие папки или файла
    "open_app",       # Запуск приложения с аргументами
    "close_window",   # Закрытие активного окна / процесса
    "text_macro",     # Текстовый макрос
    "multimedia",     # Управление мультимедиа Windows
    "volume_control", # Управление громкостью
    "http_request",   # REST API запрос к сторонним программам
    "screenshot",     # Скриншот основного монитора / окна
    "system",         # Системное действие (mute mic, lock, dimmer)
    "navigation",     # Переход на страницу/папку
    "play_audio",     # Воспроизведение звука саундборда
    "stop_audio",     # Остановка всех звуков саундборда
    "create_folder",  # Создать папку (вложенная подсетка)
    "switch_profile", # Сменить профиль
    "prev_page",      # Предыдущая страница
    "next_page",      # Следующая страница
    "goto_page",      # Перейти на страницу
    "page_indicator", # Индикатор страниц
    "brightness",     # Регулировка яркости
    "sleep_display",  # Спящий режим дисплея
    "multi_action",   # Цепочка макро-действий
    "multi_action_switch", # Переключатель цепочек макро-действий
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


class HotkeyParams(BaseModel):
    """Параметры симуляции горячих клавиш."""
    keys: List[str] = Field(default_factory=list, description="Список клавиш (например ['ctrl', 'shift', 'd'])")


class HotkeySwitchState(BaseModel):
    """Состояние переключателя хоткеев."""
    title: str = Field(default="", description="Название состояния")
    keys: List[str] = Field(default_factory=list, description="Список клавиш")
    icon: Optional[str] = Field(default=None, description="Иконка состояния")


class HotkeySwitchParams(BaseModel):
    """Параметры двухпозиционного переключателя хоткеев."""
    state_1: HotkeySwitchState = Field(default_factory=HotkeySwitchState, description="Состояние 1")
    state_2: HotkeySwitchState = Field(default_factory=HotkeySwitchState, description="Состояние 2")
    current_state: int = Field(default=1, ge=1, le=2, description="Текущее активное состояние (1 или 2)")


class WebsiteParams(BaseModel):
    """Параметры открытия веб-страницы."""
    url: str = Field(default="", description="URL адрес сайта")


class OpenPathParams(BaseModel):
    """Параметры открытия пути/файла/папки."""
    path: str = Field(default="", description="Путь к файлу или папке")


class OpenAppParams(BaseModel):
    """Параметры запуска приложения."""
    executable: str = Field(default="", description="Путь к исполняемому файлу")
    args: List[str] = Field(default_factory=list, description="Аргументы командной строки")
    working_dir: Optional[str] = Field(default=None, description="Рабочая директория")


class CloseWindowParams(BaseModel):
    """Параметры закрытия окна."""
    target: Literal["active_window", "by_process"] = Field(
        default="active_window", description="Цель закрытия"
    )
    process_name: Optional[str] = Field(default=None, description="Имя процесса (для by_process)")


class TextMacroParams(BaseModel):
    """Параметры текстового макроса."""
    text: str = Field(default="", description="Вставляемый текст")
    send_enter: bool = Field(default=False, description="Отправить Enter после вставки")


class MultimediaParams(BaseModel):
    """Параметры мультимедийного управления Windows."""
    command: Literal[
        "play_pause",
        "next_track",
        "prev_track",
        "stop",
        "mute",
        "volume_up",
        "volume_down",
    ] = Field(default="play_pause", description="Мультимедийная команда")


class VolumeControlParams(BaseModel):
    """Параметры управления громкостью."""
    target: Literal["focus_app", "master", "microphone"] = Field(
        default="focus_app", description="Цель регулировки"
    )
    command: Literal["toggle_mute", "volume_up", "volume_down", "set_level"] = Field(
        default="toggle_mute", description="Команда регулировки"
    )
    step_percent: int = Field(default=5, ge=1, le=50, description="Шаг изменения в процентах")


class AudioDeviceParams(BaseModel):
    """Параметры переключения аудиоустройств."""
    mode: Literal["toggle", "set", "cycle"] = Field(default="toggle", description="Режим переключения")
    devices: List[str] = Field(
        default_factory=lambda: ["Наушники", "Динамики"],
        description="Ключевые слова или имена устройств для циклического переключения",
    )
    target_device_id: Optional[str] = Field(default=None, description="Точный ID устройства для режима 'set'")


class LaunchParams(BaseModel):
    """Параметры запуска внешнего процесса."""
    path: str = Field(description="Путь к исполняемому файлу, скрипту или URL")
    args: List[str] = Field(default_factory=list, description="Аргументы командной строки")
    working_dir: Optional[str] = Field(default=None, description="Рабочая директория")
    detached: bool = Field(default=True, description="Запуск в фоновом изолированном процессе")


class HttpRequestParams(BaseModel):
    """Параметры HTTP REST запроса."""
    url: str = Field(description="URL запроса")
    method: Literal["GET", "POST", "PUT"] = Field(default="POST", description="HTTP метод")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP заголовки")
    json_body: Optional[Dict[str, Any]] = Field(default=None, description="Тело запроса в формате JSON")
    timeout_sec: float = Field(default=1.5, ge=0.1, le=30.0, description="Таймаут выполнения запроса в секундах")


class ScreenshotParams(BaseModel):
    """Параметры захвата экрана."""
    target: Literal["primary_screen", "active_window"] = Field(default="primary_screen", description="Цель скриншота")
    clipboard: bool = Field(default=True, description="Поместить результат в буфер обмена")
    save_path: Optional[str] = Field(default=None, description="Опциональный путь для сохранения файла на диске")


class SystemParams(BaseModel):
    """Параметры системного действия."""
    command: Literal[
        "toggle_mic_mute",
        "toggle_master_mute",
        "lock_workstation",
        "toggle_dimmer",
        "toggle_playback_device",
    ] = Field(description="Системная команда")


class NavigationParams(BaseModel):
    """Параметры навигации между страницами DuckDeck."""
    target_page_id: str = Field(default="default", description="ID целевой страницы профиля")


class SoundboardParams(BaseModel):
    """Параметры действия воспроизведения аудио саундборда."""
    file_path: str = Field(default="", description="Относительный или абсолютный путь к аудиофайлу")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Громкость воспроизведения от 0.0 до 1.0")
    stop_others: bool = Field(default=False, description="Остановить другие звуки саундборда перед запуском")


class DeckActionConfig(BaseModel):
    """Типизированная конфигурация действия кнопки."""
    action_type: ActionType
    params: Dict[str, Any] = Field(default_factory=dict)

    def get_typed_params(self) -> Union[
        HotkeyParams,
        HotkeySwitchParams,
        WebsiteParams,
        OpenPathParams,
        OpenAppParams,
        CloseWindowParams,
        TextMacroParams,
        MultimediaParams,
        VolumeControlParams,
        AudioDeviceParams,
        LaunchParams,
        HttpRequestParams,
        ScreenshotParams,
        SystemParams,
        NavigationParams,
        SoundboardParams,
        Dict[str, Any],
    ]:
        """Фабрика типизированных параметров действия."""
        mapping = {
            "hotkey": HotkeyParams,
            "hotkey_switch": HotkeySwitchParams,
            "website": WebsiteParams,
            "open_path": OpenPathParams,
            "open_app": OpenAppParams,
            "close_window": CloseWindowParams,
            "text_macro": TextMacroParams,
            "multimedia": MultimediaParams,
            "volume_control": VolumeControlParams,
            "audio_device": AudioDeviceParams,
            "launch": LaunchParams,
            "http_request": HttpRequestParams,
            "screenshot": ScreenshotParams,
            "system": SystemParams,
            "navigation": NavigationParams,
            "create_folder": NavigationParams,
            "switch_profile": NavigationParams,
            "prev_page": NavigationParams,
            "next_page": NavigationParams,
            "goto_page": NavigationParams,
            "page_indicator": NavigationParams,
            "play_audio": SoundboardParams,
            "stop_audio": SoundboardParams,
        }
        model_cls = mapping.get(self.action_type)
        if model_cls:
            return model_cls(**self.params)
        return self.params


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
        """Возвращает эталонную конфигурацию по умолчанию."""
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
                    buttons=[
                        DeckButtonConfig(
                            id="btn_toggle_audio_device",
                            slot_index=0,
                            name="Аудиовыход",
                            title="Аудиовыход",
                            category="system",
                            icon="🎧",
                            icon_path="resources/deck/icons/system/sound.png",
                            icon_size=48,
                            color_accent="#06b6d4",
                            status_source="audio_device",
                            action=DeckActionConfig(
                                action_type="audio_device",
                                params={"mode": "toggle", "devices": ["Наушники", "Динамики"]},
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_mute_mic",
                            slot_index=1,
                            name="Микрофон",
                            title="Микрофон",
                            category="system",
                            icon="🎙",
                            icon_path="resources/deck/icons/system/mic.png",
                            icon_size=48,
                            color_accent="#ef4444",
                            status_source="mic_mute",
                            action=DeckActionConfig(
                                action_type="system",
                                params={"command": "toggle_mic_mute"},
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_screenshot_primary",
                            slot_index=2,
                            name="Скриншот",
                            title="Скриншот",
                            category="system",
                            icon="📸",
                            icon_path="resources/deck/icons/system/screenshot.png",
                            icon_size=48,
                            color_accent="#38bdf8",
                            action=DeckActionConfig(
                                action_type="screenshot",
                                params={"target": "primary_screen", "clipboard": True},
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_discord_deafen",
                            slot_index=3,
                            name="Discord Deafen",
                            title="Discord Deafen",
                            category="shortcut",
                            icon="🎧",
                            icon_path="resources/deck/icons/apps/discord.png",
                            icon_size=48,
                            color_accent="#818cf8",
                            action=DeckActionConfig(
                                action_type="hotkey",
                                params={"keys": ["ctrl", "shift", "d"]},
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_obs_record",
                            slot_index=4,
                            name="OBS Запись",
                            title="OBS Запись",
                            category="shortcut",
                            icon="⏺",
                            icon_path="resources/deck/icons/apps/obs.png",
                            icon_size=48,
                            color_accent="#dc2626",
                            action=DeckActionConfig(
                                action_type="hotkey",
                                params={"keys": ["ctrl", "f9"]},
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_openrgb_red",
                            slot_index=5,
                            name="RGB Red Alert",
                            title="RGB Red Alert",
                            category="api",
                            icon="💡",
                            icon_path="resources/deck/icons/apps/openrgb.png",
                            icon_size=48,
                            color_accent="#f43f5e",
                            action=DeckActionConfig(
                                action_type="http_request",
                                params={
                                    "url": "http://127.0.0.1:6742/api/profiles/RedAlert/load",
                                    "method": "POST",
                                },
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_launch_terminal",
                            slot_index=6,
                            name="Терминал",
                            title="Терминал",
                            category="program",
                            icon="💻",
                            icon_path="resources/deck/icons/apps/terminal.png",
                            icon_size=48,
                            color_accent="#10b981",
                            action=DeckActionConfig(
                                action_type="launch",
                                params={"path": "wt.exe", "args": []},
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_toggle_dimmer",
                            slot_index=7,
                            name="Ночной режим",
                            title="Ночной режим",
                            category="system",
                            icon="🌙",
                            icon_path="resources/deck/icons/system/dimmer.png",
                            icon_size=48,
                            color_accent="#a855f7",
                            status_source="dimmer",
                            action=DeckActionConfig(
                                action_type="system",
                                params={"command": "toggle_dimmer"},
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_lock_pc",
                            slot_index=8,
                            name="Заблокировать",
                            title="Заблокировать",
                            category="system",
                            icon="🔒",
                            icon_path="resources/deck/icons/system/lock.png",
                            icon_size=48,
                            color_accent="#f59e0b",
                            action=DeckActionConfig(
                                action_type="system",
                                params={"command": "lock_workstation"},
                            ),
                        ),
                        DeckButtonConfig(
                            id="btn_launch_calc",
                            slot_index=9,
                            name="Калькулятор",
                            title="Калькулятор",
                            category="program",
                            icon="🔢",
                            icon_path="resources/deck/icons/apps/calc.png",
                            icon_size=48,
                            color_accent="#06b6d4",
                            action=DeckActionConfig(
                                action_type="launch",
                                params={"path": "calc.exe", "args": []},
                            ),
                        ),
                    ],
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
    "AudioDeviceInfo",
    "DeckActionConfig",
    "DeckButtonConfig",
    "SoundSettings",
    "DeckPageConfig",
    "DeckRootConfig",
    "DeckConfigLoader",
]
