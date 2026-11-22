"""
Виджет инспектора свойств DuckDeck (KeyPropertyInspector).
Реализует постоянный инспектор свойств на базе QStackedWidget фиксированной высоты 220 px:
- Index 0: Плейсхолдер выбора ("Выберите кнопку для настройки действия.")
- Index 1: Форма редактирования кнопки сетки (ButtonPropertyForm)
- Index 2: Форма настроек медиаплеера тачбара (TouchbarMediaForm)
- Index 3: Форма настроек часов и навигации тачбара (TouchbarClockForm)
- Index 4: Форма настроек датчиков телеметрии тачбара (TouchbarTelemetryForm)
Обеспечивает In-place Retranslate Invariant и изоляцию от сигнального эха.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.dto import (
    ButtonSlotDTO,
    TouchbarClockDTO,
    TouchbarMediaDTO,
    TouchbarTelemetryDTO,
)
from modules.deck.editor.styles import INSPECTOR_HEIGHT
from modules.deck.editor.widgets.button_property_form import ButtonPropertyForm
from modules.deck.editor.widgets.touchbar_property_forms import (
    TouchbarClockForm,
    TouchbarMediaForm,
    TouchbarTelemetryForm,
)

logger = logging.getLogger("duckdock.deck.editor.inspector")


class KeyPropertyInspector(QFrame):
    """
    Постоянный инспектор свойств кнопки и секций тачбара DuckDeck.
    Управляет стеком форм (QStackedWidget) с фиксированной высотой 220 px:
      - Index 0: Плейсхолдер с подсказкой t("deck.editor.inspector.placeholder")
      - Index 1: ButtonPropertyForm (кнопки сетки 0..9)
      - Index 2: TouchbarMediaForm (секция media)
      - Index 3: TouchbarClockForm (секция clock)
      - Index 4: TouchbarTelemetryForm (секция telemetry)
    """

    button_updated = Signal(int, str, object)
    touchbar_updated = Signal(str, str, object)
    slot_cleared = Signal(int)
    test_action_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setObjectName("propertyInspector")
        self.setProperty("class", "KeyPropertyInspector")
        self.setFixedHeight(INSPECTOR_HEIGHT)

        self._current_slot_index: Optional[int] = None
        self._current_section_type: Optional[str] = None
        self._current_mode: str = "placeholder"

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Инициализация стека форм и подключение сигналов."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("inspectorStackedWidget")

        # ----------------------------------------------------------------------
        # Index 0: Плейсхолдер нейтрального состояния
        # ----------------------------------------------------------------------
        self.placeholder_widget = QWidget(self.stack)
        self.placeholder_widget.setObjectName("inspectorPlaceholderContainer")
        ph_layout = QVBoxLayout(self.placeholder_widget)
        ph_layout.setContentsMargins(16, 16, 16, 16)
        ph_layout.setAlignment(Qt.AlignCenter)

        self.lbl_placeholder = QLabel(t("deck.editor.inspector.placeholder"), self.placeholder_widget)
        self.lbl_placeholder.setObjectName("lblInspectorPlaceholder")
        self.lbl_placeholder.setProperty("class", "InspectorPlaceholder")
        self.lbl_placeholder.setAlignment(Qt.AlignCenter)
        ph_layout.addWidget(self.lbl_placeholder)

        self.stack.addWidget(self.placeholder_widget)

        # ----------------------------------------------------------------------
        # Index 1: Форма свойств кнопки сетки (0..9)
        # ----------------------------------------------------------------------
        self.button_form = ButtonPropertyForm(self.stack)
        self.button_form.property_changed.connect(self._on_button_property_changed)
        self.button_form.delete_requested.connect(self._on_button_delete_requested)
        self.button_form.test_action_requested.connect(self.test_action_requested.emit)
        self.stack.addWidget(self.button_form)

        # ----------------------------------------------------------------------
        # Index 2: Форма свойств медиаплеера тачбара
        # ----------------------------------------------------------------------
        self.media_form = TouchbarMediaForm(self.stack)
        self.media_form.section_property_changed.connect(self._on_touchbar_property_changed)
        self.stack.addWidget(self.media_form)

        # ----------------------------------------------------------------------
        # Index 3: Форма свойств часов и навигации тачбара
        # ----------------------------------------------------------------------
        self.clock_form = TouchbarClockForm(self.stack)
        self.clock_form.section_property_changed.connect(self._on_touchbar_property_changed)
        self.stack.addWidget(self.clock_form)

        # ----------------------------------------------------------------------
        # Index 4: Форма свойств датчиков телеметрии тачбара
        # ----------------------------------------------------------------------
        self.telemetry_form = TouchbarTelemetryForm(self.stack)
        self.telemetry_form.section_property_changed.connect(self._on_touchbar_property_changed)
        self.stack.addWidget(self.telemetry_form)

        layout.addWidget(self.stack)

        # Начальное состояние — строго Index 0
        self.show_placeholder()

    # ==========================================================================
    # Публичный API управления отображением и загрузки данных
    # ==========================================================================

    def show_placeholder(self) -> None:
        """Переключает инспектор в нейтральное состояние плейсхолдера (Index 0)."""
        self._current_slot_index = None
        self._current_section_type = None
        self._current_mode = "placeholder"
        self.stack.setCurrentIndex(0)

    def load_button_slot(self, slot_index: int, data: ButtonSlotDTO) -> None:
        """
        Переключает инспектор на форму редактирования кнопки (Index 1)
        и загружает переданный DTO в форму.
        """
        self._current_slot_index = slot_index
        self._current_section_type = None
        self._current_mode = "button"
        data.slot_index = slot_index
        self.button_form.load_slot_data(data)
        self.stack.setCurrentIndex(1)

    def load_touchbar_section(self, section_type: str, data: Any = None) -> None:
        """
        Переключает инспектор на соответствующую форму тачбара (Index 2..4)
        и загружает конфигурационные параметры секции.
        """
        self._current_slot_index = None
        self._current_section_type = section_type
        self._current_mode = "touchbar"

        if section_type == "media":
            if data is not None and isinstance(data, TouchbarMediaDTO):
                self.media_form.load_data(data)
            self.stack.setCurrentIndex(2)
        elif section_type == "clock":
            if data is not None and isinstance(data, TouchbarClockDTO):
                self.clock_form.load_data(data)
            self.stack.setCurrentIndex(3)
        elif section_type == "telemetry":
            if data is not None and isinstance(data, TouchbarTelemetryDTO):
                self.telemetry_form.load_data(data)
            self.stack.setCurrentIndex(4)
        else:
            logger.warning("Unknown touchbar section type '%s', showing placeholder", section_type)
            self.show_placeholder()

    @property
    def current_slot_index(self) -> Optional[int]:
        """Возвращает индекс активного слота кнопки или None."""
        return self._current_slot_index

    @property
    def current_section_type(self) -> Optional[str]:
        """Возвращает тип активной секции тачбара или None."""
        return self._current_section_type

    @property
    def current_mode(self) -> str:
        """Возвращает текущий режим ('placeholder' | 'button' | 'touchbar')."""
        return self._current_mode

    # ==========================================================================
    # Внутренние обработчики форм и трансляция сигналов
    # ==========================================================================

    def _on_button_property_changed(self, prop: str, val: object) -> None:
        """Транслирует изменение свойства кнопки наружу с указанием slot_index."""
        if self._current_slot_index is not None:
            self.button_updated.emit(self._current_slot_index, prop, val)

    def _on_button_delete_requested(self) -> None:
        """
        Обрабатывает клик по корзине 🗑️ в шапке формы кнопки:
        эмитирует сигнал slot_cleared и сбрасывает инспектор в плейсхолдер.
        """
        if self._current_slot_index is not None:
            slot_idx = self._current_slot_index
            self.slot_cleared.emit(slot_idx)
            self.show_placeholder()

    def _on_touchbar_property_changed(self, sec_type: str, prop: str, val: object) -> None:
        """Транслирует изменение параметров секции тачбара наружу."""
        self.touchbar_updated.emit(sec_type, prop, val)

    # ==========================================================================
    # Реактивная локализация (Localization-First & In-place Retranslate)
    # ==========================================================================

    def retranslate_ui(self) -> None:
        """
        Каскадно обновляет текст плейсхолдера и локализацию всех форм в стеке.
        Сохраняет введенный пользователем текст и текущий выбор параметров.
        """
        self.lbl_placeholder.setText(t("deck.editor.inspector.placeholder"))
        self.button_form.retranslate_ui()
        self.media_form.retranslate_ui()
        self.clock_form.retranslate_ui()
        self.telemetry_form.retranslate_ui()
