"""
Виджеты и компоненты редактора DuckDeck.
"""
from __future__ import annotations

from .button_property_form import ButtonPropertyForm
from .deck_canvas import DeckCanvasWidget
from .grid_cell import EditorGridCell
from .header_bar import (
    DeviceComboBox,
    EditorHeaderBar,
    HeaderIconButton,
    ProfileComboBox,
    ToolbarVLine,
)
from .hotkey_capture import HotkeyCaptureButton
from .icon_library_dialog import IconLibraryDialog, IconTileWidget
from .key_preview_tile import KeyPreviewTile
from .pagination_bar import PageNavigationBar
from .placeholders import (
    ActionListSlot,
    CanvasAreaSlot,
    HeaderBarSlot,
    InspectorSlot,
    PaginationBarSlot,
    PlaceholderBox,
    SearchSlot,
)
from .search_bar import ActionSearchBar
from .touchbar_property_forms import (
    TouchbarClockForm,
    TouchbarMediaForm,
    TouchbarTelemetryForm,
)
from .touchbar_section import TouchbarSectionWidget
from .touchbar_strip import EditorTouchbarStrip

__all__ = [
    "PlaceholderBox",
    "HeaderBarSlot",
    "CanvasAreaSlot",
    "PaginationBarSlot",
    "InspectorSlot",
    "SearchSlot",
    "ActionListSlot",
    "ActionSearchBar",
    "DeviceComboBox",
    "ProfileComboBox",
    "HeaderIconButton",
    "ToolbarVLine",
    "EditorHeaderBar",
    "EditorGridCell",
    "TouchbarSectionWidget",
    "EditorTouchbarStrip",
    "PageNavigationBar",
    "DeckCanvasWidget",
    "KeyPreviewTile",
    "IconLibraryDialog",
    "IconTileWidget",
    "HotkeyCaptureButton",
    "ButtonPropertyForm",
    "TouchbarMediaForm",
    "TouchbarClockForm",
    "TouchbarTelemetryForm",
]
