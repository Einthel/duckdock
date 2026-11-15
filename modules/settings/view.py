"""
Сенсорный экран настроек DuckDock / TouchWM (SettingsView).
Размещается в рабочей области 944x600.
Обеспечивает просмотр и конфигурирование параметров экрана, диммера,
защиты фокуса (Stealth Focus) и системных интеграций.
"""
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.ui_base import TouchModuleView
from modules.settings.config import AppConfig, load_config

SETTINGS_QSS = """
QFrame.settings-card {
    background-color: #161b26;
    border: 1px solid #232b3e;
    border-radius: 12px;
    padding: 12px;
}

QLabel.title-label {
    color: #f8fafc;
    font-size: 18px;
    font-weight: bold;
}

QLabel.subtitle-label {
    color: #64748b;
    font-size: 12px;
}

QLabel.section-header {
    color: #e2e8f0;
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 4px;
}

QLabel.field-label {
    color: #94a3b8;
    font-size: 12px;
}

QLabel.field-value {
    color: #38bdf8;
    font-size: 12px;
    font-weight: bold;
}

QPushButton.settings-btn {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: bold;
    min-height: 36px;
}

QPushButton.settings-btn:hover {
    background-color: #2563eb;
    border-color: #60a5fa;
}

QPushButton.settings-btn:pressed {
    background-color: #1d4ed8;
}

QScrollArea {
    background-color: transparent;
    border: none;
}
"""


