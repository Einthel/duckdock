"""
Пакет визуального редактора макро-панели DuckDeck.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .actions_registry import get_default_action_catalog
from .demo_data import get_demo_editor_profile, load_demo_profile_into_window
from .dto import (
    ActionCategoryDTO,
    ActionItemDTO,
    ButtonSlotDTO,
    TouchbarClockDTO,
    TouchbarMediaDTO,
    TouchbarTelemetryDTO,
)
from .styles import (
    ACTION_ITEM_HEIGHT,
    CATEGORY_HEADER_HEIGHT,
    DRAWER_PADDING,
    EDITOR_MAIN_QSS,
    INPUT_HEIGHT,
    INSPECTOR_HEIGHT,
    PREVIEW_TILE_SIZE,
    SEARCH_BAR_HEIGHT,
    ToolbarVLine,
    apply_editor_theme,
    apply_immersive_dark_titlebar,
)

if TYPE_CHECKING:
    from .widgets.action_category import ActionCategoryHeader, ActionCategorySection
    from .widgets.action_drawer import ActionAccordionWidget, ActionLibraryDrawer
    from .widgets.action_item import ActionItemWidget
    from .widgets.button_property_form import ButtonPropertyForm
    from .widgets.deck_canvas import DeckCanvasWidget
    from .widgets.grid_cell import EditorGridCell
    from .widgets.header_bar import (
        DeviceComboBox,
        EditorHeaderBar,
        HeaderIconButton,
        ProfileComboBox,
    )
    from .widgets.hotkey_capture import HotkeyCaptureButton
    from .widgets.key_preview_tile import KeyPreviewTile
    from .widgets.pagination_bar import PageNavigationBar
    from .widgets.property_inspector import KeyPropertyInspector
    from .widgets.search_bar import ActionSearchBar
    from .widgets.touchbar_property_forms import (
        TouchbarClockForm,
        TouchbarMediaForm,
        TouchbarTelemetryForm,
    )
    from .widgets.touchbar_section import TouchbarSectionWidget
    from .widgets.touchbar_strip import EditorTouchbarStrip
    from .window import DeckEditorWindow

__all__ = [
    "DeckEditorWindow",
    "DeviceComboBox",
    "EditorHeaderBar",
    "HeaderIconButton",
    "ProfileComboBox",
    "DeckCanvasWidget",
    "EditorGridCell",
    "EditorTouchbarStrip",
    "TouchbarSectionWidget",
    "PageNavigationBar",
    "KeyPreviewTile",
    "HotkeyCaptureButton",
    "ButtonPropertyForm",
    "TouchbarMediaForm",
    "TouchbarClockForm",
    "TouchbarTelemetryForm",
    "KeyPropertyInspector",
    "ActionSearchBar",
    "ActionItemWidget",
    "ActionCategoryHeader",
    "ActionCategorySection",
    "ActionAccordionWidget",
    "ActionLibraryDrawer",
    "ButtonSlotDTO",
    "TouchbarMediaDTO",
    "TouchbarClockDTO",
    "TouchbarTelemetryDTO",
    "ActionItemDTO",
    "ActionCategoryDTO",
    "get_default_action_catalog",
    "get_demo_editor_profile",
    "load_demo_profile_into_window",
    "INSPECTOR_HEIGHT",
    "PREVIEW_TILE_SIZE",
    "INPUT_HEIGHT",
    "SEARCH_BAR_HEIGHT",
    "ACTION_ITEM_HEIGHT",
    "CATEGORY_HEADER_HEIGHT",
    "DRAWER_PADDING",
    "EDITOR_MAIN_QSS",
    "ToolbarVLine",
    "apply_editor_theme",
    "apply_immersive_dark_titlebar",
]


def __getattr__(name: str) -> Any:
    if name == "DeckEditorWindow":
        from .window import DeckEditorWindow
        return DeckEditorWindow
    if name in ("EditorHeaderBar", "DeviceComboBox", "ProfileComboBox", "HeaderIconButton"):
        from .widgets import header_bar
        return getattr(header_bar, name)
    if name == "DeckCanvasWidget":
        from .widgets.deck_canvas import DeckCanvasWidget
        return DeckCanvasWidget
    if name == "EditorGridCell":
        from .widgets.grid_cell import EditorGridCell
        return EditorGridCell
    if name == "EditorTouchbarStrip":
        from .widgets.touchbar_strip import EditorTouchbarStrip
        return EditorTouchbarStrip
    if name == "TouchbarSectionWidget":
        from .widgets.touchbar_section import TouchbarSectionWidget
        return TouchbarSectionWidget
    if name == "PageNavigationBar":
        from .widgets.pagination_bar import PageNavigationBar
        return PageNavigationBar
    if name == "KeyPreviewTile":
        from .widgets.key_preview_tile import KeyPreviewTile
        return KeyPreviewTile
    if name == "HotkeyCaptureButton":
        from .widgets.hotkey_capture import HotkeyCaptureButton
        return HotkeyCaptureButton
    if name == "ButtonPropertyForm":
        from .widgets.button_property_form import ButtonPropertyForm
        return ButtonPropertyForm
    if name in ("TouchbarMediaForm", "TouchbarClockForm", "TouchbarTelemetryForm"):
        from .widgets import touchbar_property_forms
        return getattr(touchbar_property_forms, name)
    if name == "KeyPropertyInspector":
        from .widgets.property_inspector import KeyPropertyInspector
        return KeyPropertyInspector
    if name == "ActionSearchBar":
        from .widgets.search_bar import ActionSearchBar
        return ActionSearchBar
    if name == "ActionItemWidget":
        from .widgets.action_item import ActionItemWidget
        return ActionItemWidget
    if name in ("ActionCategoryHeader", "ActionCategorySection"):
        from .widgets import action_category
        return getattr(action_category, name)
    if name in ("ActionAccordionWidget", "ActionLibraryDrawer"):
        from .widgets import action_drawer
        return getattr(action_drawer, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
