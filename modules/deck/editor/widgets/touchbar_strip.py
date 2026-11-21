"""
Интерактивная полоса тачбара 3-го ряда DuckDeck Editor (EditorTouchbarStrip).
Габариты 528x68 px, 3 секции (Media, Clock, Telemetry), микро-разделители 1px,
каскадная поддержка локализации retranslate_ui() и эксклюзивное выделение секций.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QWidget,
)

from modules.deck.editor.styles import (
    TOUCHBAR_HEIGHT,
    TOUCHBAR_WIDTH,
)
from modules.deck.editor.widgets.touchbar_section import TouchbarSectionWidget

logger = logging.getLogger(__name__)


class EditorTouchbarStrip(QFrame):
    """
    Интерактивная полоса тачбара 3-го ряда (528x68 px).
    - 3 секции: Media (~32%), Clock (~38%), Telemetry (~30%).
    - Вертикальные микро-линии 1px #232b3e между секциями.
    - Перехват кликов и эмиссия section_selected(str).
    - Каскадный retranslate_ui().
    """

    section_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._selected_section: Optional[str] = None

        self.setObjectName("editorTouchbarStrip")
        self.setProperty("editorTouchbarStrip", "true")
        self.setFixedSize(TOUCHBAR_WIDTH, TOUCHBAR_HEIGHT)
        self.setFocusPolicy(Qt.NoFocus)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Секция Media
        self.sec_media = TouchbarSectionWidget(
            section_type="media",
            title_key="deck.editor.canvas.touchbar.media_title",
            parent=self,
        )
        self.sec_media.section_clicked.connect(self._on_section_clicked)

        # Секция Clock
        self.sec_clock = TouchbarSectionWidget(
            section_type="clock",
            title_key="deck.editor.canvas.touchbar.clock_title",
            parent=self,
        )
        self.sec_clock.section_clicked.connect(self._on_section_clicked)

        # Секция Telemetry
        self.sec_telemetry = TouchbarSectionWidget(
            section_type="telemetry",
            title_key="deck.editor.canvas.touchbar.telemetry_title",
            parent=self,
        )
        self.sec_telemetry.section_clicked.connect(self._on_section_clicked)

        # Размещение в лэйауте с микро-разделителями и пропорциями (32%, 38%, 30%)
        layout.addWidget(self.sec_media, 32)
        layout.addWidget(self._create_divider())
        layout.addWidget(self.sec_clock, 38)
        layout.addWidget(self._create_divider())
        layout.addWidget(self.sec_telemetry, 30)

    def _create_divider(self) -> QFrame:
        """
        Создает вертикальный микро-разделитель 1px между секциями.
        Стилизуется централизованно через QSS (селектор .TouchbarDivider).
        """
        divider = QFrame(self)
        divider.setObjectName("touchbarDivider")
        divider.setProperty("class", "TouchbarDivider")
        divider.setFixedWidth(1)
        divider.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        return divider

    def _on_section_clicked(self, section_type: str) -> None:
        """
        Внутренний обработчик клика по секции: обновляет подсветку и эмитирует сигнал наружу.
        """
        self.select_section(section_type)
        self.section_selected.emit(section_type)

    def select_section(self, section_type: Optional[str]) -> None:
        """
        Активирует рамку выделения у целевой секции ('media' | 'clock' | 'telemetry')
        и снимает выделение с остальных секций.
        """
        self._selected_section = section_type
        self.sec_media.set_selected(section_type == "media")
        self.sec_clock.set_selected(section_type == "clock")
        self.sec_telemetry.set_selected(section_type == "telemetry")

    def clear_selection(self) -> None:
        """
        Снимает выделение со всех секций полосы тачбара.
        """
        self.select_section(None)

    def get_selected_section(self) -> Optional[str]:
        """
        Возвращает тип текущей выделенной секции или None.
        """
        return self._selected_section

    def retranslate_ui(self) -> None:
        """
        Каскадно обновляет локализованные подсказки и тексты всех дочерних секций.
        """
        self.sec_media.retranslate_ui()
        self.sec_clock.retranslate_ui()
        self.sec_telemetry.retranslate_ui()
