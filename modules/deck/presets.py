"""
Реестр готовых шаблонов действий DuckDeck (ActionPresetsRegistry).
Содержит 8 базовых категорий и 26+ декларативных пресетов действий с двуязычной локализацией.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from modules.deck.editor.dto import ActionCategoryDTO, ActionItemDTO
from modules.deck.models import (
    ActionPresetDefinition,
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

logger = logging.getLogger("duckdock.deck.presets")


class ActionPresetsRegistry:
    """
    Централизованный статический реестр шаблонов (пресетов) действий DuckDeck.
    Группирует готовые рецепты по 8 категориям таксономии и предоставляет
    методы поиска, фильтрации и преобразования в DTO.
    """

    CATEGORIES: List[Dict[str, str]] = [
        {
            "id": "audio_comm",
            "title_key": "deck.editor.categories.audio_comm",
            "icon": "🎛️",
        },
        {
            "id": "media_stream",
            "title_key": "deck.editor.categories.media_stream",
            "icon": "🎮",
        },
        {
            "id": "launchers",
            "title_key": "deck.editor.categories.launchers",
            "icon": "🚀",
        },
        {
            "id": "system_control",
            "title_key": "deck.editor.categories.system_control",
            "icon": "⚙️",
        },
        {
            "id": "input_macros",
            "title_key": "deck.editor.categories.input_macros",
            "icon": "⌨️",
        },
        {
            "id": "navigation",
            "title_key": "deck.editor.categories.navigation",
            "icon": "🧭",
        },
        {
            "id": "multi_action",
            "title_key": "deck.editor.categories.multi_action",
            "icon": "🔀",
        },
    ]

    _PRESETS: List[ActionPresetDefinition] = [
        # =========================================================
        # 1. 🎛️ audio_comm (Аудио и Связь)
        # =========================================================
        ActionPresetDefinition(
            id="output_device_toggle",
            category="audio_comm",
            title_key="deck.editor.presets.output_device_toggle.title",
            desc_key="deck.editor.presets.output_device_toggle.desc",
            icon="🎧",
            color_accent="#06b6d4",
            status_source="audio_device",
            base_action=DeckActionConfig(
                action_type="audio",
                params=AudioActionParams(
                    target="device",
                    command="toggle_device",
                    mode="toggle",
                    devices=["Наушники", "Динамики"],
                ).model_dump(exclude_none=True),
            ),
            keywords=["audio", "headphones", "speakers", "output", "device", "toggle", "звук", "наушники", "динамики", "вывод", "переключить"],
        ),
        ActionPresetDefinition(
            id="mic_mute_toggle",
            category="audio_comm",
            title_key="deck.editor.presets.mic_mute_toggle.title",
            desc_key="deck.editor.presets.mic_mute_toggle.desc",
            icon="🎙️",
            color_accent="#ef4444",
            status_source="mic_mute",
            base_action=DeckActionConfig(
                action_type="audio",
                params=AudioActionParams(
                    target="mic",
                    command="toggle_mute",
                ).model_dump(exclude_none=True),
            ),
            keywords=["mic", "microphone", "mute", "unmute", "voice", "микрофон", "мьют", "голос", "заглушить"],
        ),
        ActionPresetDefinition(
            id="master_mute_toggle",
            category="audio_comm",
            title_key="deck.editor.presets.master_mute_toggle.title",
            desc_key="deck.editor.presets.master_mute_toggle.desc",
            icon="🔇",
            color_accent="#ef4444",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="audio",
                params=AudioActionParams(
                    target="master",
                    command="toggle_mute",
                ).model_dump(exclude_none=True),
            ),
            keywords=["master", "mute", "sound", "volume", "silent", "мастер", "звук", "тишина", "заглушить"],
        ),
        ActionPresetDefinition(
            id="focus_app_vol_up",
            category="audio_comm",
            title_key="deck.editor.presets.focus_app_vol_up.title",
            desc_key="deck.editor.presets.focus_app_vol_up.desc",
            icon="🔊+",
            color_accent="#10b981",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="audio",
                params=AudioActionParams(
                    target="focus_app",
                    command="volume_up",
                    step_percent=5,
                ).model_dump(exclude_none=True),
            ),
            keywords=["volume", "up", "focus", "app", "louder", "громкость", "громче", "плюс", "фокус", "приложение"],
        ),
        ActionPresetDefinition(
            id="focus_app_vol_down",
            category="audio_comm",
            title_key="deck.editor.presets.focus_app_vol_down.title",
            desc_key="deck.editor.presets.focus_app_vol_down.desc",
            icon="🔉-",
            color_accent="#10b981",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="audio",
                params=AudioActionParams(
                    target="focus_app",
                    command="volume_down",
                    step_percent=5,
                ).model_dump(exclude_none=True),
            ),
            keywords=["volume", "down", "focus", "app", "quieter", "громкость", "тише", "минус", "фокус", "приложение"],
        ),
        ActionPresetDefinition(
            id="discord_mute",
            category="audio_comm",
            title_key="deck.editor.presets.discord_mute.title",
            desc_key="deck.editor.presets.discord_mute.desc",
            icon="🎤",
            color_accent="#818cf8",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="hotkey",
                params=HotkeyActionParams(
                    keys=["ctrl", "shift", "m"],
                    mode="press",
                ).model_dump(exclude_none=True),
            ),
            keywords=["discord", "mute", "mic", "дискорд", "мьют", "микрофон"],
        ),
        ActionPresetDefinition(
            id="discord_deafen",
            category="audio_comm",
            title_key="deck.editor.presets.discord_deafen.title",
            desc_key="deck.editor.presets.discord_deafen.desc",
            icon="🎧",
            color_accent="#818cf8",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="hotkey",
                params=HotkeyActionParams(
                    keys=["ctrl", "shift", "d"],
                    mode="press",
                ).model_dump(exclude_none=True),
            ),
            keywords=["discord", "deafen", "sound", "дискорд", "заглушить", "наушники"],
        ),

        # =========================================================
        # 2. 🎮 media_stream (Медиа и Стриминг)
        # =========================================================
        ActionPresetDefinition(
            id="media_play_pause",
            category="media_stream",
            title_key="deck.editor.presets.media_play_pause.title",
            desc_key="deck.editor.presets.media_play_pause.desc",
            icon="⏯️",
            color_accent="#f59e0b",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="media",
                params=MediaActionParams(command="play_pause").model_dump(exclude_none=True),
            ),
            keywords=["media", "play", "pause", "music", "track", "медиа", "плей", "пауза", "музыка", "трек"],
        ),
        ActionPresetDefinition(
            id="media_next_track",
            category="media_stream",
            title_key="deck.editor.presets.media_next_track.title",
            desc_key="deck.editor.presets.media_next_track.desc",
            icon="⏭️",
            color_accent="#f59e0b",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="media",
                params=MediaActionParams(command="next_track").model_dump(exclude_none=True),
            ),
            keywords=["media", "next", "track", "forward", "медиа", "следующий", "трек", "вперед"],
        ),
        ActionPresetDefinition(
            id="media_prev_track",
            category="media_stream",
            title_key="deck.editor.presets.media_prev_track.title",
            desc_key="deck.editor.presets.media_prev_track.desc",
            icon="⏮️",
            color_accent="#f59e0b",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="media",
                params=MediaActionParams(command="prev_track").model_dump(exclude_none=True),
            ),
            keywords=["media", "prev", "previous", "track", "back", "медиа", "предыдущий", "трек", "назад"],
        ),
        ActionPresetDefinition(
            id="obs_record_toggle",
            category="media_stream",
            title_key="deck.editor.presets.obs_record_toggle.title",
            desc_key="deck.editor.presets.obs_record_toggle.desc",
            icon="⏺️",
            color_accent="#dc2626",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="hotkey",
                params=HotkeyActionParams(keys=["ctrl", "f9"]).model_dump(exclude_none=True),
            ),
            keywords=["obs", "record", "stream", "video", "обзор", "запись", "стрим", "видео"],
        ),
        ActionPresetDefinition(
            id="obs_stream_toggle",
            category="media_stream",
            title_key="deck.editor.presets.obs_stream_toggle.title",
            desc_key="deck.editor.presets.obs_stream_toggle.desc",
            icon="📡",
            color_accent="#dc2626",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="hotkey",
                params=HotkeyActionParams(keys=["ctrl", "f10"]).model_dump(exclude_none=True),
            ),
            keywords=["obs", "stream", "live", "broadcast", "стрим", "эфир", "трансляция"],
        ),

        # =========================================================
        # 3. 🚀 launchers (Приложения и Файлы)
        # =========================================================
        ActionPresetDefinition(
            id="launch_terminal",
            category="launchers",
            title_key="deck.editor.presets.launch_terminal.title",
            desc_key="deck.editor.presets.launch_terminal.desc",
            icon="💻",
            color_accent="#10b981",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="launch",
                params=LaunchActionParams(target="wt.exe", kind="app").model_dump(exclude_none=True),
            ),
            keywords=["terminal", "cmd", "powershell", "wt", "bash", "терминал", "консоль", "командная строка"],
        ),
        ActionPresetDefinition(
            id="launch_browser",
            category="launchers",
            title_key="deck.editor.presets.launch_browser.title",
            desc_key="deck.editor.presets.launch_browser.desc",
            icon="🌐",
            color_accent="#38bdf8",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="launch",
                params=LaunchActionParams(target="https://google.com", kind="url").model_dump(exclude_none=True),
            ),
            keywords=["browser", "web", "internet", "chrome", "edge", "браузер", "интернет", "сайт"],
        ),
        ActionPresetDefinition(
            id="open_url",
            category="launchers",
            title_key="deck.editor.presets.open_url.title",
            desc_key="deck.editor.presets.open_url.desc",
            icon="🔗",
            color_accent="#38bdf8",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="launch",
                params=LaunchActionParams(target="https://", kind="url").model_dump(exclude_none=True),
            ),
            keywords=["url", "link", "web", "site", "сайт", "ссылка", "веб", "страница"],
        ),
        ActionPresetDefinition(
            id="launch_app",
            category="launchers",
            title_key="deck.editor.presets.launch_app.title",
            desc_key="deck.editor.presets.launch_app.desc",
            icon="🚀",
            color_accent="#10b981",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="launch",
                params=LaunchActionParams(target="", kind="app").model_dump(exclude_none=True),
            ),
            keywords=["app", "exe", "application", "launch", "run", "приложение", "программа", "запуск"],
        ),
        ActionPresetDefinition(
            id="open_downloads",
            category="launchers",
            title_key="deck.editor.presets.open_downloads.title",
            desc_key="deck.editor.presets.open_downloads.desc",
            icon="📂",
            color_accent="#f59e0b",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="launch",
                params=LaunchActionParams(target="%USERPROFILE%\\Downloads", kind="file").model_dump(exclude_none=True),
            ),
            keywords=["downloads", "folder", "files", "загрузки", "папка", "файлы"],
        ),
        ActionPresetDefinition(
            id="launch_calculator",
            category="launchers",
            title_key="deck.editor.presets.launch_calculator.title",
            desc_key="deck.editor.presets.launch_calculator.desc",
            icon="🧮",
            color_accent="#6366f1",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="launch",
                params=LaunchActionParams(target="calc.exe", kind="app").model_dump(exclude_none=True),
            ),
            keywords=["calculator", "calc", "math", "калькулятор", "расчет"],
        ),

        # =========================================================
        # 4. ⚙️ system_control (Система и Экран)
        # =========================================================
        ActionPresetDefinition(
            id="toggle_dimmer",
            category="system_control",
            title_key="deck.editor.presets.toggle_dimmer.title",
            desc_key="deck.editor.presets.toggle_dimmer.desc",
            icon="🌙",
            color_accent="#f59e0b",
            status_source="dimmer",
            base_action=DeckActionConfig(
                action_type="system",
                params=SystemActionParams(command="toggle_dimmer").model_dump(exclude_none=True),
            ),
            keywords=["dimmer", "screen", "night", "dark", "brightness", "диммер", "экран", "ночь", "темнота", "яркость"],
        ),
        ActionPresetDefinition(
            id="screenshot_primary",
            category="system_control",
            title_key="deck.editor.presets.screenshot_primary.title",
            desc_key="deck.editor.presets.screenshot_primary.desc",
            icon="📸",
            color_accent="#38bdf8",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="system",
                params=SystemActionParams(command="screenshot", screenshot_target="primary").model_dump(exclude_none=True),
            ),
            keywords=["screenshot", "capture", "screen", "image", "скриншот", "снимок", "экран"],
        ),
        ActionPresetDefinition(
            id="lock_workstation",
            category="system_control",
            title_key="deck.editor.presets.lock_workstation.title",
            desc_key="deck.editor.presets.lock_workstation.desc",
            icon="🔒",
            color_accent="#ef4444",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="system",
                params=SystemActionParams(command="lock_workstation").model_dump(exclude_none=True),
            ),
            keywords=["lock", "pc", "windows", "security", "блокировка", "компьютер", "безопасность"],
        ),
        ActionPresetDefinition(
            id="show_desktop",
            category="system_control",
            title_key="deck.editor.presets.show_desktop.title",
            desc_key="deck.editor.presets.show_desktop.desc",
            icon="🗔",
            color_accent="#06b6d4",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="hotkey",
                params=HotkeyActionParams(keys=["win", "d"]).model_dump(exclude_none=True),
            ),
            keywords=["desktop", "minimize", "windows", "рабочий стол", "свернуть", "окна"],
        ),
        ActionPresetDefinition(
            id="task_manager",
            category="system_control",
            title_key="deck.editor.presets.task_manager.title",
            desc_key="deck.editor.presets.task_manager.desc",
            icon="⚡",
            color_accent="#10b981",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="hotkey",
                params=HotkeyActionParams(keys=["ctrl", "shift", "esc"]).model_dump(exclude_none=True),
            ),
            keywords=["task manager", "performance", "processes", "диспетчер задач", "процессы"],
        ),
        ActionPresetDefinition(
            id="close_window",
            category="system_control",
            title_key="deck.editor.presets.close_window.title",
            desc_key="deck.editor.presets.close_window.desc",
            icon="❌",
            color_accent="#ef4444",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="system",
                params=SystemActionParams(command="close_window").model_dump(exclude_none=True),
            ),
            keywords=["close", "window", "kill", "exit", "закрыть", "окно", "выход"],
        ),

        # =========================================================
        # 5. ⌨️ input_macros (Ввод и Макросы)
        # =========================================================
        ActionPresetDefinition(
            id="custom_hotkey",
            category="input_macros",
            title_key="deck.editor.presets.custom_hotkey.title",
            desc_key="deck.editor.presets.custom_hotkey.desc",
            icon="⌨️",
            color_accent="#38bdf8",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="hotkey",
                params=HotkeyActionParams(keys=["ctrl", "c"]).model_dump(exclude_none=True),
            ),
            keywords=["hotkey", "shortcut", "key", "press", "хоткей", "сочетание", "клавиши"],
        ),
        ActionPresetDefinition(
            id="hotkey_toggle",
            category="input_macros",
            title_key="deck.editor.presets.hotkey_toggle.title",
            desc_key="deck.editor.presets.hotkey_toggle.desc",
            icon="⇄",
            color_accent="#a855f7",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="hotkey",
                params=HotkeyActionParams(keys=["f1"], mode="toggle", toggle_keys=["f2"]).model_dump(exclude_none=True),
            ),
            keywords=["toggle", "switch", "state", "триггер", "свитч", "тумблер", "переключатель"],
        ),
        ActionPresetDefinition(
            id="paste_text",
            category="input_macros",
            title_key="deck.editor.presets.paste_text.title",
            desc_key="deck.editor.presets.paste_text.desc",
            icon="📝",
            color_accent="#10b981",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="text",
                params=TextActionParams(text="", send_enter=False).model_dump(exclude_none=True),
            ),
            keywords=["text", "paste", "clipboard", "snippet", "текст", "вставка", "сниппет", "буфер"],
        ),

        # =========================================================
        # 6. 🧭 navigation (Навигация DuckDeck)
        # =========================================================
        ActionPresetDefinition(
            id="nav_next_page",
            category="navigation",
            title_key="deck.editor.presets.nav_next_page.title",
            desc_key="deck.editor.presets.nav_next_page.desc",
            icon="▶",
            color_accent="#71717a",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="deck_nav",
                params=DeckNavActionParams(target="next_page").model_dump(exclude_none=True),
            ),
            keywords=["next", "page", "forward", "следующая", "страница", "вперед"],
        ),
        ActionPresetDefinition(
            id="nav_prev_page",
            category="navigation",
            title_key="deck.editor.presets.nav_prev_page.title",
            desc_key="deck.editor.presets.nav_prev_page.desc",
            icon="◀",
            color_accent="#71717a",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="deck_nav",
                params=DeckNavActionParams(target="prev_page").model_dump(exclude_none=True),
            ),
            keywords=["prev", "previous", "page", "back", "предыдущая", "страница", "назад"],
        ),
        # FUTURE ARCHITECTURE:
        # 'switch_profile' зарезервирован для автоматического переключения профилей DuckDeck
        # по событиям фокуса Windows (EVENT_SYSTEM_FOREGROUND / WinEventProc).

        # =========================================================
        # 7. 🔀 multi_action (Мульти-действия и Макросы)
        # =========================================================
        ActionPresetDefinition(
            id="macro_sequence",
            category="multi_action",
            title_key="deck.editor.presets.macro_sequence.title",
            desc_key="deck.editor.presets.macro_sequence.desc",
            icon="🔀",
            color_accent="#3b82f6",
            status_source=None,
            base_action=DeckActionConfig(
                action_type="macro",
                params=MacroActionParams(steps=[], delay_ms=50).model_dump(exclude_none=True),
            ),
            keywords=["macro", "multi", "sequence", "chain", "batch", "макрос", "мульти", "цепочка", "последовательность"],
            is_wip=True,
        ),
    ]

    @classmethod
    def get_all_presets(cls) -> List[ActionPresetDefinition]:
        """Возвращает все зарегистрированные пресеты действий."""
        return list(cls._PRESETS)

    @classmethod
    def get_preset_by_id(cls, preset_id: str) -> Optional[ActionPresetDefinition]:
        """Поиск пресета по его идентификатору."""
        for p in cls._PRESETS:
            if p.id == preset_id:
                return p
        return None

    @classmethod
    def get_presets_by_category(cls, category_id: str) -> List[ActionPresetDefinition]:
        """Возвращает список пресетов для указанной категории."""
        return [p for p in cls._PRESETS if p.category == category_id]

    @classmethod
    def get_categories_dto(cls) -> List[ActionCategoryDTO]:
        """
        Преобразует категории и их пресеты в список DTO для отображения в шторке ActionLibraryDrawer.
        """
        from modules.deck.editor.dto import ActionCategoryDTO, ActionItemDTO

        result: List[ActionCategoryDTO] = []
        for cat in cls.CATEGORIES:
            cat_id = cat["id"]
            presets_in_cat = cls.get_presets_by_category(cat_id)
            items: List[ActionItemDTO] = []
            for p in presets_in_cat:
                items.append(
                    ActionItemDTO(
                        id=p.id,
                        title_key=p.title_key,
                        category_key=cat["title_key"],
                        icon=p.icon,
                        description_key=p.desc_key,
                        keywords=p.keywords,
                        default_config=p.base_action.model_dump(exclude_none=True),
                        is_wip=p.is_wip,
                        is_enabled=p.is_enabled,
                    )
                )
            result.append(
                ActionCategoryDTO(
                    id=cat_id,
                    title_key=cat["title_key"],
                    icon=cat["icon"],
                    items=items,
                )
            )
        return result

    @classmethod
    def search_presets(cls, query: str) -> List[ActionPresetDefinition]:
        """
        Поиск пресетов по поисковой строке (проверяет id и список keywords).
        """
        q = query.strip().lower()
        if not q:
            return cls.get_all_presets()

        matches: List[ActionPresetDefinition] = []
        for p in cls._PRESETS:
            if q in p.id.lower():
                matches.append(p)
                continue
            if any(q in kw.lower() for kw in p.keywords):
                matches.append(p)
        return matches


__all__ = [
    "ActionPresetsRegistry",
]
