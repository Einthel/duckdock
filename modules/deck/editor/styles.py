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
# Дизайн-токены Dark Obsidian v2 (4-уровневая система поверхностей и палитра Slate)
# ==============================================================================
SURFACE_0_CANVAS = "#0b0d13"       # Deep Canvas / Void
SURFACE_1_PANEL = "#0f141f"        # Panels, Drawer, Inspector base
SURFACE_2_CARD = "#141924"         # Cells, Preview Tile, Inputs base
SURFACE_3_HOVER = "#1c2940"        # Hover background & Active Selection

BORDER_SURFACE_1 = "#1e2638"       # Тонкая граница панелей
BORDER_SURFACE_2 = "#202a3c"       # Граница интерактивных ячеек
BORDER_FOCUS_NEON = "#38bdf8"      # Неоновый акцент выделения
BORDER_FOCUS_BASE = "#0078d4"      # Синий базовый фокус

TEXT_SLOT_INDEX = "#475569"        # Приглушенные индексы [0]..[9] (Slate 600)
TEXT_PRIMARY_HIGH = "#f8fafc"      # Основной текст (Slate 50)
TEXT_SECONDARY_MED = "#94a3b8"     # Вторичный текст (Slate 400)
TEXT_MUTED_SUBTLE = "#64748b"      # Подписи и плейсхолдеры (Slate 500)

# ==============================================================================
# Re-export Shims для 100% обратной совместимости (Dark Obsidian v1 -> v2)
# ==============================================================================
BG_WINDOW = SURFACE_0_CANVAS
BG_PANEL = SURFACE_1_PANEL
BG_CARD = SURFACE_2_CARD
BG_STRIP = SURFACE_1_PANEL
BG_CELL = SURFACE_2_CARD
BG_CELL_HOVER = SURFACE_3_HOVER
BG_STRIP_SECTION_HOVER = SURFACE_3_HOVER

BORDER_SUBTLE = BORDER_SURFACE_1
BORDER_CELL = BORDER_SURFACE_2
BORDER_FOCUS = BORDER_FOCUS_BASE
BORDER_FOCUS_ACCENT = BORDER_FOCUS_NEON
BORDER_SELECTED = BORDER_FOCUS_BASE
BORDER_SELECTED_GLOW = BORDER_FOCUS_NEON
BORDER_HOVER = "#2e3d5c"

TEXT_PRIMARY = TEXT_PRIMARY_HIGH
TEXT_SECONDARY = TEXT_SECONDARY_MED
TEXT_MUTED = TEXT_MUTED_SUBTLE
TEXT_PLACEHOLDER = TEXT_MUTED_SUBTLE

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

# Re-export Shims & фоны сетки / тачбара
BG_TOUCHBAR = SURFACE_1_PANEL
BG_SECTION_HOVER = SURFACE_3_HOVER
BG_SECTION_HOVER_SUBTLE = "#192338"

BORDER_CELL_HOVER = "#2e3d5c"
BORDER_TOUCHBAR = BORDER_SURFACE_1

# ==============================================================================
# Токены инспектора свойств и превью-плитки (Property Inspector & Tile Geometry)
# ==============================================================================
INSPECTOR_HEIGHT = 220
PREVIEW_TILE_SIZE = 84
INPUT_HEIGHT = 30
FORM_LABEL_WIDTH = 60
ICON_BTN_SIZE = 20

BG_INSPECTOR = SURFACE_1_PANEL
BG_PREVIEW_TILE = SURFACE_2_CARD
BORDER_PREVIEW_TILE = BORDER_SURFACE_2
BORDER_PREVIEW_HOVER = BORDER_HOVER
TEXT_HEADER_CATEGORY = TEXT_PRIMARY_HIGH
BTN_DELETE_HOVER = ACCENT_DANGER
HOTKEY_CAPTURING_BORDER = BORDER_FOCUS_NEON

# ==============================================================================
# Токены библиотеки действий и поиска (Action Library & Search Bar)
# ==============================================================================
SEARCH_BAR_HEIGHT = 36
ACTION_ITEM_HEIGHT = 36
CATEGORY_HEADER_HEIGHT = 38
DRAWER_PADDING = 8

