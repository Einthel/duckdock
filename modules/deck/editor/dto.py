"""
DTO-структуры данных для редактора DuckDeck (KeyPropertyInspector, Touchbar и Action Library).
Изолированные легковесные контракты состояния без зависимостей от логики ядра.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.i18n import t


@dataclass
class ButtonSlotDTO:
    """
    Модель данных слота макро-кнопки сетки (0..9).
    """

    slot_index: int
    title: str = ""
    icon: str = "🖲️"
    category: str = "System: Hotkey"
    action_type: str = "Hotkey"
    hotkey: str = ""
    font_size: int = 11
    font_color: str = "#d4d4d8"


@dataclass
class TouchbarMediaDTO:
    """
    Модель данных настроек медиаплеера тачбара (3-й ряд).
    """

    player: str = "Default"
    marquee_enabled: bool = True
    marquee_speed: int = 50


@dataclass
class TouchbarClockDTO:
    """
    Модель данных настроек блока часов и свайп-навигации тачбара.
    """

    is_24h: bool = True
    show_date: bool = True
    swipe_sensitivity: int = 3


@dataclass
class TouchbarTelemetryDTO:
    """
    Модель данных настроек блока системных датчиков тачбара.
    """

    show_cpu: bool = True
    show_gpu: bool = True
    refresh_interval_s: int = 2


@dataclass
class ActionItemDTO:
    """
    Модель действия библиотеки DuckDeck (System, Navigation, Media, etc.).
    """

    id: str
    title_key: str
    category_key: str
    icon: str
    description_key: str = ""
    keywords: list[str] = field(default_factory=list)
    default_config: dict[str, Any] = field(default_factory=dict)

    def get_title(self) -> str:
        """Возвращает локализованное название действия."""
        return t(self.title_key)


@dataclass
class ActionCategoryDTO:
    """
    Модель категории действий библиотеки DuckDeck.
    """

    id: str
    title_key: str
    icon: str = ""
    items: list[ActionItemDTO] = field(default_factory=list)
    is_expanded: bool = False

    def get_title(self) -> str:
        """Возвращает локализованное название категории."""
        return t(self.title_key)
