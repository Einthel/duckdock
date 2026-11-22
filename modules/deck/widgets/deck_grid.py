"""
Контейнер сетки сенсорных кнопок DuckDeck.
"""
import logging
from typing import Dict, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QGridLayout,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from modules.deck.models import DeckPageConfig
from modules.deck.widgets.deck_button import DeckButtonWidget
from modules.deck.widgets.swipe_detector import DeckSwipeDetector

logger = logging.getLogger("duckdock.deck.grid")


class DeckGrid(QWidget):
    """
    Контейнер сетки сенсорных кнопок DuckDeck.
    Габариты строго 944x372 px (с отступами 12 px и промежутками 12 px).
    Матрица: 2 строки x 5 колонок = 10 кнопок на страницу.
    Кнопки фиксированного размера 174x168 px.
    Поддерживает распознавание 1-пальцевого горизонтального свайпа и сброс состояния кнопок.
    """
    button_triggered = Signal(object)  # DeckButtonConfig
    swipe_detected = Signal(str)  # "left" | "right"
    swipe_left = Signal()
    swipe_right = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DeckGrid")
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(944, 372)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)

        self._buttons: Dict[str, DeckButtonWidget] = {}

        # Детектор свайпа по сетке и кнопкам
        self.swipe_detector = DeckSwipeDetector(self)
        self.swipe_detector.swipe_detected.connect(self.swipe_detected)
        self.swipe_detector.swipe_left.connect(self.swipe_left)
        self.swipe_detector.swipe_right.connect(self.swipe_right)
        self.installEventFilter(self.swipe_detector)

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)
        self.grid_layout.setSpacing(12)

        # Анимация плавного проявления сетки при смене страниц (Fade-In 160 мс)
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(160)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def load_page(self, page_config: DeckPageConfig) -> None:
        """
        Загрузка страницы кнопок с очисткой предыдущих виджетов без утечек памяти.
        В DuckDeck v0.4.0 используется сетка 2x5 (10 кнопок на страницу).
        """
        # Очистка существующих элементов
        self.clear()

        # Плавный Fade-In эффект при загрузке страницы
        if hasattr(self, "_fade_anim"):
            self._fade_anim.stop()
            self._fade_anim.setStartValue(0.4)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()

        rows = min(page_config.grid_rows or 2, 2)
        cols = page_config.grid_cols or 5

        # Размещение кнопок по формуле: row = idx // cols, col = idx % cols
        for idx, btn_cfg in enumerate(page_config.buttons):
            row = idx // cols
            col = idx % cols
            if row >= rows:
                logger.warning(
                    f"Кнопка '{btn_cfg.id}' выходит за пределы сетки ({rows}x{cols})"
                )
                break

            btn_widget = DeckButtonWidget(
                button_config=btn_cfg,
                rows=rows,
                cols=cols,
                parent=self,
            )
            btn_widget.installEventFilter(self.swipe_detector)
            btn_widget.triggered.connect(self.button_triggered.emit)
            self.grid_layout.addWidget(btn_widget, row, col, Qt.AlignCenter)
            self._buttons[btn_cfg.id] = btn_widget

        # Заполнение пустых ячеек сетки распорками для сохранения жесткой геометрии
        total_cells = rows * cols
        buttons_count = len(self._buttons)
        if buttons_count < total_cells:
            for idx in range(buttons_count, total_cells):
                r = idx // cols
                c = idx % cols
                spacer = QSpacerItem(
                    174 if cols == 5 else 143,
                    168 if rows <= 2 else 123,
                    QSizePolicy.Fixed,
                    QSizePolicy.Fixed,
                )
                self.grid_layout.addItem(spacer, r, c)

    def get_button(self, button_id: str) -> Optional[DeckButtonWidget]:
        """Получить виджет кнопки по ее ID."""
        return self._buttons.get(button_id)

    def update_page(self, page_config: DeckPageConfig) -> bool:
        """
        Обновляет кнопки текущей страницы in-place без пересоздания виджетов и мерцания.
        Возвращает True, если кнопки были успешно обновлены in-place,
        или False, если была выполнена полная перезагрузка сетки (load_page).
        """
        if not self._buttons:
            self.load_page(page_config)
            return True

        # Если количество кнопок изменилось, выполняем перестройку
        if len(self._buttons) != len(page_config.buttons):
            self.load_page(page_config)
            return False

        updated: Dict[str, DeckButtonWidget] = {}
        for btn_cfg in page_config.buttons:
            btn_widget = self._buttons.get(btn_cfg.id)
            if btn_widget is None:
                for existing_w in self._buttons.values():
                    if getattr(existing_w.button_config, "slot_index", None) == btn_cfg.slot_index:
                        btn_widget = existing_w
                        break
            if btn_widget is None:
                self.load_page(page_config)
                return False

            btn_widget.update_config(btn_cfg)
            updated[btn_cfg.id] = btn_widget

        self._buttons = updated
        return True

    def get_buttons(self) -> Dict[str, DeckButtonWidget]:
        """Возвращает словарь всех активных кнопок сетки."""
        return self._buttons.copy()

    def clear(self) -> None:
        """Безопасная очистка сетки с удалением виджетов через deleteLater."""
        for btn in self._buttons.values():
            try:
                btn.removeEventFilter(self.swipe_detector)
            except Exception:
                pass
            btn.cleanup()
            btn.setParent(None)
            btn.deleteLater()
        self._buttons.clear()

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def cleanup(self) -> None:
        """Освобождение ресурсов сетки."""
        if hasattr(self, "_fade_anim") and self._fade_anim.state() == QPropertyAnimation.State.Running:
            self._fade_anim.stop()
        self.clear()


__all__ = ["DeckGrid"]