BG_SEARCH_INPUT = SURFACE_2_CARD
BG_ACTION_ITEM_HOVER = SURFACE_3_HOVER
BG_ACTION_ITEM_ACTIVE = "#192338"
TEXT_CATEGORY_TITLE = TEXT_PRIMARY_HIGH
CHEVRON_COLOR = TEXT_MUTED_SUBTLE

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
    background-color: #101522;
    border: 1px solid {BORDER_SURFACE_1};
    border-radius: 6px;
    padding: 4px 10px 4px 10px;
    color: {TEXT_PRIMARY_HIGH};
    font-size: 13px;
    font-weight: 500;
    min-height: 24px;
}}

QComboBox:hover {{
    background-color: {SURFACE_2_CARD};
    border-color: {BORDER_HOVER};
}}

QComboBox:focus, QComboBox:on {{
    border: 1.5px solid {BORDER_FOCUS_NEON};
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
    border-top: 5px solid {TEXT_SECONDARY_MED};
    margin-right: 6px;
}}

QComboBox::down-arrow:hover {{
    border-top: 5px solid {TEXT_PRIMARY_HIGH};
}}

/* QComboBox Popup List (Dark Obsidian QAbstractItemView) */
QComboBox QAbstractItemView {{
    background-color: {SURFACE_1_PANEL};
    border: 1px solid {BORDER_SURFACE_1};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {SURFACE_3_HOVER};
    selection-color: {BORDER_FOCUS_NEON};
    color: {TEXT_PRIMARY_HIGH};
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 4px 10px;
    border-radius: 4px;
    color: {TEXT_PRIMARY_HIGH};
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {SURFACE_3_HOVER};
    color: {BORDER_FOCUS_NEON};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {SURFACE_3_HOVER};
    color: {BORDER_FOCUS_NEON};
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

/* QPushButton.HeaderSaveButton (Dark Obsidian v2 Save Button) */
QPushButton[class="HeaderSaveButton"],
QPushButton.HeaderSaveButton,
QPushButton#btnSaveConfig {{
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: {TEXT_PRIMARY_HIGH};
    font-size: 13px;
    font-weight: 600;
    padding: 4px 14px;
    min-height: 24px;
    height: 32px;
}}

QPushButton[class="HeaderSaveButton"]:hover,
QPushButton.HeaderSaveButton:hover,
QPushButton#btnSaveConfig:hover {{
    background-color: #334155;
    border: 1px solid {BORDER_FOCUS_NEON};
    color: #ffffff;
}}

QPushButton[class="HeaderSaveButton"]:pressed,
QPushButton.HeaderSaveButton:pressed,
QPushButton#btnSaveConfig:pressed {{
    background-color: #0f172a;
    border-color: #0284c7;
}}

QPushButton[class="HeaderSaveButton"][state="success"],
QPushButton.HeaderSaveButton[state="success"],
QPushButton#btnSaveConfig[state="success"] {{
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
}}

QPushButton[class="HeaderSaveButton"][state="success"]:hover,
QPushButton.HeaderSaveButton[state="success"]:hover,
QPushButton#btnSaveConfig[state="success"]:hover {{
    background-color: #10b981;
    border: 1px solid #34d399;
    color: #ffffff;
}}

/* ========================================================================== */
/* EditorGridCell (Холст: ячейки кнопок 96x96, Dark Obsidian v2)               */
/* ========================================================================== */
QFrame#editorGridCell,
QFrame[editorGridCell="true"],
EditorGridCell {{
    background-color: {SURFACE_2_CARD};
    border: 1px solid {BORDER_SURFACE_2};
    border-radius: {GRID_CORNER_RADIUS}px;
}}

QFrame#editorGridCell:hover,
QFrame[editorGridCell="true"]:hover,
EditorGridCell:hover {{
    background-color: {SURFACE_3_HOVER};
    border: 1px solid {BORDER_HOVER};
}}

QFrame#editorGridCell[selected="true"],
QFrame[editorGridCell="true"][selected="true"],
EditorGridCell[selected="true"] {{
    background-color: {SURFACE_2_CARD};
    border: 2px solid {BORDER_FOCUS_NEON};
    border-radius: {GRID_CORNER_RADIUS}px;
}}

QFrame#editorGridCell[selected="true"]:hover,
QFrame[editorGridCell="true"][selected="true"]:hover,
EditorGridCell[selected="true"]:hover {{
    background-color: {SURFACE_3_HOVER};
    border: 2px solid {BORDER_FOCUS_NEON};
}}

/* Лейблы ячейки сетки кнопок (CellIndexLabel, CellIconLabel, CellTitleLabel) */
QLabel.CellIndexLabel,
QLabel[class="CellIndexLabel"],
QLabel#lblCellIndex {{
    color: {TEXT_SLOT_INDEX};
    font-size: 10px;
    font-weight: 600;
    background: transparent;
    border: none;
}}

