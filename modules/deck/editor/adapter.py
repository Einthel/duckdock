"""
Двусторонний адаптер конфигурации DuckDeck (DeckConfigAdapter).
Реализует бесшовную трансляцию между Pydantic v2 моделями (DeckRootConfig, DeckButtonConfig)
и презентационными DTO редактора (ButtonSlotDTO) со 100% сохранением расширенных полей:
  - color_accent, status_source, sound_override, toggle_action
  - Сохранение контекста многостраничной структуры (Pages 1..N)
  - Атомарное сохранение на диск с созданием .tmp, .bak и вызовом os.replace().
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import ValidationError

from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.models import (
    ActionCategory,
    ActionType,
    DeckActionConfig,
    DeckButtonConfig,
    DeckConfigLoader,
    DeckPageConfig,
    DeckRootConfig,
    HotkeyParams,
)

logger = logging.getLogger("duckdock.deck.editor.adapter")


class DeckConfigAdapter:
    """
    Двусторонний адаптер трансляции и атомарного I/O конфигурации макро-панели DuckDeck.
    Служит связующим мостом между Pydantic v2 моделями ядра и интерфейсом редактора.
    """

    @classmethod
    def slot_to_dto(cls, button_config: DeckButtonConfig) -> ButtonSlotDTO:
        """
        Транслирует Pydantic v2 DeckButtonConfig в легковесный ButtonSlotDTO
        со 100% сохранением расширенных полей (color_accent, status_source, sound_override, toggle_action).
        """
        hotkey_str = ""
        action_type_display = "Hotkey"
        category_display = "System: Hotkey"

        action = button_config.action
        if action.action_type == "hotkey":
            keys = action.params.get("keys", [])
            if keys:
                hotkey_str = cls._format_keys_to_string(keys)
            action_type_display = "Hotkey"
            category_display = "System: Hotkey"
        elif action.action_type == "launch":
            action_type_display = "Open Application"
            category_display = "System: Open Application"
        elif action.action_type == "audio_device":
            action_type_display = "Audio Device"
            category_display = "System: Audio Device"
        elif action.action_type == "system":
            action_type_display = "System"
            category_display = "System"
        elif action.action_type == "screenshot":
            action_type_display = "Screenshot"
            category_display = "System: Screenshot"
        elif action.action_type == "http_request":
            action_type_display = "HTTP Request"
            category_display = "API: HTTP Request"
        elif action.action_type == "navigation":
            action_type_display = "Navigation"
            category_display = "Navigation"
        else:
            action_type_display = str(action.action_type).capitalize()
            category_display = str(button_config.category).capitalize()

        return ButtonSlotDTO(
            slot_index=button_config.slot_index,
            title=button_config.title,
            icon=button_config.icon,
            category=category_display,
            action_type=action_type_display,
            hotkey=hotkey_str,
            font_size=11,
            font_color="#d4d4d8",
            color_accent=button_config.color_accent,
            status_source=button_config.status_source,
            sound_override=button_config.sound_override,
            toggle_action=button_config.toggle_action.model_copy(deep=True) if button_config.toggle_action else None,
            original_config=button_config.model_copy(deep=True),
        )

    @classmethod
    def dto_to_slot(
        cls,
        dto: ButtonSlotDTO,
        original_config: Optional[DeckButtonConfig] = None,
    ) -> DeckButtonConfig:
        """
        Конвертирует ButtonSlotDTO в валидный DeckButtonConfig с сохранением
        расширенных метаданных и слиянием модифицированных пользователем полей.
        """
        orig = original_config or getattr(dto, "original_config", None)

        # 1. Извлечение и слияние color_accent
        color_accent = getattr(dto, "color_accent", None)
        if not color_accent and orig:
            color_accent = orig.color_accent
        elif not color_accent:
            color_accent = "#38bdf8"

        # 2. Извлечение и слияние status_source
        status_source = getattr(dto, "status_source", None)
        if status_source is None and orig:
            status_source = orig.status_source

        # 3. Извлечение и слияние sound_override
        sound_override = getattr(dto, "sound_override", None)
        if sound_override is None and orig:
            sound_override = orig.sound_override

        # 4. Извлечение и слияние toggle_action
        toggle_action = getattr(dto, "toggle_action", None)
        if toggle_action is None and orig:
            toggle_action = orig.toggle_action.model_copy(deep=True) if orig.toggle_action else None
        elif isinstance(toggle_action, dict):
            toggle_action = DeckActionConfig.model_validate(toggle_action)

        # 5. Слияние с оригинальной конфигурацией
        if orig is not None:
            action = orig.action.model_copy(deep=True)
            category = orig.category

            if dto.hotkey and dto.hotkey.strip():
                parsed_keys = cls._parse_hotkey_string(dto.hotkey)
                action = DeckActionConfig(action_type="hotkey", params={"keys": parsed_keys})
                category = "shortcut"
            elif dto.action_type:
                norm_type = cls._normalize_action_type(dto.action_type)
                if norm_type != orig.action.action_type:
                    action, category = cls._create_default_action(norm_type)

            return DeckButtonConfig(
                id=orig.id,
                slot_index=dto.slot_index,
                name=orig.name or dto.title or f"Slot {dto.slot_index}",
                title=dto.title,
                category=category,
                icon=dto.icon if dto.icon else orig.icon,
                icon_path=orig.icon_path,
                icon_size=orig.icon_size,
                color_accent=color_accent,
                background_color=orig.background_color,
                action=action,
                toggle_action=toggle_action,
                status_source=status_source,
                sound_override=sound_override,
            )

        # 6. Создание нового слота с дефолтными атрибутами Pydantic v2
        btn_id = f"btn_slot_{dto.slot_index}"
        title = dto.title or ""
        icon = dto.icon or "⚡"

        if dto.hotkey and dto.hotkey.strip():
            parsed_keys = cls._parse_hotkey_string(dto.hotkey)
            action = DeckActionConfig(action_type="hotkey", params={"keys": parsed_keys})
            category = "shortcut"
        elif dto.action_type:
            norm_type = cls._normalize_action_type(dto.action_type)
            action, category = cls._create_default_action(norm_type)
        else:
            action = DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"})
            category = "system"

        return DeckButtonConfig(
            id=btn_id,
            slot_index=dto.slot_index,
            name=title or f"Slot {dto.slot_index}",
            title=title,
            category=category,
            icon=icon,
            icon_size=48,
            color_accent=color_accent,
            background_color="#161b26",
            action=action,
            toggle_action=toggle_action,
            status_source=status_source,
            sound_override=sound_override,
        )

    @classmethod
    def load_page_slots(
        cls,
        root_config: DeckRootConfig,
        page_id_or_index: Union[str, int] = 0,
    ) -> dict[int, ButtonSlotDTO]:
        """
        Загружает словарь слотов 0..9 для указанной страницы (по ID или числовому индексу).
        Слоты без кнопок инициализируются пустыми ButtonSlotDTO(slot_index=i).
        """
        target_page: Optional[DeckPageConfig] = None

        if isinstance(page_id_or_index, int):
            if 0 <= page_id_or_index < len(root_config.pages):
                target_page = root_config.pages[page_id_or_index]
        elif isinstance(page_id_or_index, str):
            for p in root_config.pages:
                if p.id == page_id_or_index:
                    target_page = p
                    break
            if target_page is None:
                for p in root_config.pages:
                    if p.name == page_id_or_index:
                        target_page = p
                        break
            if target_page is None and page_id_or_index.isdigit():
                idx = int(page_id_or_index)
                if 0 <= idx < len(root_config.pages):
                    target_page = root_config.pages[idx]

        if target_page is None:
            if root_config.pages:
                target_page = root_config.pages[0]
                logger.warning(
                    "Page '%s' not found in DeckRootConfig. Fallback to first page '%s'.",
                    page_id_or_index,
                    target_page.id,
                )
            else:
                logger.warning("DeckRootConfig has no pages. Returning empty slots 0..9.")
                return {i: ButtonSlotDTO(slot_index=i) for i in range(10)}

        result: dict[int, ButtonSlotDTO] = {i: ButtonSlotDTO(slot_index=i) for i in range(10)}
        for btn in target_page.buttons:
            if 0 <= btn.slot_index <= 9:
                result[btn.slot_index] = cls.slot_to_dto(btn)

        return result

    @classmethod
    def apply_slots_to_page(
        cls,
        root_config: DeckRootConfig,
        page_id_or_index: Union[str, int],
        slots: dict[int, ButtonSlotDTO],
    ) -> DeckRootConfig:
        """
        Интегрирует обновленные слоты в целевую страницу DeckRootConfig
        с сохранением структуры остальных страниц (Pages 1..N).
        """
        updated_root = root_config.model_copy(deep=True)

        target_page_idx = -1
        if isinstance(page_id_or_index, int):
            if 0 <= page_id_or_index < len(updated_root.pages):
                target_page_idx = page_id_or_index
        elif isinstance(page_id_or_index, str):
            for idx, p in enumerate(updated_root.pages):
                if p.id == page_id_or_index:
                    target_page_idx = idx
                    break
            if target_page_idx == -1:
                for idx, p in enumerate(updated_root.pages):
                    if p.name == page_id_or_index:
                        target_page_idx = idx
                        break
            if target_page_idx == -1 and page_id_or_index.isdigit():
                idx = int(page_id_or_index)
                if 0 <= idx < len(updated_root.pages):
                    target_page_idx = idx

        if target_page_idx == -1:
            page_id = str(page_id_or_index) if page_id_or_index else "default"
            new_page = DeckPageConfig(
                id=page_id,
                name=f"Page {len(updated_root.pages) + 1}",
                grid_rows=2,
                grid_cols=5,
                buttons=[],
            )
            updated_root.pages.append(new_page)
            target_page_idx = len(updated_root.pages) - 1

        target_page = updated_root.pages[target_page_idx]
        existing_by_slot = {b.slot_index: b for b in target_page.buttons}

        new_buttons_by_slot: dict[int, DeckButtonConfig] = {}

        # 1. Сохраняем не затронутые вызовом кнопки (если передан частичный dict слотов)
        for s_idx, btn in existing_by_slot.items():
            if s_idx not in slots:
                new_buttons_by_slot[s_idx] = btn

        # 2. Обрабатываем переданные слоты
        for slot_idx, dto in slots.items():
            orig_btn = getattr(dto, "original_config", None) or existing_by_slot.get(slot_idx)

            # Проверка очищенного/пустого слота
            is_empty = (
                not dto.title
                and not dto.hotkey
                and dto.icon in ("", "🖲️")
                and (
                    not getattr(dto, "original_config", None)
                    or (dto.title == "" and not dto.hotkey and not dto.icon)
                )
            )
            if is_empty:
                continue

            btn_config = cls.dto_to_slot(dto, original_config=orig_btn)
            new_buttons_by_slot[slot_idx] = btn_config

        # 3. Финальная сортировка по slot_index
        sorted_buttons = [new_buttons_by_slot[idx] for idx in sorted(new_buttons_by_slot.keys())]
        target_page.buttons = sorted_buttons

        return updated_root

    @classmethod
    def save_deck_config_atomic(
        cls,
        cfg: DeckRootConfig,
        file_path: str = "config/deck_config.json",
    ) -> bool:
        """
        Атомарно сохраняет DeckRootConfig в JSON-файл:
          1. Проверяет валидность Pydantic v2.
          2. Создает директорию назначения (если отсутствует).
          3. Сериализует модель в JSON с форматированием.
          4. Записывает данные во временный файл .tmp с fsync.
          5. При наличии существующего файла создает бэкап .bak.
          6. Выполняет атомарную замену через os.replace().
          7. При сбоях очищает .tmp и логирует ошибку без повреждения боевого файла.
        """
        tmp_path: Optional[str] = None
        try:
            # 1. Валидация входной структуры Pydantic v2
            if not isinstance(cfg, DeckRootConfig):
                try:
                    cfg = DeckRootConfig.model_validate(cfg)
                except ValidationError as val_err:
                    logger.error("DeckRootConfig validation error before saving: %s", val_err)
                    return False

            # 2. Сериализация в форматированный JSON
            json_data = cfg.model_dump_json(indent=2)

            # 3. Формирование путей на том же логическом диске
            abs_path = os.path.abspath(file_path)
            parent_dir = os.path.dirname(abs_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            tmp_path = f"{abs_path}.tmp"
            bak_path = f"{abs_path}.bak"

            # 4. Запись во временный файл со сбросом системных буферов (fsync)
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(json_data)
                f.flush()
                os.fsync(f.fileno())

            # 5. Создание резервной копии существующего файла
            if os.path.exists(abs_path):
                try:
                    shutil.copy2(abs_path, bak_path)
                except Exception as bak_err:
                    logger.warning("Failed to create backup copy '%s': %s", bak_path, bak_err)

            # 6. Атомарная замена файла
            os.replace(tmp_path, abs_path)
            tmp_path = None  # Файл успешно перемещен

            logger.info("Deck configuration successfully saved atomically to '%s'", abs_path)
            return True

        except (IOError, OSError, ValidationError, Exception) as exc:
            logger.error(
                "Failed to atomically save deck configuration to '%s': %s",
                file_path,
                exc,
                exc_info=True,
            )
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            return False

    @classmethod
    def load_deck_config(cls, file_path: str = "config/deck_config.json") -> DeckRootConfig:
        """
        Загружает DeckRootConfig из файла с валидацией Pydantic v2 и автоматическим fallback.
        """
        return DeckConfigLoader.load_from_file(file_path)

    # ==========================================================================
    # Вспомогательные методы форматирования и нормализации
    # ==========================================================================

    @staticmethod
    def _format_keys_to_string(keys: list[str]) -> str:
        """Форматирует список клавиш в удобочитаемую строку комбинации (например, 'Ctrl + Shift + D')."""
        parts: list[str] = []
        for k in keys:
            lk = k.strip().lower()
            if lk == "ctrl":
                parts.append("Ctrl")
            elif lk == "alt":
                parts.append("Alt")
            elif lk == "shift":
                parts.append("Shift")
            elif lk in ("win", "cmd", "meta"):
                parts.append("Win")
            elif lk.startswith("f") and lk[1:].isdigit():
                parts.append(lk.upper())
            elif len(lk) == 1:
                parts.append(lk.upper())
            else:
                parts.append(lk.capitalize())
        return " + ".join(parts)

    @staticmethod
    def _parse_hotkey_string(hotkey_str: str) -> list[str]:
        """Парсит строку хоткея ('Ctrl + Shift + D') в канонический список клавиш ['ctrl', 'shift', 'd']."""
        if not hotkey_str or not hotkey_str.strip():
            return []
        raw_keys = [k.strip() for k in hotkey_str.split("+") if k.strip()]
        keys: list[str] = []
        for k in raw_keys:
            lk = k.lower()
            if lk in ("control", "ctrl"):
                keys.append("ctrl")
            elif lk in ("alt", "option"):
                keys.append("alt")
            elif lk == "shift":
                keys.append("shift")
            elif lk in ("win", "cmd", "meta", "super"):
                keys.append("win")
            else:
                keys.append(lk)
        return keys

    @staticmethod
    def _normalize_action_type(action_type_str: str) -> str:
        """Нормализует пользовательскую строку типа действия в канонический ActionType."""
        raw = action_type_str.strip().lower().replace(" ", "_")
        if raw in ("hotkey", "shortcut"):
            return "hotkey"
        if raw in ("open_application", "launch", "program", "launch_app"):
            return "launch"
        if raw in ("audio_device", "audio"):
            return "audio_device"
        if raw in ("screenshot", "screen"):
            return "screenshot"
        if raw in ("http_request", "api", "rest"):
            return "http_request"
        if raw in ("navigation", "page", "switch_page"):
            return "navigation"
        return "system"

    @classmethod
    def _create_default_action(cls, action_type: str) -> Tuple[DeckActionConfig, ActionCategory]:
        """Создает дефолтное действие DeckActionConfig и сопоставляет ActionCategory."""
        if action_type == "hotkey":
            return (
                DeckActionConfig(action_type="hotkey", params={"keys": []}),
                "shortcut",
            )
        if action_type == "launch":
            return (
                DeckActionConfig(action_type="launch", params={"path": "", "args": []}),
                "program",
            )
        if action_type == "audio_device":
            return (
                DeckActionConfig(
                    action_type="audio_device",
                    params={"mode": "toggle", "devices": ["Наушники", "Динамики"]},
                ),
                "system",
            )
        if action_type == "screenshot":
            return (
                DeckActionConfig(
                    action_type="screenshot",
                    params={"target": "primary_screen", "clipboard": True},
                ),
                "system",
            )
        if action_type == "http_request":
            return (
                DeckActionConfig(
                    action_type="http_request",
                    params={"url": "", "method": "POST"},
                ),
                "api",
            )
        if action_type == "navigation":
            return (
                DeckActionConfig(
                    action_type="navigation",
                    params={"target_page_id": "default"},
                ),
                "system",
            )
        return (
            DeckActionConfig(
                action_type="system",
                params={"command": "toggle_dimmer"},
            ),
            "system",
        )


__all__ = ["DeckConfigAdapter"]
