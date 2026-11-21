"""
Модуль стилей и дизайн-токенов редактора DuckDeck (Dark Obsidian Design System).
Включает токены палитры, геометрию, единую таблицу стилей QSS и функцию темного заголовка Win32.
"""
from __future__ import annotations

import ctypes
import sys
from typing import Any, Optional

from PySide6.QtWidgets import QFrame, QWidget

# ==============================================================================
# Цветовая палитра Dark Obsidian
# ==============================================================================
BG_WINDOW = "#121214"
BG_PANEL = "#18181b"
BG_CARD = "#222227"
BG_STRIP = "#161b26"
BG_STRIP_SECTION_HOVER = "#1e2638"

BORDER_SUBTLE = "#2e2e36"
BORDER_FOCUS = "#0078d4"
BORDER_FOCUS_ACCENT = "#38bdf8"
BORDER_HOVER = "#3f3f46"

TEXT_PRIMARY = "#f4f4f5"
TEXT_SECONDARY = "#9ca3af"
TEXT_MUTED = "#71717a"
TEXT_PLACEHOLDER = "#71717a"

ACCENT_DANGER = "#ef4444"

# Константы тулбара и выпадающих списков (Header Bar & Dropdowns)
BG_DROPDOWN = "#222227"
BG_DROPDOWN_HOVER = "#2a2a32"
BG_DROPDOWN_OPEN = "#18181b"
BORDER_DROPDOWN_FOCUS = "#0078d4"

TOOLTIP_BG = "#1e1e24"
TOOLTIP_BORDER = "#3f3f46"

# ==============================================================================
# Токены геометрии и компоновки
# ==============================================================================
WINDOW_DEFAULT_SIZE = (1080, 740)
WINDOW_MIN_SIZE = (960, 640)

WORKSPACE_MIN_WIDTH = 640
DRAWER_MIN_WIDTH = 280
DRAWER_MAX_WIDTH = 420

HEADER_SLOT_HEIGHT = 52
HEADER_HEIGHT = 52
TOOL_BUTTON_SIZE = 32

CANVAS_SLOT_MIN_HEIGHT = 300
PAGINATION_SLOT_HEIGHT = 36
INSPECTOR_SLOT_HEIGHT = 220
SEARCH_SLOT_HEIGHT = 52

# ==============================================================================
# Токены сетки холста, тачбара и пагинации (Canvas Grid & Touchbar Geometry)
# ==============================================================================
GRID_CELL_SIZE = 96
GRID_SPACING = 12
GRID_CORNER_RADIUS = 12

TOUCHBAR_HEIGHT = 68
TOUCHBAR_WIDTH = 528
TOUCHBAR_RADIUS = 12

PAGE_NAV_BTN_SIZE = 28

BG_CELL = "#222227"
BG_CELL_HOVER = "#2a2a32"
BG_TOUCHBAR = "#161b26"
BG_SECTION_HOVER = "#1e2638"
BG_SECTION_HOVER_SUBTLE = "#1a2233"

BORDER_CELL = "#2e2e36"
BORDER_CELL_HOVER = "#3f3f46"
BORDER_TOUCHBAR = "#2a3447"
BORDER_SELECTED = "#0078d4"
BORDER_SELECTED_GLOW = "#38bdf8"

# ==============================================================================
# Токены инспектора свойств и превью-плитки (Property Inspector & Tile Geometry)
# ==============================================================================
INSPECTOR_HEIGHT = 220
PREVIEW_TILE_SIZE = 84
INPUT_HEIGHT = 30
FORM_LABEL_WIDTH = 60
ICON_BTN_SIZE = 18

BG_INSPECTOR = "#18181b"
BG_PREVIEW_TILE = "#222227"
BORDER_PREVIEW_TILE = "#2e2e36"
BORDER_PREVIEW_HOVER = "#3f3f46"
TEXT_HEADER_CATEGORY = "#e4e4e7"
BTN_DELETE_HOVER = "#ef4444"
HOTKEY_CAPTURING_BORDER = "#38bdf8"