QLabel.CellIconLabel,
QLabel[class="CellIconLabel"],
QLabel#lblCellIcon {{
    color: {TEXT_PRIMARY_HIGH};
    font-size: 26px;
    background: transparent;
    border: none;
}}

QLabel.CellTitleLabel,
QLabel[class="CellTitleLabel"],
QLabel#lblCellTitle {{
    color: {TEXT_SECONDARY_MED};
    font-size: 11px;
    font-weight: 500;
    background: transparent;
    border: none;
}}

QFrame#editorGridCell:hover QLabel.CellTitleLabel,
QFrame[editorGridCell="true"]:hover QLabel.CellTitleLabel,
EditorGridCell:hover QLabel.CellTitleLabel,
QFrame#editorGridCell:hover QLabel[class="CellTitleLabel"],
QFrame[editorGridCell="true"]:hover QLabel[class="CellTitleLabel"],
EditorGridCell:hover QLabel[class="CellTitleLabel"] {{
    color: {TEXT_PRIMARY_HIGH};
}}

/* ========================================================================== */
/* EditorTouchbarStrip (Холст: интерактивный тачбар 3-го ряда 528x68)         */
/* ========================================================================== */
QFrame#editorTouchbarStrip,
QFrame[editorTouchbarStrip="true"],
EditorTouchbarStrip {{
    background-color: {SURFACE_1_PANEL};
    border: 1px solid {BORDER_SURFACE_1};
    border-radius: {TOUCHBAR_RADIUS}px;
}}

/* Вертикальный микро-разделитель 1px между секциями тачбара */
QFrame#touchbarDivider,
QFrame.TouchbarDivider,
QFrame[class="TouchbarDivider"] {{
    background-color: {BORDER_SURFACE_1};
    border: none;
    width: 1px;
    max-width: 1px;
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
    background-color: {SURFACE_3_HOVER};
    border: 1px solid {BORDER_HOVER};
}}

QFrame#touchbarSectionWidget[selected="true"],
QFrame[touchbarSection="true"][selected="true"],
TouchbarSectionWidget[selected="true"] {{
    background-color: #192338;
    border: 2px solid {BORDER_FOCUS_NEON};
    border-radius: 10px;
}}

QFrame#touchbarSectionWidget[selected="true"]:hover,
QFrame[touchbarSection="true"][selected="true"]:hover,
TouchbarSectionWidget[selected="true"]:hover {{
    background-color: {SURFACE_3_HOVER};
    border: 2px solid {BORDER_FOCUS_NEON};
}}

/* Элементы и текстовые метки секций тачбара */
QLabel.TouchbarMediaIcon,
QLabel[class="TouchbarMediaIcon"],
QLabel#lblTouchbarMediaIcon {{
    color: {BORDER_FOCUS_NEON};
    font-size: 18px;
    background: transparent;
    border: none;
}}

QLabel.TouchbarMediaTrack,
QLabel[class="TouchbarMediaTrack"],
QLabel#lblTouchbarMediaTrack {{
    color: {TEXT_PRIMARY_HIGH};
    font-size: 11px;
    font-weight: 600;
    background: transparent;
    border: none;
}}

QLabel.TouchbarMediaArtist,
QLabel[class="TouchbarMediaArtist"],
QLabel#lblTouchbarMediaArtist {{
    color: {TEXT_MUTED_SUBTLE};
    font-size: 9px;
    background: transparent;
    border: none;
}}

QLabel.TouchbarMediaControls,
QLabel[class="TouchbarMediaControls"],
QLabel#lblTouchbarMediaControls {{
    color: {TEXT_SECONDARY_MED};
    font-size: 12px;
    background: transparent;
    border: none;
}}

QLabel.TouchbarClockTime,
QLabel[class="TouchbarClockTime"],
QLabel#lblTouchbarClockTime {{
    color: {BORDER_FOCUS_NEON};
    font-size: 16px;
    font-weight: 700;
    background: transparent;
    border: none;
}}

QLabel.TouchbarClockDots,
QLabel[class="TouchbarClockDots"],
QLabel#lblTouchbarClockDots {{
    color: {TEXT_MUTED_SUBTLE};
    font-size: 9px;
    background: transparent;
    border: none;
}}

