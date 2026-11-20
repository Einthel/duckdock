"""
Подсистема локализации DuckDock (i18n).
Предоставляет фасад для доступа к менеджеру переводов, плюрализации и быстрым функциям t/tp.
"""
from core.i18n.manager import I18nManager, SafeFormatter, t, tp
from core.i18n.plural import (
    get_plural_category_en,
    get_plural_category_ru,
    resolve_plural_category,
)

__all__ = [
    "I18nManager",
    "SafeFormatter",
    "t",
    "tp",
    "get_plural_category_ru",
    "get_plural_category_en",
    "resolve_plural_category",
]