# ==============================================================================
# Токены библиотеки действий и поиска (Action Library & Search Bar)
# ==============================================================================
SEARCH_BAR_HEIGHT = 36
ACTION_ITEM_HEIGHT = 36
CATEGORY_HEADER_HEIGHT = 38
DRAWER_PADDING = 8

BG_SEARCH_INPUT = "#18181b"
BG_ACTION_ITEM_HOVER = "#27272a"
BG_ACTION_ITEM_ACTIVE = "#1e2638"
TEXT_CATEGORY_TITLE = "#f4f4f5"
CHEVRON_COLOR = "#9ca3af"

# ==============================================================================
# Единая таблица стилей EDITOR_MAIN_QSS
# ==============================================================================
EDITOR_MAIN_QSS = f"""
QMainWindow {{
    background-color: {BG_WINDOW};
    color: {TEXT_PRIMARY};
}}

QWidget#editorCentralWidget {{
    background-color: {BG_WINDOW};
}}

QWidget#workspaceContainer, QWidget#drawerContainer {{
    background-color: {BG_WINDOW};
}}

/* QSplitter */
QSplitter {{
    background-color: {BG_WINDOW};
}}

QSplitter::handle:horizontal {{
    background-color: {BORDER_SUBTLE};
    width: 2px;
}}

QSplitter::handle:horizontal:hover {{
    background-color: {BORDER_FOCUS_ACCENT};
}}

/* Тонкие кастомные скроллбары 6px */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_SUBTLE};
    min-height: 24px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {BORDER_HOVER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* Разделители */
QFrame#editorSeparator, QFrame[frameShape="4"] {{
    border: none;
    background-color: {BORDER_SUBTLE};
    height: 1px;
    max-height: 1px;
}}

/* Слоты-плейсхолдеры */
QFrame[placeholderBox="true"] {{
    background-color: {BG_PANEL};
    border: 1px dashed {BORDER_SUBTLE};
    border-radius: 8px;
}}

QLabel[placeholderLabel="true"] {{
    color: {TEXT_PLACEHOLDER};
    font-size: 13px;
    font-weight: 500;
}}

/* QComboBox (Dark Obsidian) */
QComboBox {{
    background-color: {BG_DROPDOWN};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    padding: 4px 10px 4px 10px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
    min-height: 24px;
}}

QComboBox:hover {{
    background-color: {BG_DROPDOWN_HOVER};
    border-color: {BORDER_HOVER};
}}

QComboBox:focus, QComboBox:on {{
    border-color: {BORDER_DROPDOWN_FOCUS};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
    background: transparent;
}}

QComboBox::down-arrow {{
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_SECONDARY};
    margin-right: 6px;
}}

QComboBox::down-arrow:hover {{
    border-top: 5px solid {TEXT_PRIMARY};
}}

/* QComboBox Popup List (Dark Obsidian QAbstractItemView) */
QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #27272a;
    selection-color: {BORDER_FOCUS_ACCENT};
    color: {TEXT_PRIMARY};
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 4px 10px;
    border-radius: 4px;
    color: {TEXT_PRIMARY};
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: #27272a;
    color: {BORDER_FOCUS_ACCENT};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #27272a;
    color: {BORDER_FOCUS_ACCENT};
}}

/* QPushButton.HeaderIconButton */
QPushButton[class="HeaderIconButton"],
QPushButton.HeaderIconButton,
HeaderIconButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 15px;
    min-width: {TOOL_BUTTON_SIZE}px;
    max-width: {TOOL_BUTTON_SIZE}px;
    min-height: {TOOL_BUTTON_SIZE}px;
    max-height: {TOOL_BUTTON_SIZE}px;
    padding: 0px;
}}

QPushButton[class="HeaderIconButton"]:hover,
QPushButton.HeaderIconButton:hover,
HeaderIconButton:hover {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
}}

QPushButton[class="HeaderIconButton"]:pressed,
QPushButton.HeaderIconButton:pressed,
HeaderIconButton:pressed {{
    background-color: {BG_DROPDOWN_HOVER};
    color: {BORDER_FOCUS_ACCENT};
}}

/* QToolTip */
QToolTip {{
    background-color: {TOOLTIP_BG};
    border: 1px solid {TOOLTIP_BORDER};
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    padding: 4px 8px;
    font-size: 11px;
}}

/* ToolbarVLine */
QFrame#toolbarVLine,
QFrame[toolbarVLine="true"],
QFrame.ToolbarVLine,
ToolbarVLine {{
    background-color: {BORDER_SUBTLE};
    width: 1px;
    max-width: 1px;
    height: 20px;
    max-height: 20px;
    border: none;
    margin: 0px 4px;
}}

/* ========================================================================== */
/* EditorGridCell (Холст: ячейки кнопок 96x96)                                */
/* ========================================================================== */
QFrame#editorGridCell,
QFrame[editorGridCell="true"],
EditorGridCell {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {GRID_CORNER_RADIUS}px;
}}

QFrame#editorGridCell:hover,
QFrame[editorGridCell="true"]:hover,
EditorGridCell:hover {{
    background-color: {BG_CELL_HOVER};
    border: 1px solid {BORDER_HOVER};
}}

QFrame#editorGridCell[selected="true"],
QFrame[editorGridCell="true"][selected="true"],
EditorGridCell[selected="true"] {{
    background-color: {BG_CARD};
    border: 2px solid {BORDER_FOCUS};
    border-radius: {GRID_CORNER_RADIUS}px;
}}

QFrame#editorGridCell[selected="true"]:hover,
QFrame[editorGridCell="true"][selected="true"]:hover,
EditorGridCell[selected="true"]:hover {{
    background-color: #26262c;
    border: 2px solid {BORDER_FOCUS_ACCENT};
}}

/* ========================================================================== */
/* EditorTouchbarStrip (Холст: интерактивный тачбар 3-го ряда 528x68)         */
/* ========================================================================== */
QFrame#editorTouchbarStrip,
QFrame[editorTouchbarStrip="true"],
EditorTouchbarStrip {{
    background-color: {BG_STRIP};
    border: 1px solid {BORDER_TOUCHBAR};
    border-radius: {TOUCHBAR_RADIUS}px;
}}

/* ========================================================================== */
/* TouchbarSectionWidget (Секции тачбара: медиа, часы, телеметрия)            */
/* ========================================================================== */
QFrame#touchbarSectionWidget,
QFrame[touchbarSection="true"],
TouchbarSectionWidget {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
}}

QFrame#touchbarSectionWidget:hover,
QFrame[touchbarSection="true"]:hover,
TouchbarSectionWidget:hover {{
    background-color: {BG_SECTION_HOVER_SUBTLE};
    border: 1px solid {BORDER_HOVER};
}}

QFrame#touchbarSectionWidget[selected="true"],
QFrame[touchbarSection="true"][selected="true"],
TouchbarSectionWidget[selected="true"] {{
    background-color: {BG_SECTION_HOVER};
    border: 2px solid {BORDER_FOCUS};
    border-radius: 10px;
}}

QFrame#touchbarSectionWidget[selected="true"]:hover,
QFrame[touchbarSection="true"][selected="true"]:hover,
TouchbarSectionWidget[selected="true"]:hover {{
    background-color: #242d42;
    border: 2px solid {BORDER_FOCUS_ACCENT};
}}

/* ========================================================================== */
/* PageNavigationBar: кнопки пагинации 28x28                                 */
/* ========================================================================== */
QPushButton[class="PageNavButton"],
QPushButton.PageNavButton,
PageNavButton {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
    min-width: {PAGE_NAV_BTN_SIZE}px;
    max-width: {PAGE_NAV_BTN_SIZE}px;
    min-height: {PAGE_NAV_BTN_SIZE}px;
    max-height: {PAGE_NAV_BTN_SIZE}px;
    padding: 0px;
}}

QPushButton[class="PageNavButton"]:hover,
QPushButton.PageNavButton:hover,
PageNavButton:hover {{
    background-color: {BG_CARD};
    border-color: {BORDER_HOVER};
    color: {TEXT_PRIMARY};
}}

QPushButton[class="PageNavButton"][active="true"],
QPushButton.PageNavButton[active="true"],
PageNavButton[active="true"] {{
    background-color: {BORDER_FOCUS};
    border: 1px solid {BORDER_FOCUS};
    color: #ffffff;
}}

QPushButton[class="PageNavButton"][active="true"]:hover,
QPushButton.PageNavButton[active="true"]:hover,
PageNavButton[active="true"]:hover {{
    background-color: {BORDER_FOCUS_ACCENT};
    border-color: {BORDER_FOCUS_ACCENT};
    color: #ffffff;
}}

/* ==========================================================================
   Инспектор свойств (KeyPropertyInspector) и формы
   ========================================================================== */

QFrame#propertyInspector,
QFrame[class="KeyPropertyInspector"],
KeyPropertyInspector {{
    background-color: {BG_INSPECTOR};
    border: none;
}}

QLabel.InspectorPlaceholder,
QLabel[class="InspectorPlaceholder"],
InspectorPlaceholder {{
    color: {TEXT_PLACEHOLDER};
    font-size: 14px;
    qproperty-alignment: 'AlignCenter';
    background: transparent;
}}

QLabel.InspectorCategoryLabel,
QLabel[class="InspectorCategoryLabel"],
InspectorCategoryLabel {{
    color: {TEXT_HEADER_CATEGORY};
    font-size: 13px;
    font-weight: bold;
    background: transparent;
}}

QPushButton.InspectorDeleteButton,
QPushButton[class="InspectorDeleteButton"],
InspectorDeleteButton {{
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 14px;
    padding: 0px;
}}

QPushButton.InspectorDeleteButton:hover,
QPushButton[class="InspectorDeleteButton"]:hover,
InspectorDeleteButton:hover {{
    background-color: {BG_CARD};
    color: {BTN_DELETE_HOVER};
}}

QPushButton.InspectorDeleteButton:pressed,
QPushButton[class="InspectorDeleteButton"]:pressed,
InspectorDeleteButton:pressed {{
    background-color: #3b1d1d;
    color: #f87171;
}}

/* Плитка превью иконки (KeyPreviewTile) */
QFrame.KeyPreviewTile,
QFrame[class="KeyPreviewTile"],
KeyPreviewTile {{
    background-color: {BG_PREVIEW_TILE};
    border: 1px solid {BORDER_PREVIEW_TILE};
    border-radius: 10px;
    min-width: {PREVIEW_TILE_SIZE}px;
    max-width: {PREVIEW_TILE_SIZE}px;
    min-height: {PREVIEW_TILE_SIZE}px;
    max-height: {PREVIEW_TILE_SIZE}px;
}}

QFrame.KeyPreviewTile:hover,
QFrame[class="KeyPreviewTile"]:hover,
KeyPreviewTile:hover {{
    border: 1px solid {BORDER_PREVIEW_HOVER};
}}

/* Угловые микро-кнопки плитки превью (18x18 px) */
QPushButton.TileCornerButton,
QPushButton[class="TileCornerButton"],
TileCornerButton {{
    min-width: {ICON_BTN_SIZE}px;
    max-width: {ICON_BTN_SIZE}px;
    min-height: {ICON_BTN_SIZE}px;
    max-height: {ICON_BTN_SIZE}px;
    background-color: {BORDER_PREVIEW_TILE};
    border: 1px solid {BORDER_PREVIEW_HOVER};
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    font-size: 10px;
    font-weight: bold;
    padding: 0px;
}}

QPushButton.TileCornerButton:hover,
QPushButton[class="TileCornerButton"]:hover,
TileCornerButton:hover {{
    background-color: {BORDER_PREVIEW_HOVER};
    border-color: {BORDER_FOCUS_ACCENT};
    color: #ffffff;
}}

QPushButton.TileCornerButton:pressed,
QPushButton[class="TileCornerButton"]:pressed,
TileCornerButton:pressed {{
    background-color: #4b5563;
    color: {BORDER_FOCUS_ACCENT};
}}

/* Поля ввода инспектора */
QLineEdit.InspectorLineEdit,
QLineEdit[class="InspectorLineEdit"],
InspectorLineEdit {{
    min-height: {INPUT_HEIGHT}px;
    max-height: {INPUT_HEIGHT}px;
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 0 8px;
}}

QLineEdit.InspectorLineEdit:hover,
QLineEdit[class="InspectorLineEdit"]:hover,
InspectorLineEdit:hover {{
    border-color: {BORDER_HOVER};
}}

QLineEdit.InspectorLineEdit:focus,
QLineEdit[class="InspectorLineEdit"]:focus,
InspectorLineEdit:focus {{
    border-color: {BORDER_FOCUS};
}}

/* Кнопка настроек шрифта */
QPushButton.FontSettingButton,
QPushButton[class="FontSettingButton"],
FontSettingButton {{
    min-width: {INPUT_HEIGHT}px;
    max-width: {INPUT_HEIGHT}px;
    min-height: {INPUT_HEIGHT}px;
    max-height: {INPUT_HEIGHT}px;
    background-color: {BG_CARD};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: bold;
    padding: 0px;
}}

QPushButton.FontSettingButton:hover,
QPushButton[class="FontSettingButton"]:hover,
FontSettingButton:hover {{
    background-color: {BG_DROPDOWN_HOVER};
    border-color: {BORDER_HOVER};
    color: {TEXT_PRIMARY};
}}

/* Кнопка захвата хоткея (HotkeyCaptureButton) */
QPushButton.HotkeyCaptureButton,
QPushButton[class="HotkeyCaptureButton"],
HotkeyCaptureButton {{
    min-height: {INPUT_HEIGHT}px;
    max-height: {INPUT_HEIGHT}px;
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    padding: 0 10px;
    text-align: left;
}}

QPushButton.HotkeyCaptureButton:hover,
QPushButton[class="HotkeyCaptureButton"]:hover,
HotkeyCaptureButton:hover {{
    border-color: {BORDER_HOVER};
    background-color: #1e1e24;
}}

QPushButton.HotkeyCaptureButton[capturing="true"],
QPushButton[class="HotkeyCaptureButton"][capturing="true"],
HotkeyCaptureButton[capturing="true"] {{
    border: 2px solid {HOTKEY_CAPTURING_BORDER};
    color: {HOTKEY_CAPTURING_BORDER};
    background-color: {BG_STRIP_SECTION_HOVER};
    font-weight: bold;
}}

/* Метки полей форм инспектора */
QLabel.InspectorFieldLabel,
QLabel[class="InspectorFieldLabel"],
InspectorFieldLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}}

/* Кнопка сброса настроек секции тачбара */
QPushButton.InspectorResetButton,
QPushButton[class="InspectorResetButton"],
InspectorResetButton {{
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 15px;
    padding: 0px;
}}

QPushButton.InspectorResetButton:hover,
QPushButton[class="InspectorResetButton"]:hover,
InspectorResetButton:hover {{
    background-color: {BG_CARD};
    color: {BORDER_FOCUS_ACCENT};
}}

QPushButton.InspectorResetButton:pressed,
QPushButton[class="InspectorResetButton"]:pressed,
InspectorResetButton:pressed {{
    background-color: {BG_DROPDOWN_HOVER};
    color: #ffffff;
}}

/* Стилизация чекбоксов форм (Dark Obsidian QCheckBox) */
QCheckBox {{
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 500;
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 4px;
    background-color: {BG_PANEL};
}}

QCheckBox::indicator:hover {{
    border-color: {BORDER_HOVER};
    background-color: {BG_CARD};
}}

QCheckBox::indicator:checked {{
    background-color: {BORDER_FOCUS};
    border-color: {BORDER_FOCUS};
}}

QCheckBox::indicator:checked:hover {{
    background-color: {BORDER_FOCUS_ACCENT};
    border-color: {BORDER_FOCUS_ACCENT};
}}

/* Стилизация слайдеров (Dark Obsidian QSlider) */
QSlider::groove:horizontal {{
    background: {BORDER_SUBTLE};
    height: 4px;
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {BORDER_FOCUS};
    height: 4px;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {TEXT_PRIMARY};
    border: 1px solid {BORDER_HOVER};
    width: 14px;
    height: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {BORDER_FOCUS_ACCENT};
    border-color: {BORDER_FOCUS};
}}

/* ==============================================================================
   Библиотека действий (Action Library Drawer) и поиск
   ============================================================================== */

/* Поле поиска каталога действий (ActionSearchInput) */
QLineEdit.ActionSearchInput,
QLineEdit[class="ActionSearchInput"],
ActionSearchInput {{
    background-color: {BG_SEARCH_INPUT};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    padding: 0px 28px 0px 30px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
    min-height: 28px;
    selection-background-color: {BORDER_FOCUS};
    selection-color: #ffffff;
}}

QLineEdit.ActionSearchInput:hover,
QLineEdit[class="ActionSearchInput"]:hover,
ActionSearchInput:hover {{
    border-color: {BORDER_HOVER};
}}

QLineEdit.ActionSearchInput:focus,
QLineEdit[class="ActionSearchInput"]:focus,
ActionSearchInput:focus {{
    border-color: {BORDER_FOCUS};
    background-color: {BG_WINDOW};
}}

/* Микро-кнопка быстрой очистки поиска (SearchClearButton) */
QPushButton.SearchClearButton,
QPushButton[class="SearchClearButton"],
SearchClearButton {{
    min-width: 18px;
    max-width: 18px;
    min-height: 18px;
    max-height: 18px;
    background-color: transparent;
    border: none;
    border-radius: 9px;
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: bold;
    padding: 0px;
}}

QPushButton.SearchClearButton:hover,
QPushButton[class="SearchClearButton"]:hover,
SearchClearButton:hover {{
    background-color: {BORDER_SUBTLE};
    color: {TEXT_PRIMARY};
}}

QPushButton.SearchClearButton:pressed,
QPushButton[class="SearchClearButton"]:pressed,
SearchClearButton:pressed {{
    background-color: {BORDER_HOVER};
    color: #ffffff;
}}

/* Служебная кнопка опций отображения (ActionViewButton) */
QPushButton.ActionViewButton,
QPushButton[class="ActionViewButton"],
ActionViewButton {{
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    background-color: {BG_SEARCH_INPUT};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 15px;
    font-weight: bold;
    padding: 0px;
}}

QPushButton.ActionViewButton:hover,
QPushButton[class="ActionViewButton"]:hover,
ActionViewButton:hover {{
    background-color: {BG_CARD};
    border-color: {BORDER_HOVER};
    color: {TEXT_PRIMARY};
}}

QPushButton.ActionViewButton:pressed,
QPushButton[class="ActionViewButton"]:pressed,
ActionViewButton:pressed {{
    background-color: {BG_DROPDOWN_HOVER};
    color: #ffffff;
}}

/* Заголовок категории аккордеона (ActionCategoryHeader) */
QFrame.ActionCategoryHeader,
QFrame[class="ActionCategoryHeader"],
ActionCategoryHeader {{
    background-color: {BG_SEARCH_INPUT};
    border: none;
    border-bottom: 1px solid {BG_CARD};
    min-height: 38px;
    max-height: 38px;
}}

QFrame.ActionCategoryHeader:hover,
QFrame[class="ActionCategoryHeader"]:hover,
ActionCategoryHeader:hover {{
    background-color: {BG_CARD};
}}

/* Шеврон и заголовок категории */
QLabel.CategoryChevron,
QLabel[class="CategoryChevron"],
CategoryChevron {{
    color: {CHEVRON_COLOR};
    font-size: 13px;
    font-weight: bold;
    background: transparent;
}}

QLabel.CategoryTitle,
QLabel[class="CategoryTitle"],
CategoryTitle {{
    color: {TEXT_CATEGORY_TITLE};
    font-size: 13px;
    font-weight: bold;
    background: transparent;
}}

/* Карточка действия (ActionItemCard) */
QFrame.ActionItemCard,
QFrame[class="ActionItemCard"],
ActionItemCard {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    min-height: 36px;
    max-height: 36px;
}}

QFrame.ActionItemCard:hover,
QFrame[class="ActionItemCard"]:hover,
ActionItemCard:hover {{
    background-color: {BG_ACTION_ITEM_HOVER};
}}

QFrame.ActionItemCard:pressed,
QFrame[class="ActionItemCard"]:pressed,
ActionItemCard:pressed,
QFrame.ActionItemCard[active="true"] {{
    background-color: {BG_ACTION_ITEM_ACTIVE};
}}

/* Подложка иконки действия */
QFrame.ActionItemIconBox,
QFrame[class="ActionItemIconBox"],
ActionItemIconBox {{
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    background-color: {BG_CARD};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 4px;
}}

/* Название действия */
QLabel.ActionItemTitle,
QLabel[class="ActionItemTitle"],
ActionItemTitle {{
    color: #d4d4d8;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}}

QFrame.ActionItemCard:hover QLabel.ActionItemTitle {{
    color: {TEXT_PRIMARY};
}}

/* Плейсхолдер пустого поиска (SearchEmptyPlaceholder) */
QLabel.SearchEmptyPlaceholder,
QLabel[class="SearchEmptyPlaceholder"],
SearchEmptyPlaceholder {{
    color: {TEXT_MUTED};
    font-size: 13px;
    font-weight: 500;
    background: transparent;
    padding-top: 30px;
}}
"""