class SettingsView(TouchModuleView):
    """
    Экран сенсорных настроек DuckDock.
    Наследуется от TouchModuleView и гарантирует инвариант Stealth Focus (Qt.NoFocus).
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        config_path: Optional[Path | str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.config_path = config_path
        self.config = config if config is not None else load_config(config_path)
        self.setStyleSheet(SETTINGS_QSS)

        self._labels: dict[str, QLabel] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # 1. Заголовок экрана
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(2)

        lbl_title = QLabel("Настройки DuckDock")
        lbl_title.setProperty("class", "title-label")
        lbl_title.setFocusPolicy(Qt.NoFocus)

        lbl_sub = QLabel("Параметры дополнительного сенсорного экрана, диммера и защиты фокуса")
        lbl_sub.setProperty("class", "subtitle-label")
        lbl_sub.setFocusPolicy(Qt.NoFocus)

        header_text_layout.addWidget(lbl_title)
        header_text_layout.addWidget(lbl_sub)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        self.btn_reload = QPushButton("Перезагрузить JSON")
        self.btn_reload.setProperty("class", "settings-btn")
        self.btn_reload.setFocusPolicy(Qt.NoFocus)
        self.btn_reload.clicked.connect(self.reload_config)
        header_layout.addWidget(self.btn_reload)

        root_layout.addLayout(header_layout)

        # 2. Сетка секций конфигурации
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFocusPolicy(Qt.NoFocus)

        scroll_content = QWidget()
        scroll_content.setFocusPolicy(Qt.NoFocus)
        grid = QGridLayout(scroll_content)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        # Секция 1: Дисплей
        card_display = self._create_card(
            "Экран и геометрия",
            [
                ("Индекс экрана:", f"{self.config.display.screen_index}", "screen_idx"),
                ("Разрешение:", f"{self.config.display.width}x{self.config.display.height} px", "resolution"),
                ("Целевой FPS:", f"{self.config.display.target_fps} fps", "target_fps"),
                ("Fallback окно:", f"{self.config.display.fallback_geometry}", "geometry"),
            ],
        )
        grid.addWidget(card_display, 0, 0)

        # Секция 2: Слой затемнения (Диммер)
        card_dimmer = self._create_card(
            "Диммер и ночной режим",
            [
                ("Начальная яркость:", f"{int(self.config.dimmer.default_opacity * 100)}%", "dimmer_default"),
                ("Ночной режим:", f"{int(self.config.dimmer.night_mode_opacity * 100)}%", "dimmer_night"),
                ("Шаг изменения:", f"{self.config.dimmer.step:.2f}", "dimmer_step"),
            ],
        )
        grid.addWidget(card_dimmer, 0, 1)

        # Секция 3: Защита фокуса (Stealth Focus)
        card_stealth = self._create_card(
            "Защита фокуса (Stealth)",
            [
                ("WS_EX_NOACTIVATE:", "Включен" if self.config.stealth.enable_stealth_focus else "Отключен", "stealth_enabled"),
                ("Anti-Cursor Warp:", "Включен" if self.config.stealth.anti_cursor_warp else "Отключен", "warp_enabled"),
                ("Задержка фокуса:", f"{self.config.stealth.focus_restore_delay_ms} мс", "focus_delay"),
                ("Задержка курсора:", f"{self.config.stealth.cursor_restore_delay_ms} мс", "cursor_delay"),
            ],
        )
        grid.addWidget(card_stealth, 1, 0)

        # Секция 4: Макет рабочей области
        card_layout = self._create_card(
            "Макет и элементы",
            [
                ("Ширина сайдбара:", f"{self.config.layout.sidebar_width} px", "sidebar_width"),
                ("Рабочая область:", f"{self.config.layout.workspace_width} px", "workspace_width"),
                ("Размер тач-кнопок:", f"{self.config.layout.button_size}x{self.config.layout.button_size} px", "btn_size"),
                ("Радиус скругления:", f"{self.config.layout.corner_radius} px", "corner_radius"),
            ],
        )
        grid.addWidget(card_layout, 1, 1)

        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area)

    def _create_card(self, title: str, rows: list[tuple[str, str, str]]) -> QFrame:
        card = QFrame()
        card.setProperty("class", "settings-card")
        card.setFocusPolicy(Qt.NoFocus)

        vbox = QVBoxLayout(card)
        vbox.setSpacing(6)
        vbox.setContentsMargins(12, 12, 12, 12)

        lbl_header = QLabel(title)
        lbl_header.setProperty("class", "section-header")
        lbl_header.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(lbl_header)

        for label_text, value_text, key in rows:
            hbox = QHBoxLayout()
            lbl_key = QLabel(label_text)
            lbl_key.setProperty("class", "field-label")
            lbl_key.setFocusPolicy(Qt.NoFocus)

            lbl_val = QLabel(value_text)
            lbl_val.setProperty("class", "field-value")
            lbl_val.setFocusPolicy(Qt.NoFocus)
            self._labels[key] = lbl_val

            hbox.addWidget(lbl_key)
            hbox.addStretch()
            hbox.addWidget(lbl_val)
            vbox.addLayout(hbox)

        return card

    def reload_config(self) -> None:
        """Перезагрузить конфигурацию из файла и обновить текстовые метки."""
        self.config = load_config(self.config_path)
        self._update_ui_values()

    def _update_ui_values(self) -> None:
        """Синхронизировать отображаемые значения интерфейса с текущим объектом config."""
        if "screen_idx" in self._labels:
            self._labels["screen_idx"].setText(f"{self.config.display.screen_index}")
        if "resolution" in self._labels:
            self._labels["resolution"].setText(f"{self.config.display.width}x{self.config.display.height} px")
        if "target_fps" in self._labels:
            self._labels["target_fps"].setText(f"{self.config.display.target_fps} fps")
        if "geometry" in self._labels:
            self._labels["geometry"].setText(f"{self.config.display.fallback_geometry}")

        if "dimmer_default" in self._labels:
            self._labels["dimmer_default"].setText(f"{int(self.config.dimmer.default_opacity * 100)}%")
        if "dimmer_night" in self._labels:
            self._labels["dimmer_night"].setText(f"{int(self.config.dimmer.night_mode_opacity * 100)}%")
        if "dimmer_step" in self._labels:
            self._labels["dimmer_step"].setText(f"{self.config.dimmer.step:.2f}")

        if "stealth_enabled" in self._labels:
            self._labels["stealth_enabled"].setText("Включен" if self.config.stealth.enable_stealth_focus else "Отключен")
        if "warp_enabled" in self._labels:
            self._labels["warp_enabled"].setText("Включен" if self.config.stealth.anti_cursor_warp else "Отключен")
        if "focus_delay" in self._labels:
            self._labels["focus_delay"].setText(f"{self.config.stealth.focus_restore_delay_ms} мс")
        if "cursor_delay" in self._labels:
            self._labels["cursor_delay"].setText(f"{self.config.stealth.cursor_restore_delay_ms} мс")

        if "sidebar_width" in self._labels:
            self._labels["sidebar_width"].setText(f"{self.config.layout.sidebar_width} px")
        if "workspace_width" in self._labels:
            self._labels["workspace_width"].setText(f"{self.config.layout.workspace_width} px")
        if "btn_size" in self._labels:
            self._labels["btn_size"].setText(f"{self.config.layout.button_size}x{self.config.layout.button_size} px")
        if "corner_radius" in self._labels:
            self._labels["corner_radius"].setText(f"{self.config.layout.corner_radius} px")

    def cleanup(self) -> None:
        """Очистка ресурсов и отписка от событий при закрытии модуля."""
        pass


__all__ = ["SettingsView", "SETTINGS_QSS"]
