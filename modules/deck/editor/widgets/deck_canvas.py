"""
Интерактивный холст DuckDeck Editor (DeckCanvasWidget).
Содержит:
  - Сетку кнопок 2x5 (слоты 0..4 - ряд 0, слоты 5..9 - ряд 1, размер ячеек 96x96 px, gap 12 px).
  - Полосу тачбара 3-го ряда EditorTouchbarStrip (ряд 2, colspan=5, 528x68 px).
  - Single Source of Truth для выделения (взаимное исключение между 10 кнопками и 3 секциями тачбара).
  - Обработку клика по нейтральному фону холста и клавиши Escape для сброса выделения (clear_selection).
  - Каскадный retranslate_ui() с вызовом self.touchbar_strip.retranslate_ui().
  - Сигналы selection_changed(str target_type, object target_id) и selection_cleared().
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple, cast

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from modules.deck.editor.styles import (
    CANVAS_SLOT_MIN_HEIGHT,
    GRID_CELL_SIZE,
    GRID_SPACING,
    TOUCHBAR_HEIGHT,
    TOUCHBAR_WIDTH,
)
from modules.deck.editor.widgets.grid_cell import EditorGridCell
from modules.deck.editor.widgets.touchbar_strip import EditorTouchbarStrip

logger = logging.getLogger(__name__)


class DeckCanvasWidget(QWidget):
    """
    Интерактивный холст компоновки кнопок и тачбара DuckDeck.
    - 10 ячеек EditorGridCell (ряды 0 и 1 по 5 колонок, 96x96 px).
    - 1 полоса EditorTouchbarStrip (ряд 2, colspan=5, 528x68 px).
    - Single Source of Truth для выделения.
    - Сброс выделения при клике в пустоту и Esc.
    """

    selection_changed = Signal(str, object)
    selection_cleared = Signal()
    action_dropped = Signal(int, dict)
    slot_dropped = Signal(int, int, bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._selected_target: Optional[Tuple[str, Any]] = None
        self._current_page: int = 1
        self.cells: List[EditorGridCell] = []

        self.setObjectName("deckCanvasWidget")
        self.setProperty("deckCanvasWidget", "true")
        self.setMinimumHeight(CANVAS_SLOT_MIN_HEIGHT)
        self.setFocusPolicy(Qt.StrongFocus)

        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignCenter)

        # Аккуратная подпись текущей страницы над сеткой (Рис. 2, 528 px, фиксированная высота)
        self.page_title_label = QLabel(self)
        self.page_title_label.setObjectName("canvasPageTitleLabel")
        self.page_title_label.setAlignment(Qt.AlignCenter)
        self.page_title_label.setFixedHeight(24)
        self.page_title_label.setFixedWidth(TOUCHBAR_WIDTH)
        self.page_title_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.page_title_label.setVisible(True)
        root_layout.addWidget(self.page_title_label, alignment=Qt.AlignCenter)

        # Контейнер сетки фиксированного размера для идеального центрирования
        # 5 колонок * 96px + 4 промежутка * 12px = 528px
        # 2 ряда * 96px + 2 промежутка * 12px + 68px = 284px
        grid_height = 2 * GRID_CELL_SIZE + 2 * GRID_SPACING + TOUCHBAR_HEIGHT
        self.grid_container = QWidget(self)
        self.grid_container.setObjectName("canvasGridContainer")
        self.grid_container.setFixedSize(TOUCHBAR_WIDTH, grid_height)
        self.grid_container.installEventFilter(self)

        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(GRID_SPACING)

        # Ряд 0: слоты 0..4
        for col in range(5):
            slot_idx = col
            cell = EditorGridCell(slot_index=slot_idx, parent=self.grid_container)
            cell.cell_clicked.connect(self.select_button)
            cell.action_dropped.connect(self.action_dropped.emit)
            cell.slot_dropped.connect(self.slot_dropped.emit)
            self.grid_layout.addWidget(cell, 0, col)
            self.cells.append(cell)

        # Ряд 1: слоты 5..9
        for col in range(5):
            slot_idx = 5 + col
            cell = EditorGridCell(slot_index=slot_idx, parent=self.grid_container)
            cell.cell_clicked.connect(self.select_button)
            cell.action_dropped.connect(self.action_dropped.emit)
            cell.slot_dropped.connect(self.slot_dropped.emit)
            self.grid_layout.addWidget(cell, 1, col)
            self.cells.append(cell)

        # Ряд 2: полоса тачбара (colspan=5)
        self.touchbar_strip = EditorTouchbarStrip(parent=self.grid_container)
        self.touchbar_strip.section_selected.connect(self.select_touchbar_section)
        self.grid_layout.addWidget(self.touchbar_strip, 2, 0, 1, 5)

        root_layout.addWidget(self.grid_container, alignment=Qt.AlignCenter)

    def select_button(self, slot_index: int) -> None:
        """
        Выделяет указанную ячейку кнопки (0..9) и снимает выделение с остальных кнопок и тачбара.
        Эмитирует сигнал selection_changed("button", slot_index).
        """
        self._selected_target = ("button", slot_index)
        for cell in self.cells:
            cell.set_selected(cell.slot_index == slot_index)
        self.touchbar_strip.clear_selection()
        self.selection_changed.emit("button", slot_index)

    def select_touchbar_section(self, section_type: str) -> None:
        """
        Выделяет указанную секцию тачбара ('media' | 'clock' | 'telemetry')
        и снимает выделение со всех 10 кнопок и остальных секций.
        Эмитирует сигнал selection_changed("touchbar", section_type).
        """
        self._selected_target = ("touchbar", section_type)
        for cell in self.cells:
            cell.set_selected(False)
        self.touchbar_strip.select_section(section_type)
        self.selection_changed.emit("touchbar", section_type)

    def clear_selection(self) -> None:
        """
        Снимает выделение со всех 10 кнопок и полосы тачбара.
        Эмитирует сигнал selection_cleared().
        """
        had_selection = (
            self._selected_target is not None
            or any(c.is_selected() for c in self.cells)
            or self.touchbar_strip.get_selected_section() is not None
        )

        self._selected_target = None
        for cell in self.cells:
            cell.set_selected(False)
        self.touchbar_strip.clear_selection()

        if had_selection:
            self.selection_cleared.emit()

    def get_selected_target(self) -> Optional[Tuple[str, Any]]:
        """
        Возвращает текущую выделенную цель в виде ("button", slot_index) или ("touchbar", section_type),
        либо None, если выделение отсутствует.
        """
        return self._selected_target

    def get_cell(self, slot_index: int) -> Optional[EditorGridCell]:
        """Возвращает объект ячейки по ее индексу слота (0..9)."""
        if 0 <= slot_index < len(self.cells):
            return self.cells[slot_index]
        return None

    def update_cell_preview(self, slot_index: int, prop: str, val: Any) -> None:
        """
        Точечно обновляет отображение ячейки холста по имени свойства без циклической эмиссии.
        """
        cell = self.get_cell(slot_index)
        if cell is None:
            return
        data = cell.get_button_data()
        if prop == "title":
            data["title"] = str(val) if val is not None else ""
        elif prop == "icon":
            data["icon"] = str(val) if val is not None else ""
        elif prop == "category":
            data["category"] = str(val) if val is not None else ""
        elif prop == "hotkey":
            data["hotkey"] = str(val) if val is not None else ""
        elif prop == "status_source":
            data["status_source"] = str(val) if val is not None else "none"
        elif prop == "font_size":
            data["font_size"] = int(val) if val is not None else 11
        elif prop == "font_color":
            data["font_color"] = str(val) if val is not None else "#d4d4d8"
        elif prop == "text_alignment":
            data["text_alignment"] = str(val) if val is not None else "bottom"
        elif prop == "hide_title":
            data["hide_title"] = bool(val)
        elif prop == "color_accent":
            data["color_accent"] = str(val) if val is not None else "#38bdf8"
        cell.set_button_data(
            title=data.get("title", ""),
            icon=data.get("icon", ""),
            category=data.get("category", ""),
            hotkey=data.get("hotkey", ""),
            status_source=data.get("status_source", "none"),
            color_accent=data.get("color_accent", "#38bdf8"),
            font_size=data.get("font_size", 11),
            font_color=data.get("font_color", "#d4d4d8"),
            text_alignment=data.get("text_alignment", "bottom"),
            hide_title=data.get("hide_title", False),
        )

    def update_cell_icon(self, slot_index: int, icon_str: str) -> None:
        """Точечно обновляет иконку ячейки холста."""
        self.update_cell_preview(slot_index, "icon", icon_str)

    def clear_cell(self, slot_index: int) -> None:
        """
        Сбрасывает данные ячейки холста в исходное пустое состояние.
        """
        cell = self.get_cell(slot_index)
        if cell is not None:
            cell.clear_button_data()

    def set_page(self, page_index: int) -> None:
        """Смена активной страницы холста со сбросом выделения."""
        self._current_page = page_index
        self.clear_selection()

    def get_page(self) -> int:
        """Возвращает текущую активную страницу."""
        return self._current_page

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Перехват кликов в промежутках между ячейками grid_container для сброса выделения."""
        if watched is self.grid_container and event.type() == QEvent.MouseButtonPress:
            mouse_evt = cast(QMouseEvent, event)
            if mouse_evt.button() == Qt.LeftButton:
                pos = mouse_evt.position().toPoint() if hasattr(mouse_evt, "position") else mouse_evt.pos()
                child = self.grid_container.childAt(pos)
                if child is None or child is self.grid_container:
                    self.clear_selection()
                    return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Клик по нейтральной области холста сбрасывает выделение.
        """
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            child = self.childAt(pos)
            if child is None or child is self or child is self.grid_container:
                self.clear_selection()
                event.accept()
                return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Нажатие клавиши Escape сбрасывает выделение на холсте.
        """
        if event.key() == Qt.Key_Escape:
            self.clear_selection()
            event.accept()
            return
        super().keyPressEvent(event)

    def set_page_title(self, title: Optional[str]) -> None:
        """
        Устанавливает аккуратную подпись текущей страницы.
        Контейнер всегда сохраняет фиксированную геометрию, исключая сдвиг кнопок вверх.
        Видна только в редакторе.
        """
        clean_title = (title or "").strip()
        self.page_title_label.setText(clean_title)

    def get_page_title(self) -> str:
        """Возвращает текущую подпись страницы."""
        return self.page_title_label.text()

    def retranslate_ui(self) -> None:
        """
        Каскадно обновляет локализацию дочерних элементов (полоса тачбара).
        """
        self.touchbar_strip.retranslate_ui()
