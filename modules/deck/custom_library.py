"""
Хранилище пользовательской библиотеки кнопок и вкладок DuckDeck (CustomLibraryStorage).
Обеспечивает атомарное чтение/запись (tmp + os.replace) в config/deck_custom_library.json,
изолированное от системных пресетов ActionPresetsRegistry.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError

from modules.deck.editor.dto import ActionCategoryDTO, ActionItemDTO
from modules.deck.models import DeckActionConfig

logger = logging.getLogger("duckdock.deck.custom_library")

DEFAULT_CUSTOM_LIBRARY_PATH = "config/deck_custom_library.json"


class CustomTabConfig(BaseModel):
    """Модель пользовательской вкладки (категории) в библиотеке действий."""

    id: str = Field(description="Уникальный идентификатор вкладки")
    title: str = Field(description="Отображаемое название вкладки")
    icon: str = Field(default="📁", description="Иконка вкладки (эмодзи)")


class CustomButtonPreset(BaseModel):
    """Модель сохранённой пользовательской кнопки в библиотеке."""

    id: str = Field(description="Уникальный идентификатор сохранённой кнопки")
    tab_id: str = Field(description="ID родительской пользовательской вкладки")
    title: str = Field(description="Название кнопки")
    icon: str = Field(default="🖲️", description="Эмодзи или путь к графической иконке")
    color_accent: str = Field(default="#38bdf8", description="Неоновый цвет акцента")
    status_source: Optional[str] = Field(default=None, description="Источник живого статуса")
    sound_override: Optional[str] = Field(default=None, description="Переопределение звука клика")
    action: DeckActionConfig = Field(description="Конфигурация действия кнопки")
    keywords: List[str] = Field(default_factory=list, description="Поисковые теги")


class CustomLibraryData(BaseModel):
    """Корневая модель файла config/deck_custom_library.json."""

    tabs: List[CustomTabConfig] = Field(default_factory=list)
    items: List[CustomButtonPreset] = Field(default_factory=list)


class CustomLibraryStorage:
    """
    Менеджер пользовательской библиотеки DuckDeck с атомарным сохранением на диск.
    """

    def __init__(self, file_path: Optional[str] = None) -> None:
        self.file_path: str = file_path or DEFAULT_CUSTOM_LIBRARY_PATH
        self._data: CustomLibraryData = self._load()

    def _load(self) -> CustomLibraryData:
        """Загружает данные библиотеки из JSON или возвращает пустую структуру."""
        if not os.path.exists(self.file_path):
            return CustomLibraryData()
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw, dict):
                return CustomLibraryData()
            return CustomLibraryData.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Failed to load custom library from %s: %s", self.file_path, exc)
            return CustomLibraryData()

    def _save(self) -> None:
        """Атомарно записывает библиотеку на диск через .tmp + os.replace."""
        parent = os.path.dirname(os.path.abspath(self.file_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp_path = f"{self.file_path}.tmp"
        payload = self._data.model_dump(exclude_none=False)
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.file_path)

    def reload(self) -> None:
        """Перечитывает данные библиотеки с диска."""
        self._data = self._load()

    def list_tabs(self) -> List[CustomTabConfig]:
        """Возвращает список всех пользовательских вкладок."""
        return list(self._data.tabs)

    def list_items(self, tab_id: Optional[str] = None) -> List[CustomButtonPreset]:
        """Возвращает список сохранённых кнопок (всех или для конкретной вкладки)."""
        if tab_id is None:
            return list(self._data.items)
        return [it for it in self._data.items if it.tab_id == tab_id]

    def get_item(self, item_id: str) -> Optional[CustomButtonPreset]:
        """Ищет сохранённую кнопку по её идентификатору."""
        for item in self._data.items:
            if item.id == item_id:
                return item
        return None

    def create_tab(self, title: str, icon: str = "📁") -> CustomTabConfig:
        """Создаёт новую пользовательскую вкладку и сохраняет библиотеку."""
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Tab title must not be empty")
        tab = CustomTabConfig(
            id=f"custom_tab_{uuid.uuid4().hex[:8]}",
            title=clean_title,
            icon=icon.strip() or "📁",
        )
        self._data.tabs.append(tab)
        self._save()
        return tab

    def rename_tab(self, tab_id: str, new_title: str) -> bool:
        """Переименовывает пользовательскую вкладку."""
        clean_title = new_title.strip()
        if not clean_title:
            return False
        for tab in self._data.tabs:
            if tab.id == tab_id:
                tab.title = clean_title
                self._save()
                return True
        return False

    def delete_tab(self, tab_id: str) -> bool:
        """Удаляет пользовательскую вкладку и все привязанные к ней кнопки."""
        before_count = len(self._data.tabs)
        self._data.tabs = [tab for tab in self._data.tabs if tab.id != tab_id]
        if len(self._data.tabs) == before_count:
            return False
        self._data.items = [it for it in self._data.items if it.tab_id != tab_id]
        self._save()
        return True

    def add_item(
        self,
        tab_id: str,
        item: Union[CustomButtonPreset, dict[str, Any]],
    ) -> CustomButtonPreset:
        """Добавляет сохранённую кнопку в указанную пользовательскую вкладку."""
        if not any(tab.id == tab_id for tab in self._data.tabs):
            raise ValueError(f"Custom tab '{tab_id}' does not exist")

        if isinstance(item, dict):
            data = dict(item)
            data["tab_id"] = tab_id
            if not data.get("id"):
                data["id"] = f"custom_btn_{uuid.uuid4().hex[:8]}"
            preset = CustomButtonPreset.model_validate(data)
        else:
            preset = item.model_copy(deep=True)
            preset.tab_id = tab_id
            if not preset.id:
                preset.id = f"custom_btn_{uuid.uuid4().hex[:8]}"

        self._data.items.append(preset)
        self._save()
        return preset

    def rename_item(self, item_id: str, new_title: str) -> bool:
        """Переименовывает сохранённую кнопку в библиотеке."""
        clean_title = new_title.strip()
        if not clean_title:
            return False
        for item in self._data.items:
            if item.id == item_id:
                item.title = clean_title
                self._save()
                return True
        return False

    def delete_item(self, item_id: str) -> bool:
        """Удаляет сохранённую кнопку из библиотеки."""
        before_count = len(self._data.items)
        self._data.items = [it for it in self._data.items if it.id != item_id]
        if len(self._data.items) == before_count:
            return False
        self._save()
        return True

    def to_categories_dto(self) -> List[ActionCategoryDTO]:
        """Преобразует пользовательские вкладки и кнопки в список ActionCategoryDTO."""
        categories: List[ActionCategoryDTO] = []
        for tab in self._data.tabs:
            tab_items: List[ActionItemDTO] = []
            for item in self._data.items:
                if item.tab_id != tab.id:
                    continue
                keywords = list(item.keywords) if item.keywords else [item.title]
                if tab.title not in keywords:
                    keywords.append(tab.title)
                tab_items.append(
                    ActionItemDTO(
                        id=item.id,
                        title_key="",
                        raw_title=item.title,
                        category_key="",
                        icon=item.icon,
                        keywords=keywords,
                        default_config={
                            "id": item.id,
                            "title": item.title,
                            "icon": item.icon,
                            "color_accent": item.color_accent,
                            "status_source": item.status_source,
                            "sound_override": item.sound_override,
                            "action": item.action.model_dump(exclude_none=True),
                        },
                        is_wip=False,
                        is_enabled=True,
                        is_custom=True,
                    )
                )
            categories.append(
                ActionCategoryDTO(
                    id=tab.id,
                    title_key="",
                    raw_title=tab.title,
                    icon=tab.icon,
                    items=tab_items,
                    is_expanded=False,
                    is_custom=True,
                )
            )
        return categories
