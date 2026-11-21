"""
Виджет интерактивной секции тачбара DuckDeck Editor (TouchbarSectionWidget).
Представляет одну из 3-х секций полосы тачбара 3-го ряда:
- "media": медиаплеер (обложка, название трека, кнопки управления);
- "clock": цифровые часы, дата и индикатор страниц;
- "telemetry": датчики CPU/GPU и кнопка настроек.
Поддерживает выделение синей рамкой, перехват клика мыши с изоляцией дочерних элементов
и реактивное обновление подсказок через retranslate_ui().
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.styles import (
    BORDER_FOCUS_ACCENT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

logger = logging.getLogger(__name__)


class TouchbarSectionWidget(QFrame):
    """
    Интерактивная секция интерактивного тачбара холста.
    - section_type: 'media' | 'clock' | 'telemetry'
    - title_key: ключ локализации из 'deck.editor.canvas.touchbar.*_title'
    - Инвариант: все дочерние элементы получают WA_TransparentForMouseEvents=True.
      Секция перехватывает клик и эмитирует section_clicked(str).
    """

    section_clicked = Signal(str)

    def __init__(
        self,
        section_type: str,
        title_key: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.section_type = section_type
        self.title_key = title_key

        self.setObjectName("touchbarSectionWidget")
        self.setProperty("touchbarSection", "true")
        self.setProperty("selected", "false")
        self.setCursor(Qt.PointingHandCursor)

        self._build_section_ui()
        self._make_children_transparent()
        self.retranslate_ui()

    def _build_section_ui(self) -> None:
        """
        Формирует WYSIWYG-представление в зависимости от типа секции.
        """
        if self.section_type == "media":
            self._build_media_ui()
        elif self.section_type == "clock":
            self._build_clock_ui()
        elif self.section_type == "telemetry":
            self._build_telemetry_ui()
        else:
            self._build_fallback_ui()

    def _build_media_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # Иконка ноты
        lbl_icon = QLabel("🎵", self)
        lbl_icon.setStyleSheet(
            f"color: {BORDER_FOCUS_ACCENT}; font-size: 18px; background: transparent; border: none;"
        )
        layout.addWidget(lbl_icon)

        # Текстовый блок (название трека)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        text_layout.setAlignment(Qt.AlignVCenter)

        lbl_track = QLabel("YouTube Music", self)
        lbl_track.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: 600; background: transparent; border: none;"
        )
        text_layout.addWidget(lbl_track)

        lbl_artist = QLabel("DuckDeck Player", self)
        lbl_artist.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 9px; background: transparent; border: none;"
        )
        text_layout.addWidget(lbl_artist)

        layout.addLayout(text_layout)
        layout.addStretch(1)

        # Мини-кнопки управления ⏮ ⏯ ⏭
        lbl_controls = QLabel("⏮  ⏯  ⏭", self)
        lbl_controls.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent; border: none;"
        )
        layout.addWidget(lbl_controls)

    def _build_clock_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        # Цифровые часы
        lbl_time = QLabel("14:45", self)
        lbl_time.setAlignment(Qt.AlignCenter)
        lbl_time.setStyleSheet(
            f"color: {BORDER_FOCUS_ACCENT}; font-size: 16px; font-weight: 700; background: transparent; border: none;"
        )
        layout.addWidget(lbl_time)

        # Точечный индикатор страниц
        lbl_dots = QLabel("●  ○  ○", self)
        lbl_dots.setAlignment(Qt.AlignCenter)
        lbl_dots.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 9px; background: transparent; border: none;"
        )
        layout.addWidget(lbl_dots)

    def _build_telemetry_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # Плашки датчиков
        sensors_layout = QVBoxLayout()
        sensors_layout.setContentsMargins(0, 0, 0, 0)
        sensors_layout.setSpacing(2)
        sensors_layout.setAlignment(Qt.AlignVCenter)

        lbl_cpu = QLabel("CPU 48°C", self)
        lbl_cpu.setStyleSheet(
            "color: #10b981; font-size: 10px; font-weight: 600; background: transparent; border: none;"
        )
        sensors_layout.addWidget(lbl_cpu)

        lbl_gpu = QLabel("GPU 52°C", self)
        lbl_gpu.setStyleSheet(
            "color: #10b981; font-size: 10px; font-weight: 600; background: transparent; border: none;"
        )
        sensors_layout.addWidget(lbl_gpu)

        layout.addLayout(sensors_layout)
        layout.addStretch(1)

        # Сервисная иконка шестеренки
        lbl_gear = QLabel("⚙", self)
        lbl_gear.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 14px; background: transparent; border: none;"
        )
        layout.addWidget(lbl_gear)

    def _build_fallback_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignCenter)
        lbl = QLabel(self.section_type, self)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(lbl)

    def _make_children_transparent(self) -> None:
        """
        Инвариант: устанавливает Qt.WA_TransparentForMouseEvents = True на все дочерние виджеты,
        чтобы клик в любую область секции не поглощался вложенными элементами.
        """
        for child in self.findChildren(QWidget):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_selected(self, selected: bool) -> None:
        """
        Переключает состояние выделения секции тачбара.
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
        Возвращает True, если секция выделена.
        """
        return self.property("selected") in ("true", True)

    def retranslate_ui(self) -> None:
        """
        Обновляет подсказку секции через t(self.title_key) согласно текущей локали.
        """
        if self.title_key:
            self.setToolTip(t(self.title_key))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Перехватывает нажатие ЛКМ и эмитирует section_clicked(str).
        """
        if event.button() == Qt.LeftButton:
            self.section_clicked.emit(self.section_type)
            event.accept()
        else:
            super().mousePressEvent(event)
