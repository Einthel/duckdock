"""
Виджет отдельного действия каталога DuckDeck (ActionItemWidget).
Представляет собой компактную кликабельную карточку действия с иконкой и локализованным названием.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal, QMimeData
from PySide6.QtGui import QContextMenuEvent, QDrag, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.dto import ActionItemDTO
from modules.deck.editor.styles import ACTION_ITEM_HEIGHT


class ActionItemWidget(QFrame):
    """
    Карточка действия в библиотеке DuckDeck.
    Высота 36 px, стиль ActionItemCard, подложка иконки 24x24 px.
    Поддерживает протокол локализации retranslate_ui и эмитирует сигнал item_clicked(ActionItemDTO).
    """

    item_clicked = Signal(object)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(
        self,
        item_dto: ActionItemDTO,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.item_dto = item_dto
        self._context_menu: Optional[QMenu] = None

        self.setObjectName(f"actionItem_{item_dto.id}")
        self.setProperty("class", "ActionItemCard")
        self.setFixedHeight(ACTION_ITEM_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 8, 2)
        layout.setSpacing(8)

        # Подложка иконки (24x24 px)
        self.icon_box = QFrame(self)
        self.icon_box.setObjectName("actionItemIconBox")
        self.icon_box.setProperty("class", "ActionItemIconBox")
        self.icon_box.setFixedSize(24, 24)

        icon_layout = QHBoxLayout(self.icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)

        self.lbl_icon = QLabel(self.icon_box)
        self.lbl_icon.setObjectName("actionItemIcon")
        self.lbl_icon.setProperty("class", "ActionItemIcon")
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._render_icon(self.item_dto.icon)
        icon_layout.addWidget(self.lbl_icon)

        layout.addWidget(self.icon_box, 0, Qt.AlignVCenter)

        # Название действия
        self.lbl_title = QLabel(self._format_title(), self)
        self.lbl_title.setObjectName("actionItemTitle")
        self.lbl_title.setProperty("class", "ActionItemTitle")
        self.lbl_title.setTextFormat(Qt.PlainText)
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents)

        layout.addWidget(self.lbl_title, 1, Qt.AlignVCenter)

        # Подсказка и состояние WIP / Disabled
        if self._is_blocked():
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(0.5)
            self.setGraphicsEffect(effect)
            self.setCursor(Qt.ForbiddenCursor)
            self.setToolTip(t("deck.editor.tooltips.wip_feature"))
        else:
            self.setToolTip(self.item_dto.get_title())

        self._drag_start_pos: Optional[QPoint] = None

    def _render_icon(self, icon_str: str) -> None:
        """Отрисовывает графическую иконку (PNG/SVG) или эмодзи."""
        if icon_str and os.path.isfile(icon_str):
            pixmap = QPixmap(icon_str)
            if not pixmap.isNull():
                scaled = pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_icon.setPixmap(scaled)
                return
        self.lbl_icon.setText(icon_str or "🖲️")

    def _is_blocked(self) -> bool:
        """Возвращает True, если карточка находится в разработке (WIP) или отключена."""
        return bool(getattr(self.item_dto, "is_wip", False) or not getattr(self.item_dto, "is_enabled", True))

    def _format_title(self) -> str:
        """Формирует отображаемый заголовок с учетом статуса WIP."""
        base = self.item_dto.get_title()
        if getattr(self.item_dto, "is_wip", False):
            return f"{base}{t('deck.editor.presets.macro_wip_badge')}"
        if not getattr(self.item_dto, "is_enabled", True):
            return f"{base}{t('deck.editor.presets.switch_profile_wip_badge')}"
        return base

    def retranslate_ui(self) -> None:
        """Обновляет локализованное название действия и тултип."""
        self.lbl_title.setText(self._format_title())
        if self._is_blocked():
            self.setToolTip(t("deck.editor.tooltips.wip_feature"))
        else:
            self.setToolTip(self.item_dto.get_title())

    def set_active(self, active: bool) -> None:
        """Устанавливает визуальный статус активности карточки."""
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Фиксация точки начала взаимодействия для детекции Drag-and-Drop."""
        if event.button() == Qt.LeftButton:
            if self._is_blocked():
                event.accept()
                return
            self._drag_start_pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Сброс координаты перетаскивания и локальное уведомление о клике."""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = None
            if not self._is_blocked():
                self.item_clicked.emit(self.item_dto)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Инициализация Drag-and-Drop при перемещении с зажатой ЛКМ."""
        if self._is_blocked():
            return
        if (event.buttons() & Qt.LeftButton) and self._drag_start_pos is not None:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            dist = (pos - self._drag_start_pos).manhattanLength()
            if dist >= QApplication.startDragDistance():
                self._drag_start_pos = None

                cat_id = getattr(self.item_dto, "category_id", "")
                if not cat_id and getattr(self.item_dto, "category_key", ""):
                    cat_id = self.item_dto.category_key.split(".")[-1]

                cfg = dict(getattr(self.item_dto, "default_config", {}) or {})
                is_custom = bool(getattr(self.item_dto, "is_custom", False))
                payload = {
                    "id": self.item_dto.id,
                    "title": self.item_dto.get_title(),
                    "icon": self.item_dto.icon,
                    "category": self.item_dto.category_key,
                    "category_id": cat_id,
                    "keywords": self.item_dto.keywords,
                    "is_custom": is_custom,
                    "default_config": cfg,
                }
                if is_custom:
                    payload["color_accent"] = cfg.get("color_accent", "#38bdf8")
                    payload["status_source"] = cfg.get("status_source")
                    payload["sound_override"] = cfg.get("sound_override")
                mime = QMimeData()
                mime.setData("application/x-duckdeck-action", json.dumps(payload).encode("utf-8"))
                drag = QDrag(self)
                drag.setMimeData(mime)
                pixmap = self.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(pos)
                drag.exec(Qt.CopyAction)
                return
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Контекстное меню (ПКМ) для пользовательских карточек библиотеки."""
        if not getattr(self.item_dto, "is_custom", False):
            event.ignore()
            return
        self.show_context_menu(event.globalPos())
        event.accept()

    def show_context_menu(self, global_pos: Optional[QPoint] = None) -> QMenu:
        """Создаёт и показывает контекстное меню для пользовательской карточки."""
        menu = QMenu(self)
        menu.setObjectName("customActionItemContextMenu")

        act_rename = menu.addAction(f"✏️ {t('deck.editor.drawer.custom.rename_item')}")
        act_rename.triggered.connect(lambda: self.rename_requested.emit(self.item_dto.id))

        act_delete = menu.addAction(f"🗑️ {t('deck.editor.drawer.custom.delete_item')}")
        act_delete.triggered.connect(lambda: self.delete_requested.emit(self.item_dto.id))

        self._context_menu = menu
        if global_pos is not None:
            menu.exec(global_pos)
        return menu
