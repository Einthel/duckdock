"""
Интерактивная ячейка кнопки холста DuckDeck Editor (EditorGridCell).
Отображает слот кнопки [0]..[9], превью иконки и заголовка,
поддерживает состояния ховера, синего фокуса (selected) и сигнал клика.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from PySide6.QtCore import QPoint, Qt, Signal, QMimeData
from PySide6.QtGui import (
    QDrag,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QFontMetrics,
    QMouseEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from modules.deck.editor.styles import GRID_CELL_SIZE

logger = logging.getLogger(__name__)


class EditorGridCell(QFrame):
    """
    Интерактивная ячейка холста DuckDeck (96x96 px).
    - Метка индекса [0]..[9] в верхнем левом углу (.CellIndexLabel, 10px, TEXT_SLOT_INDEX).
    - Центральная иконка (.CellIconLabel, 26px, центрированная).
    - Нижний заголовок (.CellTitleLabel, 11px, центрированный, с эллипсисом).
    - Эксклюзивное выделение неоновой рамкой 2px #38bdf8 через свойство selected.
    - Инвариант Stealth Focus: setFocusPolicy(Qt.NoFocus).
    """

    cell_clicked = Signal(int)
    action_dropped = Signal(int, dict)
    slot_dropped = Signal(int, int, bool)

    def __init__(self, slot_index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.slot_index = slot_index
        self._title = ""
        self._icon = ""
        self._category = ""
        self._hotkey = ""
        self._status_source = "none"
        self._color_accent = "#38bdf8"
        self._font_size = 11
        self._font_color = "#d4d4d8"
        self._text_alignment = "bottom"
        self._hide_title = False
        self._drag_start_pos: Optional[QPoint] = None

        self.setObjectName("editorGridCell")
        self.setProperty("editorGridCell", "true")
        self.setProperty("selected", "false")
        self.setProperty("drag_hover", "false")
        self.setFixedSize(GRID_CELL_SIZE, GRID_CELL_SIZE)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self._cell_layout = QVBoxLayout(self)
        self._cell_layout.setContentsMargins(6, 6, 6, 6)
        self._cell_layout.setSpacing(2)

        # Верхняя строка: индекс слота [0]..[9] и бейдж статуса
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.lbl_index = QLabel(f"[{self.slot_index}]", self)
        self.lbl_index.setObjectName("lblCellIndex")
        self.lbl_index.setProperty("class", "CellIndexLabel")
        self.lbl_index.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_layout.addWidget(self.lbl_index, alignment=Qt.AlignLeft | Qt.AlignTop)
        top_layout.addStretch(1)

        self.lbl_status = QLabel("", self)
        self.lbl_status.setObjectName("lblCellStatus")
        self.lbl_status.setProperty("class", "CellStatusBadge")
        self.lbl_status.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_status.setVisible(False)
        top_layout.addWidget(self.lbl_status, alignment=Qt.AlignRight | Qt.AlignTop)

        self._cell_layout.addLayout(top_layout)

        # Центральная зона: иконка (26px)
        self.lbl_icon = QLabel("", self)
        self.lbl_icon.setObjectName("lblCellIcon")
        self.lbl_icon.setProperty("class", "CellIconLabel")
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self._cell_layout.addWidget(self.lbl_icon, 1, alignment=Qt.AlignCenter)

        # Нижняя зона: заголовок (11px)
        self.lbl_title = QLabel("", self)
        self.lbl_title.setObjectName("lblCellTitle")
        self.lbl_title.setProperty("class", "CellTitleLabel")
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self._cell_layout.addWidget(self.lbl_title, alignment=Qt.AlignCenter)

    def set_typography(
        self,
        font_size: int = 11,
        font_color: str = "#d4d4d8",
        text_alignment: str = "bottom",
        hide_title: bool = False,
    ) -> None:
        """
        Применяет пользовательские параметры шрифта и выравнивания к заголовку ячейки.
        """
        self._font_size = font_size
        self._font_color = font_color
        self._text_alignment = text_alignment
        self._hide_title = hide_title

        self.lbl_title.setStyleSheet(f"font-size: {font_size}px; color: {font_color};")
        self.lbl_title.setVisible(not hide_title)

        if text_alignment == "top":
            self._cell_layout.removeWidget(self.lbl_title)
            self._cell_layout.removeWidget(self.lbl_icon)
            self._cell_layout.addWidget(self.lbl_title, alignment=Qt.AlignCenter)
            self._cell_layout.addWidget(self.lbl_icon, 1, alignment=Qt.AlignCenter)
        else:
            self._cell_layout.removeWidget(self.lbl_title)
            self._cell_layout.removeWidget(self.lbl_icon)
            self._cell_layout.addWidget(self.lbl_icon, 1, alignment=Qt.AlignCenter)
            self._cell_layout.addWidget(self.lbl_title, alignment=Qt.AlignCenter)

    def update_status(
        self,
        status_text: Optional[str] = None,
        icon: Optional[str] = None,
        badge_color: Optional[str] = None,
    ) -> None:
        """
        Централизованное обновление бейджа живого тайла ячейки.
        """
        if status_text is not None:
            clean = status_text.strip()
            if clean:
                self.lbl_status.setText(clean)
                self.lbl_status.setVisible(True)
                if badge_color:
                    self.lbl_status.setStyleSheet(
                        f"font-size: 9px; font-weight: 600; color: {badge_color}; "
                        f"background-color: rgba(15, 23, 42, 0.85); "
                        f"border: 1px solid {badge_color}; border-radius: 4px; padding: 1px 3px;"
                    )
                else:
                    self.lbl_status.setStyleSheet("")
            else:
                self.lbl_status.setText("")
                self.lbl_status.setVisible(False)

    def set_selected(self, selected: bool) -> None:
        """
        Переключает состояние выделения ячейки.
        Обновляет динамическое свойство 'selected' и перезагружает стиль.
        """
        val_str = "true" if selected else "false"
        if self.property("selected") == val_str:
            return

        self.setProperty("selected", val_str)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def is_selected(self) -> bool:
        """
        Возвращает True, если ячейка выделена.
        """
        return self.property("selected") in ("true", True)

    def set_button_data(
        self,
        title: str,
        icon: str,
        category: str = "",
        hotkey: str = "",
        status_source: str = "none",
        color_accent: str = "#38bdf8",
        font_size: int = 11,
        font_color: str = "#d4d4d8",
        text_alignment: str = "bottom",
        hide_title: bool = False,
    ) -> None:
        """
        Задает отображаемые данные кнопки в ячейке.
        """
        self._title = title
        self._icon = icon
        self._category = category
        self._hotkey = hotkey
        self._status_source = status_source
        self._color_accent = color_accent

        self.set_typography(font_size, font_color, text_alignment, hide_title)

        if icon and os.path.isfile(icon):
            pixmap = QPixmap(icon)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    48,
                    48,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.lbl_icon.setPixmap(scaled)
            else:
                self.lbl_icon.setText(icon)
        else:
            self.lbl_icon.setText(icon)

        # Эллипсис для длинных названий
        metrics = QFontMetrics(self.lbl_title.font())
        elided = metrics.elidedText(title, Qt.ElideRight, GRID_CELL_SIZE - 16)
        self.lbl_title.setText(elided)
        self.setToolTip(f"{title} ({hotkey})" if hotkey else title)

        # Отображение превью живого статуса
        if status_source == "mic_mute":
            self.update_status("🎙 LIVE")
        elif status_source == "audio_device":
            self.update_status("🔊 DEV")
        elif status_source == "dimmer":
            self.update_status("🌙 DIM")
        elif status_source == "cpu_temp":
            self.update_status("58°C", badge_color="#10b981")
        elif status_source == "gpu_temp":
            self.update_status("62°C", badge_color="#f59e0b")
        else:
            self.update_status("")

    def clear_button_data(self) -> None:
        """
        Сбрасывает данные кнопки, возвращая ячейку в пустое состояние.
        """
        self._title = ""
        self._icon = ""
        self._category = ""
        self._hotkey = ""
        self._status_source = "none"
        self._color_accent = "#38bdf8"

        self.lbl_icon.clear()
        self.lbl_title.setText("")
        self.lbl_status.setText("")
        self.lbl_status.setVisible(False)
        self.set_typography(11, "#d4d4d8", "bottom", False)
        self.setToolTip("")

    def get_button_data(self) -> dict[str, Any]:
        """
        Возвращает словарь текущих данных ячейки.
        """
        return {
            "title": self._title,
            "icon": self._icon,
            "category": self._category,
            "hotkey": self._hotkey,
            "status_source": self._status_source,
            "color_accent": self._color_accent,
            "font_size": self._font_size,
            "font_color": self._font_color,
            "text_alignment": self._text_alignment,
            "hide_title": self._hide_title,
        }

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Обработка клика мыши: эмиттирует cell_clicked(slot_index) при нажатии ЛКМ.
        """
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self.cell_clicked.emit(self.slot_index)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Инициализация Drag-and-Drop слота холста.
        """
        if (event.buttons() & Qt.LeftButton) and self._drag_start_pos is not None:
            dist = (event.pos() - self._drag_start_pos).manhattanLength()
            if dist >= QApplication.startDragDistance():
                self._drag_start_pos = None
                if bool(self._title) or bool(self._icon) or bool(self._hotkey):
                    mime = QMimeData()
                    mime.setData("application/x-duckdeck-slot", str(self.slot_index).encode("utf-8"))
                    drag = QDrag(self)
                    drag.setMimeData(mime)
                    pixmap = self.grab()
                    drag.setPixmap(pixmap)
                    drag.setHotSpot(event.pos())
                    drag.exec(Qt.MoveAction | Qt.CopyAction)
                    return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Проверка входящего DND: поддержка действий каталога и перестановки слотов.
        """
        mime = event.mimeData()
        if mime.hasFormat("application/x-duckdeck-action") or mime.hasFormat("application/x-duckdeck-slot"):
            event.acceptProposedAction()
            self.setProperty("drag_hover", "true")
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Подтверждение перемещения курсора над ячейкой."""
        mime = event.mimeData()
        if mime.hasFormat("application/x-duckdeck-action") or mime.hasFormat("application/x-duckdeck-slot"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Снятие подсветки ячейки при уходе курсора."""
        self.setProperty("drag_hover", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Обработка сброса действия или кнопки на целевую ячейку.
        """
        self.setProperty("drag_hover", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        mime = event.mimeData()
        if mime.hasFormat("application/x-duckdeck-action"):
            raw_bytes = bytes(mime.data("application/x-duckdeck-action"))
            try:
                action_data = json.loads(raw_bytes.decode("utf-8"))
                if not isinstance(action_data, dict) or not action_data.get("id"):
                    logger.warning("Invalid action payload structure: %s", action_data)
                    event.ignore()
                    return
                self.action_dropped.emit(self.slot_index, action_data)
                event.acceptProposedAction()
            except Exception as exc:
                logger.warning("Failed to parse dropped action data: %s", exc)
                event.ignore()
        elif mime.hasFormat("application/x-duckdeck-slot"):
            raw_bytes = bytes(mime.data("application/x-duckdeck-slot"))
            try:
                src_slot = int(raw_bytes.decode("utf-8"))
                if not (0 <= src_slot < 10):
                    logger.warning("Dropped slot index out of bounds: %d", src_slot)
                    event.ignore()
                    return
                if src_slot == self.slot_index:
                    event.ignore()
                    return
                is_copy = bool(event.modifiers() & Qt.ControlModifier)
                self.slot_dropped.emit(src_slot, self.slot_index, is_copy)
                event.acceptProposedAction()
            except Exception as exc:
                logger.warning("Failed to parse dropped slot data: %s", exc)
                event.ignore()
        else:
            event.ignore()