QLabel.TouchbarTelemetrySensor,
QLabel[class="TouchbarTelemetrySensor"],
QLabel#lblTouchbarCpu,
QLabel#lblTouchbarGpu {{
    color: #10b981;
    font-size: 10px;
    font-weight: 600;
    background: transparent;
    border: none;
}}

QLabel.TouchbarTelemetryGear,
QLabel[class="TouchbarTelemetryGear"],
QLabel#lblTouchbarGear {{
    color: {TEXT_SECONDARY_MED};
    font-size: 14px;
    background: transparent;
    border: none;
}}

QLabel.TouchbarFallbackLabel,
QLabel[class="TouchbarFallbackLabel"],
QLabel#lblTouchbarFallback {{
    color: {TEXT_SECONDARY_MED};
    font-size: 11px;
    background: transparent;
    border: none;
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
    background-color: {SURFACE_1_PANEL};
    border: none;
}}

/* Разделители форм инспектора и панелей */
QFrame#formSeparator,
QFrame#touchbarFormSeparator,
QFrame.FormSeparator,
QFrame#drawerInternalSeparator,
QFrame.DrawerInternalSeparator {{
    background-color: {BORDER_SURFACE_1};
    border: none;
    height: 1px;
    max-height: 1px;
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
    color: {TEXT_PRIMARY_HIGH};
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
    color: {TEXT_MUTED_SUBTLE};
    font-size: 14px;
    padding: 0px;
}}

QPushButton.InspectorDeleteButton:hover,
QPushButton[class="InspectorDeleteButton"]:hover,
InspectorDeleteButton:hover {{
    background-color: #2a171b;
    color: {ACCENT_DANGER};
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
    background-color: {SURFACE_2_CARD};
    border: 1px solid {BORDER_SURFACE_2};
    border-radius: 10px;
    min-width: {PREVIEW_TILE_SIZE}px;
    max-width: {PREVIEW_TILE_SIZE}px;
    min-height: {PREVIEW_TILE_SIZE}px;
    max-height: {PREVIEW_TILE_SIZE}px;
}}

QFrame.KeyPreviewTile:hover,
QFrame[class="KeyPreviewTile"]:hover,
KeyPreviewTile:hover {{
    border: 1px solid {BORDER_HOVER};
}}

/* Угловые микро-кнопки плитки превью (20x20 px) */
QPushButton.TileCornerButton,
QPushButton[class="TileCornerButton"],
TileCornerButton {{
    min-width: {ICON_BTN_SIZE}px;
    max-width: {ICON_BTN_SIZE}px;
    min-height: {ICON_BTN_SIZE}px;
    max-height: {ICON_BTN_SIZE}px;
    background-color: {SURFACE_3_HOVER};
    border: 1px solid {BORDER_HOVER};
    border-radius: 5px;
    color: {TEXT_SECONDARY_MED};
    font-size: 11px;
    font-weight: bold;
    padding: 0px;
}}

QPushButton.TileCornerButton:hover,
QPushButton[class="TileCornerButton"]:hover,
TileCornerButton:hover {{
    background-color: {SURFACE_3_HOVER};
    border: 1px solid {BORDER_FOCUS_NEON};
    color: #ffffff;
}}

QPushButton.TileCornerButton:pressed,
QPushButton[class="TileCornerButton"]:pressed,
TileCornerButton:pressed {{
    background-color: #2e3d5c;
    border: 1px solid {BORDER_FOCUS_NEON};
    color: {BORDER_FOCUS_NEON};
}}

/* Поля ввода инспектора */
QLineEdit.InspectorLineEdit,
QLineEdit[class="InspectorLineEdit"],
InspectorLineEdit {{
    min-height: {INPUT_HEIGHT}px;
    max-height: {INPUT_HEIGHT}px;
    background-color: #101522;
    border: 1px solid {BORDER_SURFACE_1};
    border-radius: 6px;
    color: {TEXT_PRIMARY_HIGH};
    font-size: 13px;
    padding: 0 8px;
    selection-background-color: {BORDER_FOCUS_BASE};
    selection-color: #ffffff;
}}

QLineEdit.InspectorLineEdit:hover,
QLineEdit[class="InspectorLineEdit"]:hover,
InspectorLineEdit:hover {{
    border-color: {BORDER_HOVER};
}}

QLineEdit.InspectorLineEdit:focus,
QLineEdit[class="InspectorLineEdit"]:focus,
InspectorLineEdit:focus {{
    border: 1.5px solid {BORDER_FOCUS_NEON};
}}