class ToolbarVLine(QFrame):
    """
    Вертикальный микро-разделитель тулбара (1px x 20px, #2e2e36).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbarVLine")
        self.setProperty("toolbarVLine", "true")
        self.setFixedWidth(1)
        self.setFixedHeight(20)
        self.setStyleSheet(f"background-color: {BORDER_SUBTLE}; border: none;")


def apply_immersive_dark_titlebar(window: Any) -> bool:
    """
    Применяет Win32 DWMWA_USE_IMMERSIVE_DARK_MODE к окну для нативного темного заголовка.
    Изолирован от сбоев платформы и безопасен для запуска на Linux/CI и в тестах.
    """
    if sys.platform != "win32":
        return False
    try:
        if not hasattr(window, "winId"):
            return False
        hwnd = int(window.winId())
        if not hwnd:
            return False

        # DWMWA_USE_IMMERSIVE_DARK_MODE:
        # 20 для Windows 11 и Windows 10 20H1+
        # 19 для Windows 10 1809 - 1909
        dwmwa_use_immersive_dark_mode = 20
        dwmwa_use_immersive_dark_mode_before_20h1 = 19

        value = ctypes.c_int(1)
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(dwmwa_use_immersive_dark_mode),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        if res != 0:
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(dwmwa_use_immersive_dark_mode_before_20h1),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
        return res == 0
    except (OSError, AttributeError, Exception):
        return False


def apply_editor_theme(window: Any) -> None:
    """
    Фасад применения темы Dark Obsidian к окну:
    - Задает темный заголовок Win32 (DWM);
    - Применяет таблицу стилей EDITOR_MAIN_QSS.
    """
    apply_immersive_dark_titlebar(window)
    if hasattr(window, "setStyleSheet"):
        window.setStyleSheet(EDITOR_MAIN_QSS)
