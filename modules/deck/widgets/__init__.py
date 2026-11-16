"""
Виджеты сенсорной панели DuckDeck.
"""
from modules.deck.widgets.deck_button import DeckButtonWidget
from modules.deck.widgets.deck_grid import DeckGrid
from modules.deck.widgets.header_bar import HeaderBar
from modules.deck.widgets.swipe_detector import DeckSwipeDetector, _extract_point_pos
from modules.deck.widgets.interactive_panel import (
    DeckCenterSection,
    DeckInteractivePanel,
    DeckLeftSection,
    DeckRightSection,
    DotPagingWidget,
)

__all__ = [
    "DeckButtonWidget",
    "DeckGrid",
    "HeaderBar",
    "DeckInteractivePanel",
    "DeckCenterSection",
    "DeckLeftSection",
    "DeckRightSection",
    "DeckSwipeDetector",
    "DotPagingWidget",
]