/* Кнопка настроек шрифта */
QPushButton.FontSettingButton,
QPushButton[class="FontSettingButton"],
FontSettingButton {{
    min-width: {INPUT_HEIGHT}px;
    max-width: {INPUT_HEIGHT}px;
    min-height: {INPUT_HEIGHT}px;
    max-height: {INPUT_HEIGHT}px;
    background-color: {SURFACE_2_CARD};
    border: 1px solid {BORDER_SURFACE_1};
    border-radius: 6px;
    color: {TEXT_SECONDARY_MED};
    font-size: 12px;
    font-weight: bold;
    padding: 0px;
}}

QPushButton.FontSettingButton:hover,
QPushButton[class="FontSettingButton"]:hover,
FontSettingButton:hover {{
    background-color: {SURFACE_3_HOVER};
    border-color: {BORDER_HOVER};
    color: {TEXT_PRIMARY_HIGH};
}}

/* Кнопка захвата хоткея (HotkeyCaptureButton) */
QPushButton.HotkeyCaptureButton,
QPushButton[class="HotkeyCaptureButton"],
HotkeyCaptureButton {{
    min-height: {INPUT_HEIGHT}px;
    max-height: {INPUT_HEIGHT}px;
    background-color: #101522;
    border: 1px solid {BORDER_SURFACE_1};
    border-radius: 6px;
    color: {TEXT_PRIMARY_HIGH};
    font-size: 12px;
    padding: 0 10px;
    text-align: left;
}}

QPushButton.HotkeyCaptureButton:hover,
QPushButton[class="HotkeyCaptureButton"]:hover,
HotkeyCaptureButton:hover {{
    border-color: {BORDER_HOVER};
    background-color: {SURFACE_2_CARD};
}}

QPushButton.HotkeyCaptureButton:focus,
QPushButton[class="HotkeyCaptureButton"]:focus,
HotkeyCaptureButton:focus {{
    border: 1.5px solid {BORDER_FOCUS_NEON};
}}

QPushButton.HotkeyCaptureButton[capturing="true"],
QPushButton[class="HotkeyCaptureButton"][capturing="true"],
HotkeyCaptureButton[capturing="true"] {{
    border: 1.5px solid {BORDER_FOCUS_NEON};
    color: {BORDER_FOCUS_NEON};
    background-color: {SURFACE_3_HOVER};
    font-weight: bold;
}}

/* Метки полей форм инспектора */
QLabel.InspectorFieldLabel,
QLabel[class="InspectorFieldLabel"],
InspectorFieldLabel {{
    color: {TEXT_SECONDARY_MED};
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

QWidget#actionLibraryDrawer,
QWidget[class="ActionLibraryDrawer"],
ActionLibraryDrawer {{
    background-color: {SURFACE_1_PANEL};
}}

QFrame#actionSearchBar,
ActionSearchBar {{
    background-color: transparent;
    border: none;
}}

/* Поле поиска каталога действий (ActionSearchInput) */
QLineEdit.ActionSearchInput,
QLineEdit[class="ActionSearchInput"],
ActionSearchInput {{
    background-color: {SURFACE_2_CARD};
    border: 1px solid {BORDER_SURFACE_2};
    border-radius: 6px;
    padding: 0px 28px 0px 30px;
    color: {TEXT_PRIMARY_HIGH};
    font-size: 13px;
    font-weight: 500;
    min-height: 28px;
    selection-background-color: {BORDER_FOCUS_BASE};
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
    border: 1.5px solid {BORDER_FOCUS_NEON};
    background-color: #101522;
}}

/* Иконка лупы в строке поиска */
QLabel.SearchIconLabel,
QLabel#searchIconLabel {{
    color: {TEXT_MUTED_SUBTLE};
    font-size: 13px;
    background: transparent;
    border: none;
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
    color: {TEXT_MUTED_SUBTLE};
    font-size: 11px;
    font-weight: bold;
    padding: 0px;
}}

QPushButton.SearchClearButton:hover,
QPushButton[class="SearchClearButton"]:hover,
SearchClearButton:hover {{
    background-color: {SURFACE_3_HOVER};
    color: {TEXT_PRIMARY_HIGH};
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
    background-color: {SURFACE_2_CARD};
    border: 1px solid {BORDER_SURFACE_2};
    border-radius: 6px;
    color: {TEXT_SECONDARY_MED};
    font-size: 15px;
    font-weight: bold;
    padding: 0px;
}}

