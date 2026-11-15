"""
Контейнер сетки сенсорных кнопок DuckDeck.
"""
import logging
from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QSpacerItem, QWidget

from modules.deck.models import DeckPageConfig
from modules.deck.widgets.deck_button import DeckButtonWidget

logger = logging.getLogger("duckdock.deck.grid")


class DeckGrid(QWidget):
    """
    Контейнер сетки сенсорных кнопок DuckDeck.
    Габариты строго 944x372 px (с отступами 12 px и промежутками 12 px).
    Матрица: 2 строки x 5 колонок = 10 кнопок на страницу.
    Кнопки фиксированного размера 174x168 px.
    """
    button_triggered = Signal(object)  # DeckButtonConfig

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DeckGrid")
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(944, 372)

        self._buttons: Dict[str, DeckButtonWidget] = {}

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)
        self.grid_layout.setSpacing(12)

    def load_page(self, page_config: DeckPageConfig) -> None:
        """
        Загрузка страницы кнопок с очисткой предыдущих виджетов без утечек памяти.
        В DuckDeck v0.4.0 используется сетка 2x5 (10 кнопок на страницу).
        """
        # Очистка существующих элементов
        self.clear()

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

    def get_buttons(self) -> Dict[str, DeckButtonWidget]:
        """Возвращает словарь всех активных кнопок сетки."""
        return self._buttons.copy()

    def clear(self) -> None:
        """Безопасная очистка сетки с удалением виджетов через deleteLater."""
        for btn in self._buttons.values():
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
        self.clear()


__all__ = ["DeckGrid"]
