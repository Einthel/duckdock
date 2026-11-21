"""
Формы инспектора свойств для секций тачбара (3-й ряд):
- TouchbarMediaForm (Медиаплеер)
- TouchbarClockForm (Часы и навигация)
- TouchbarTelemetryForm (Системные датчики)
Все формы верстаются в строгом бюджете высоты 220 px и поддерживают In-place Retranslate.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.dto import (
    TouchbarClockDTO,
    TouchbarMediaDTO,
    TouchbarTelemetryDTO,
)
from modules.deck.editor.styles import (
    FORM_LABEL_WIDTH,
    INPUT_HEIGHT,
    INSPECTOR_HEIGHT,
)

# Поддерживаемые интервалы обновления телеметрии: (секунды, суффикс ключа локали)
TELEMETRY_REFRESH_INTERVALS = [
    (1, "refresh_1s"),
    (2, "refresh_2s"),
    (5, "refresh_5s"),
]


def _create_form_separator(parent: QWidget) -> QFrame:
    """
    Вспомогательная функция создания разделителя HLine (1px #2e2e36).
    """
    separator = QFrame(parent)
    separator.setFrameShape(QFrame.HLine)
    separator.setFrameShadow(QFrame.Plain)
    separator.setFixedHeight(1)
    separator.setStyleSheet("background-color: #2e2e36; border: none;")
    return separator


# ==============================================================================
# 1. TouchbarMediaForm: Настройки медиаплеера тачбара
# ==============================================================================
class TouchbarMediaForm(QWidget):
    """
    Форма инспектора свойств секции медиаплеера тачбара.
    Размещается на Index 2 стэка KeyPropertyInspector.
    """

    section_property_changed = Signal(str, str, object)
    reset_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("touchbarMediaForm")
        self.setFixedHeight(INSPECTOR_HEIGHT)

        self._sec_type: str = "media"

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 8, 12, 8)
        root_layout.setSpacing(6)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_header = QLabel(self)
        self.lbl_header.setObjectName("lblMediaHeader")
        self.lbl_header.setProperty("class", "InspectorCategoryLabel")

        self.btn_reset = QPushButton("↺", self)
        self.btn_reset.setObjectName("btnMediaReset")
        self.btn_reset.setProperty("class", "InspectorResetButton")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset_clicked)

        header_layout.addWidget(self.lbl_header)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_reset)
        root_layout.addLayout(header_layout)

        root_layout.addWidget(_create_form_separator(self))

        # Поле 1: Выбор плеера
        player_layout = QHBoxLayout()
        player_layout.setContentsMargins(0, 2, 0, 2)
        player_layout.setSpacing(8)

        self.lbl_player = QLabel(self)
        self.lbl_player.setObjectName("lblPlayerLabel")
        self.lbl_player.setProperty("class", "InspectorFieldLabel")
        self.lbl_player.setFixedWidth(FORM_LABEL_WIDTH)

        self.combo_player = QComboBox(self)
        self.combo_player.setObjectName("comboMediaPlayers")
        self.combo_player.setFixedHeight(INPUT_HEIGHT)
        self.combo_player.setCursor(Qt.PointingHandCursor)
        for player_name in ["Default", "YouTube Music", "Spotify", "Foobar2000", "YouTube", "AIMP"]:
            self.combo_player.addItem(player_name, player_name)
        self.combo_player.currentTextChanged.connect(
            lambda name: self.section_property_changed.emit(self._sec_type, "player", name)
        )

        player_layout.addWidget(self.lbl_player)
        player_layout.addWidget(self.combo_player)
        root_layout.addLayout(player_layout)

        # Поле 2: Чекбокс бегущей строки
        self.chk_marquee = QCheckBox(self)
        self.chk_marquee.setObjectName("chkMarqueeEnabled")
        self.chk_marquee.setChecked(True)
        self.chk_marquee.toggled.connect(
            lambda checked: self.section_property_changed.emit(
                self._sec_type, "marquee_enabled", checked
            )
        )
        root_layout.addWidget(self.chk_marquee)

        # Поле 3: Слайдер скорости бегущей строки (10..100)
        speed_layout = QHBoxLayout()
        speed_layout.setContentsMargins(0, 2, 0, 2)
        speed_layout.setSpacing(8)

        self.lbl_speed = QLabel(self)
        self.lbl_speed.setObjectName("lblSpeedLabel")
        self.lbl_speed.setProperty("class", "InspectorFieldLabel")

        self.slider_speed = QSlider(Qt.Horizontal, self)
        self.slider_speed.setObjectName("sliderMarqueeSpeed")
        self.slider_speed.setRange(10, 100)
        self.slider_speed.setSingleStep(5)
        self.slider_speed.setValue(50)
        self.slider_speed.setCursor(Qt.PointingHandCursor)

        self.lbl_speed_val = QLabel("50", self)
        self.lbl_speed_val.setObjectName("lblSpeedValue")
        self.lbl_speed_val.setProperty("class", "InspectorFieldLabel")
        self.lbl_speed_val.setFixedWidth(28)
        self.lbl_speed_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.slider_speed.valueChanged.connect(self._on_speed_changed)

        speed_layout.addWidget(self.lbl_speed)
        speed_layout.addWidget(self.slider_speed)
        speed_layout.addWidget(self.lbl_speed_val)
        root_layout.addLayout(speed_layout)

        root_layout.addStretch(1)
        self.retranslate_ui()

    def _on_speed_changed(self, value: int) -> None:
        self.lbl_speed_val.setText(str(value))
        self.section_property_changed.emit(self._sec_type, "marquee_speed", value)

    def _on_reset_clicked(self) -> None:
        default_dto = TouchbarMediaDTO()
        self.load_data(default_dto)
        self.reset_requested.emit(self._sec_type)
        self.section_property_changed.emit(self._sec_type, "player", default_dto.player)
        self.section_property_changed.emit(
            self._sec_type, "marquee_enabled", default_dto.marquee_enabled
        )
        self.section_property_changed.emit(
            self._sec_type, "marquee_speed", default_dto.marquee_speed
        )

    def load_data(self, dto: TouchbarMediaDTO) -> None:
        """
        Загружает параметры медиаплеера с защитой blockSignals(True).
        """
        self.combo_player.blockSignals(True)
        self.chk_marquee.blockSignals(True)
        self.slider_speed.blockSignals(True)
        try:
            # Выбор плеера
            idx = self.combo_player.findText(dto.player)
            if idx >= 0:
                self.combo_player.setCurrentIndex(idx)
            elif dto.player:
                self.combo_player.addItem(dto.player, dto.player)
                self.combo_player.setCurrentIndex(self.combo_player.count() - 1)
            elif self.combo_player.count() > 0:
                self.combo_player.setCurrentIndex(0)

            self.chk_marquee.setChecked(dto.marquee_enabled)
            self.slider_speed.setValue(dto.marquee_speed)
            self.lbl_speed_val.setText(str(dto.marquee_speed))
        finally:
            self.combo_player.blockSignals(False)
            self.chk_marquee.blockSignals(False)
            self.slider_speed.blockSignals(False)

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованные метки формы медиаплеера, сохраняя состояние настроек.
        """
        self.lbl_header.setText(t("deck.editor.inspector.touchbar.media_header"))
        self.btn_reset.setToolTip(t("deck.editor.inspector.tooltips.reset_settings"))
        self.lbl_player.setText(t("deck.editor.inspector.touchbar.player_label"))
        self.chk_marquee.setText(t("deck.editor.inspector.touchbar.marquee_enabled"))
        self.lbl_speed.setText(t("deck.editor.inspector.touchbar.marquee_speed"))


# ==============================================================================
# 2. TouchbarClockForm: Настройки часов и свайп-навигации тачбара
# ==============================================================================
class TouchbarClockForm(QWidget):
    """
    Форма инспектора свойств секции часов и навигации тачбара.
    Размещается на Index 3 стэка KeyPropertyInspector.
    """

    section_property_changed = Signal(str, str, object)
    reset_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("touchbarClockForm")
        self.setFixedHeight(INSPECTOR_HEIGHT)

        self._sec_type: str = "clock"

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 8, 12, 8)
        root_layout.setSpacing(6)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_header = QLabel(self)
        self.lbl_header.setObjectName("lblClockHeader")
        self.lbl_header.setProperty("class", "InspectorCategoryLabel")

        self.btn_reset = QPushButton("↺", self)
        self.btn_reset.setObjectName("btnClockReset")
        self.btn_reset.setProperty("class", "InspectorResetButton")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset_clicked)

        header_layout.addWidget(self.lbl_header)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_reset)
        root_layout.addLayout(header_layout)

        root_layout.addWidget(_create_form_separator(self))

        # Чекбоксы: 24-часовой формат и показ даты
        self.chk_24h = QCheckBox(self)
        self.chk_24h.setObjectName("chk24hFormat")
        self.chk_24h.setChecked(True)
        self.chk_24h.toggled.connect(
            lambda checked: self.section_property_changed.emit(
                self._sec_type, "is_24h", checked
            )
        )
        root_layout.addWidget(self.chk_24h)

        self.chk_show_date = QCheckBox(self)
        self.chk_show_date.setObjectName("chkShowDate")
        self.chk_show_date.setChecked(True)
        self.chk_show_date.toggled.connect(
            lambda checked: self.section_property_changed.emit(
                self._sec_type, "show_date", checked
            )
        )
        root_layout.addWidget(self.chk_show_date)

        # Слайдер чувствительности свайпа (1..10)
        swipe_layout = QHBoxLayout()
        swipe_layout.setContentsMargins(0, 2, 0, 2)
        swipe_layout.setSpacing(8)

        self.lbl_swipe = QLabel(self)
        self.lbl_swipe.setObjectName("lblSwipeLabel")
        self.lbl_swipe.setProperty("class", "InspectorFieldLabel")

        self.slider_swipe = QSlider(Qt.Horizontal, self)
        self.slider_swipe.setObjectName("sliderSwipeSensitivity")
        self.slider_swipe.setRange(1, 10)
        self.slider_swipe.setSingleStep(1)
        self.slider_swipe.setValue(3)
        self.slider_swipe.setCursor(Qt.PointingHandCursor)

        self.lbl_swipe_val = QLabel("3", self)
        self.lbl_swipe_val.setObjectName("lblSwipeValue")
        self.lbl_swipe_val.setProperty("class", "InspectorFieldLabel")
        self.lbl_swipe_val.setFixedWidth(24)
        self.lbl_swipe_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.slider_swipe.valueChanged.connect(self._on_swipe_changed)

        swipe_layout.addWidget(self.lbl_swipe)
        swipe_layout.addWidget(self.slider_swipe)
        swipe_layout.addWidget(self.lbl_swipe_val)
        root_layout.addLayout(swipe_layout)

        root_layout.addStretch(1)
        self.retranslate_ui()

    def _on_swipe_changed(self, value: int) -> None:
        self.lbl_swipe_val.setText(str(value))
        self.section_property_changed.emit(self._sec_type, "swipe_sensitivity", value)

    def _on_reset_clicked(self) -> None:
        default_dto = TouchbarClockDTO()
        self.load_data(default_dto)
        self.reset_requested.emit(self._sec_type)
        self.section_property_changed.emit(self._sec_type, "is_24h", default_dto.is_24h)
        self.section_property_changed.emit(
            self._sec_type, "show_date", default_dto.show_date
        )
        self.section_property_changed.emit(
            self._sec_type, "swipe_sensitivity", default_dto.swipe_sensitivity
        )

    def load_data(self, dto: TouchbarClockDTO) -> None:
        """
        Загружает параметры часов с защитой blockSignals(True).
        """
        self.chk_24h.blockSignals(True)
        self.chk_show_date.blockSignals(True)
        self.slider_swipe.blockSignals(True)
        try:
            self.chk_24h.setChecked(dto.is_24h)
            self.chk_show_date.setChecked(dto.show_date)
            self.slider_swipe.setValue(dto.swipe_sensitivity)
            self.lbl_swipe_val.setText(str(dto.swipe_sensitivity))
        finally:
            self.chk_24h.blockSignals(False)
            self.chk_show_date.blockSignals(False)
            self.slider_swipe.blockSignals(False)

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованные подписи полей часов без сброса значений.
        """
        self.lbl_header.setText(t("deck.editor.inspector.touchbar.clock_header"))
        self.btn_reset.setToolTip(t("deck.editor.inspector.tooltips.reset_settings"))
        self.chk_24h.setText(t("deck.editor.inspector.touchbar.time_format_24h"))
        self.chk_show_date.setText(t("deck.editor.inspector.touchbar.show_date"))
        self.lbl_swipe.setText(t("deck.editor.inspector.touchbar.swipe_sensitivity"))


# ==============================================================================
# 3. TouchbarTelemetryForm: Настройки датчиков телеметрии тачбара
# ==============================================================================
class TouchbarTelemetryForm(QWidget):
    """
    Форма инспектора свойств секции системных датчиков тачбара.
    Размещается на Index 4 стэка KeyPropertyInspector.
    """

    section_property_changed = Signal(str, str, object)
    reset_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("touchbarTelemetryForm")
        self.setFixedHeight(INSPECTOR_HEIGHT)

        self._sec_type: str = "telemetry"

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 8, 12, 8)
        root_layout.setSpacing(6)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_header = QLabel(self)
        self.lbl_header.setObjectName("lblTelemetryHeader")
        self.lbl_header.setProperty("class", "InspectorCategoryLabel")

        self.btn_reset = QPushButton("↺", self)
        self.btn_reset.setObjectName("btnTelemetryReset")
        self.btn_reset.setProperty("class", "InspectorResetButton")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset_clicked)

        header_layout.addWidget(self.lbl_header)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_reset)
        root_layout.addLayout(header_layout)

        root_layout.addWidget(_create_form_separator(self))

        # Чекбоксы CPU и GPU
        sensors_row = QHBoxLayout()
        sensors_row.setContentsMargins(0, 2, 0, 2)
        sensors_row.setSpacing(16)

        self.chk_cpu = QCheckBox(self)
        self.chk_cpu.setObjectName("chkShowCpu")
        self.chk_cpu.setChecked(True)
        self.chk_cpu.toggled.connect(
            lambda checked: self.section_property_changed.emit(
                self._sec_type, "show_cpu", checked
            )
        )

        self.chk_gpu = QCheckBox(self)
        self.chk_gpu.setObjectName("chkShowGpu")
        self.chk_gpu.setChecked(True)
        self.chk_gpu.toggled.connect(
            lambda checked: self.section_property_changed.emit(
                self._sec_type, "show_gpu", checked
            )
        )

        sensors_row.addWidget(self.chk_cpu)
        sensors_row.addWidget(self.chk_gpu)
        sensors_row.addStretch(1)
        root_layout.addLayout(sensors_row)

        # Выбор интервала обновления (1s, 2s, 5s)
        refresh_layout = QHBoxLayout()
        refresh_layout.setContentsMargins(0, 2, 0, 2)
        refresh_layout.setSpacing(8)

        self.lbl_refresh = QLabel(self)
        self.lbl_refresh.setObjectName("lblRefreshLabel")
        self.lbl_refresh.setProperty("class", "InspectorFieldLabel")

        self.combo_refresh = QComboBox(self)
        self.combo_refresh.setObjectName("comboRefreshInterval")
        self.combo_refresh.setFixedHeight(INPUT_HEIGHT)
        self.combo_refresh.setCursor(Qt.PointingHandCursor)
        for interval_s, key_suffix in TELEMETRY_REFRESH_INTERVALS:
            self.combo_refresh.addItem(
                t(f"deck.editor.inspector.touchbar.{key_suffix}"), interval_s
            )
        self.combo_refresh.currentIndexChanged.connect(self._on_refresh_interval_changed)

        refresh_layout.addWidget(self.lbl_refresh)
        refresh_layout.addWidget(self.combo_refresh)
        root_layout.addLayout(refresh_layout)

        # Чекбокс оповещения о перегреве
        self.chk_overheat = QCheckBox(self)
        self.chk_overheat.setObjectName("chkOverheatAlerts")
        self.chk_overheat.setChecked(False)
        self.chk_overheat.toggled.connect(
            lambda checked: self.section_property_changed.emit(
                self._sec_type, "overheat_alerts", checked
            )
        )
        root_layout.addWidget(self.chk_overheat)

        root_layout.addStretch(1)
        self.retranslate_ui()

    def _on_refresh_interval_changed(self, index: int) -> None:
        interval_val = self.combo_refresh.itemData(index)
        self.section_property_changed.emit(
            self._sec_type, "refresh_interval_s", interval_val
        )

    def _on_reset_clicked(self) -> None:
        default_dto = TouchbarTelemetryDTO()
        self.load_data(default_dto)
        self.reset_requested.emit(self._sec_type)
        self.section_property_changed.emit(
            self._sec_type, "show_cpu", default_dto.show_cpu
        )
        self.section_property_changed.emit(
            self._sec_type, "show_gpu", default_dto.show_gpu
        )
        self.section_property_changed.emit(
            self._sec_type, "refresh_interval_s", default_dto.refresh_interval_s
        )
        self.section_property_changed.emit(
            self._sec_type, "overheat_alerts", False
        )

    def load_data(self, dto: TouchbarTelemetryDTO) -> None:
        """
        Загружает параметры датчиков с защитой blockSignals(True).
        """
        self.chk_cpu.blockSignals(True)
        self.chk_gpu.blockSignals(True)
        self.combo_refresh.blockSignals(True)
        self.chk_overheat.blockSignals(True)
        try:
            self.chk_cpu.setChecked(dto.show_cpu)
            self.chk_gpu.setChecked(dto.show_gpu)

            # Сопоставление интервала обновления
            for i in range(self.combo_refresh.count()):
                if self.combo_refresh.itemData(i) == dto.refresh_interval_s:
                    self.combo_refresh.setCurrentIndex(i)
                    break
        finally:
            self.chk_cpu.blockSignals(False)
            self.chk_gpu.blockSignals(False)
            self.combo_refresh.blockSignals(False)
            self.chk_overheat.blockSignals(False)

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованные подписи сенсоров и интервалов обновления,
        сохраняя активный выбор пользователя.
        """
        self.lbl_header.setText(t("deck.editor.inspector.touchbar.telemetry_header"))
        self.btn_reset.setToolTip(t("deck.editor.inspector.tooltips.reset_settings"))
        self.chk_cpu.setText(t("deck.editor.inspector.touchbar.show_cpu"))
        self.chk_gpu.setText(t("deck.editor.inspector.touchbar.show_gpu"))
        self.lbl_refresh.setText(t("deck.editor.inspector.touchbar.refresh_interval"))
        self.chk_overheat.setText(t("deck.editor.inspector.touchbar.overheat_alerts"))

        self.combo_refresh.blockSignals(True)
        try:
            for i in range(self.combo_refresh.count()):
                interval_s = self.combo_refresh.itemData(i)
                for sec, key_suffix in TELEMETRY_REFRESH_INTERVALS:
                    if sec == interval_s:
                        self.combo_refresh.setItemText(
                            i, t(f"deck.editor.inspector.touchbar.{key_suffix}")
                        )
                        break
        finally:
            self.combo_refresh.blockSignals(False)