QPushButton.ActionViewButton:hover,
QPushButton[class="ActionViewButton"]:hover,
ActionViewButton:hover {{
    background-color: {SURFACE_3_HOVER};
    border-color: {BORDER_HOVER};
    color: {TEXT_PRIMARY_HIGH};
}}

QPushButton.ActionViewButton:pressed,
QPushButton[class="ActionViewButton"]:pressed,
ActionViewButton:pressed {{
    background-color: #192338;
    border-color: {BORDER_FOCUS_NEON};
    color: {BORDER_FOCUS_NEON};
}}

/* Скроллируемый контейнер-аккордеон категорий */
QScrollArea#actionAccordionWidget,
ActionAccordionWidget {{
    background-color: transparent;
    border: none;
}}

QWidget#actionAccordionContent {{
    background-color: transparent;
}}

/* Секция категории действий */
QFrame.ActionCategorySection,
ActionCategorySection {{
    background: transparent;
    border: none;
}}

QWidget[objectName^="categoryBody_"] {{
    background: transparent;
}}

/* Заголовок категории аккордеона (ActionCategoryHeader) */
QFrame.ActionCategoryHeader,
QFrame[class="ActionCategoryHeader"],
ActionCategoryHeader {{
    background-color: {SURFACE_1_PANEL};
    border: none;
    border-bottom: 1px solid {BORDER_SURFACE_1};
    min-height: {CATEGORY_HEADER_HEIGHT}px;
    max-height: {CATEGORY_HEADER_HEIGHT}px;
}}

QFrame.ActionCategoryHeader:hover,
QFrame[class="ActionCategoryHeader"]:hover,
ActionCategoryHeader:hover {{
    background-color: {SURFACE_2_CARD};
}}

/* Шеврон и заголовок категории */
QLabel.CategoryChevron,
QLabel[class="CategoryChevron"],
CategoryChevron {{
    color: {TEXT_MUTED_SUBTLE};
    font-size: 13px;
    font-weight: bold;
    background: transparent;
}}

QLabel.CategoryChevron[expanded="true"],
QLabel[class="CategoryChevron"][expanded="true"],
CategoryChevron[expanded="true"],
QFrame.ActionCategoryHeader[expanded="true"] QLabel.CategoryChevron {{
    color: {BORDER_FOCUS_NEON};
}}

QLabel.CategoryTitle,
QLabel[class="CategoryTitle"],
CategoryTitle {{
    color: {TEXT_PRIMARY_HIGH};
    font-size: 13px;
    font-weight: bold;
    background: transparent;
}}

/* Карточка действия (ActionItemCard) */
QFrame.ActionItemCard,
QFrame[class="ActionItemCard"],
ActionItemCard {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    min-height: {ACTION_ITEM_HEIGHT}px;
    max-height: {ACTION_ITEM_HEIGHT}px;
}}

QFrame.ActionItemCard:hover,
QFrame[class="ActionItemCard"]:hover,
ActionItemCard:hover {{
    background-color: {SURFACE_3_HOVER};
    border: 1px solid {BORDER_HOVER};
}}

QFrame.ActionItemCard:pressed,
QFrame[class="ActionItemCard"]:pressed,
ActionItemCard:pressed,
QFrame.ActionItemCard[active="true"] {{
    background-color: #192338;
    border: 1px solid {BORDER_FOCUS_NEON};
}}

/* Подложка иконки действия */
QFrame.ActionItemIconBox,
QFrame[class="ActionItemIconBox"],
ActionItemIconBox {{
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    background-color: {SURFACE_2_CARD};
    border: 1px solid {BORDER_SURFACE_2};
    border-radius: 4px;
}}

QLabel.ActionItemIcon,
QLabel#actionItemIcon {{
    font-size: 13px;
    background: transparent;
    border: none;
}}

/* Название действия */
QLabel.ActionItemTitle,
QLabel[class="ActionItemTitle"],
ActionItemTitle {{
    color: {TEXT_SECONDARY_MED};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}}

QFrame.ActionItemCard:hover QLabel.ActionItemTitle,
QFrame[class="ActionItemCard"]:hover QLabel[class="ActionItemTitle"],
ActionItemCard:hover ActionItemTitle {{
    color: {TEXT_PRIMARY_HIGH};
}}

/* Плейсхолдер пустого поиска (SearchEmptyPlaceholder) */
QLabel.SearchEmptyPlaceholder,
QLabel[class="SearchEmptyPlaceholder"],
SearchEmptyPlaceholder {{
    color: {TEXT_MUTED_SUBTLE};
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
