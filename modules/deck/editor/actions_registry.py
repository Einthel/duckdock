"""
Единый фасад каталога действий библиотеки DuckDeck (Action Library).
Делегирует получение категорий и пресетов в ActionPresetsRegistry (Single Source of Truth).
"""
from __future__ import annotations

from modules.deck.editor.dto import ActionCategoryDTO


def get_default_action_catalog() -> list[ActionCategoryDTO]:
    """
    Возвращает стандартный каталог библиотеки действий из ActionPresetsRegistry (SSOT),
    разбитый на 8 категорий таксономии с двуязычными тегами поиска (RU/EN) и ключами локализации.
    """
    from modules.deck.presets import ActionPresetsRegistry

    return ActionPresetsRegistry.get_categories_dto()
