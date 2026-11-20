"""
Сенсорный экран настроек DuckDock / TouchWM (SettingsView).
Размещается в рабочей области 944x600.
Обеспечивает просмотр и конфигурирование параметров экрана, диммера,
защиты фокуса (Stealth Focus), системных интеграций и выбора языка интерфейса.
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

from core.i18n import I18nManager, t
from core.ui_base import TouchModuleView
from modules.settings.config import AppConfig, load_config, save_config

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

QPushButton.settings-lang-btn {
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    min-height: 44px;
}

QPushButton.settings-lang-btn:hover {
    background-color: #334155;
    color: #f8fafc;
}

QPushButton.settings-lang-btn[active="true"] {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #60a5fa;
}

QPushButton.settings-lang-btn[active="true"]:hover {
    background-color: #1d4ed8;
}

QPushButton.settings-lang-btn:pressed {
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
    Поддерживает сенсорное переключение языка RU/EN и прямое обновление текстов через retranslate_ui().
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

    def _make_field_label(self) -> QLabel:
        lbl = QLabel()
        lbl.setProperty("class", "field-label")
        lbl.setFocusPolicy(Qt.NoFocus)
        return lbl

    def _add_field_row(self, vbox: QVBoxLayout, lbl_field: QLabel, key: str) -> QLabel:
        hbox = QHBoxLayout()
        lbl_val = QLabel()
        lbl_val.setProperty("class", "field-value")
        lbl_val.setFocusPolicy(Qt.NoFocus)
        self._labels[key] = lbl_val

        hbox.addWidget(lbl_field)
        hbox.addStretch()
        hbox.addWidget(lbl_val)
        vbox.addLayout(hbox)
        return lbl_val

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # 1. Заголовок экрана
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(2)

        self.lbl_title = QLabel()
        self.lbl_title.setProperty("class", "title-label")
        self.lbl_title.setFocusPolicy(Qt.NoFocus)

        self.lbl_sub = QLabel()
        self.lbl_sub.setProperty("class", "subtitle-label")
        self.lbl_sub.setFocusPolicy(Qt.NoFocus)

        header_text_layout.addWidget(self.lbl_title)
        header_text_layout.addWidget(self.lbl_sub)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        self.btn_reload = QPushButton()
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
        card_display = self._create_display_card()
        grid.addWidget(card_display, 0, 0)

        # Секция 2: Слой затемнения (Диммер)
        card_dimmer = self._create_dimmer_card()
        grid.addWidget(card_dimmer, 0, 1)

        # Секция 3: Защита фокуса (Stealth Focus)
        card_stealth = self._create_stealth_card()
        grid.addWidget(card_stealth, 1, 0)

        # Секция 4: Макет рабочей области
        card_layout = self._create_layout_card()
        grid.addWidget(card_layout, 1, 1)

        # Секция 5: Селектор языка интерфейса (RU / EN)
        card_language = self._create_language_card()
        grid.addWidget(card_language, 2, 0, 1, 2)

        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area)

        # Первичное заполнение всех текстов через i18n
        self.retranslate_ui()

    def _create_display_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "settings-card")
        card.setFocusPolicy(Qt.NoFocus)

        vbox = QVBoxLayout(card)
        vbox.setSpacing(6)
        vbox.setContentsMargins(12, 12, 12, 12)

        self.lbl_display_header = QLabel()
        self.lbl_display_header.setProperty("class", "section-header")
        self.lbl_display_header.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(self.lbl_display_header)

        self.lbl_field_screen_idx = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_screen_idx, "screen_idx")

        self.lbl_field_resolution = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_resolution, "resolution")

        self.lbl_field_target_fps = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_target_fps, "target_fps")

        self.lbl_field_geometry = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_geometry, "geometry")

        return card

    def _create_dimmer_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "settings-card")
        card.setFocusPolicy(Qt.NoFocus)

        vbox = QVBoxLayout(card)
        vbox.setSpacing(6)
        vbox.setContentsMargins(12, 12, 12, 12)

        self.lbl_dimmer_header = QLabel()
        self.lbl_dimmer_header.setProperty("class", "section-header")
        self.lbl_dimmer_header.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(self.lbl_dimmer_header)

        self.lbl_field_dimmer_default = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_dimmer_default, "dimmer_default")

        self.lbl_field_dimmer_night = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_dimmer_night, "dimmer_night")

        self.lbl_field_dimmer_step = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_dimmer_step, "dimmer_step")

        return card

    def _create_stealth_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "settings-card")
        card.setFocusPolicy(Qt.NoFocus)

        vbox = QVBoxLayout(card)
        vbox.setSpacing(6)
        vbox.setContentsMargins(12, 12, 12, 12)

        self.lbl_stealth_header = QLabel()
        self.lbl_stealth_header.setProperty("class", "section-header")
        self.lbl_stealth_header.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(self.lbl_stealth_header)

        self.lbl_field_ws_noactivate = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_ws_noactivate, "stealth_enabled")

        self.lbl_field_anti_warp = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_anti_warp, "warp_enabled")

        self.lbl_field_focus_delay = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_focus_delay, "focus_delay")

        self.lbl_field_cursor_delay = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_cursor_delay, "cursor_delay")

        return card

    def _create_layout_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "settings-card")
        card.setFocusPolicy(Qt.NoFocus)

        vbox = QVBoxLayout(card)
        vbox.setSpacing(6)
        vbox.setContentsMargins(12, 12, 12, 12)

        self.lbl_layout_header = QLabel()
        self.lbl_layout_header.setProperty("class", "section-header")
        self.lbl_layout_header.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(self.lbl_layout_header)

        self.lbl_field_sidebar_width = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_sidebar_width, "sidebar_width")

        self.lbl_field_workspace_width = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_workspace_width, "workspace_width")

        self.lbl_field_btn_size = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_btn_size, "btn_size")

        self.lbl_field_corner_radius = self._make_field_label()
        self._add_field_row(vbox, self.lbl_field_corner_radius, "corner_radius")

        return card

    def _create_language_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "settings-card")
        card.setFocusPolicy(Qt.NoFocus)

        vbox = QVBoxLayout(card)
        vbox.setSpacing(8)
        vbox.setContentsMargins(12, 12, 12, 12)

        self.lbl_lang_header = QLabel()
        self.lbl_lang_header.setProperty("class", "section-header")
        self.lbl_lang_header.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(self.lbl_lang_header)

        self.lbl_lang_desc = QLabel()
        self.lbl_lang_desc.setProperty("class", "field-label")
        self.lbl_lang_desc.setFocusPolicy(Qt.NoFocus)
        vbox.addWidget(self.lbl_lang_desc)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_lang_ru = QPushButton()
        self.btn_lang_ru.setProperty("class", "settings-lang-btn")
        self.btn_lang_ru.setFocusPolicy(Qt.NoFocus)
        self.btn_lang_ru.setMinimumHeight(44)
        self.btn_lang_ru.setMinimumWidth(120)
        self.btn_lang_ru.clicked.connect(lambda: self._on_language_selected("ru"))

        self.btn_lang_en = QPushButton()
        self.btn_lang_en.setProperty("class", "settings-lang-btn")
        self.btn_lang_en.setFocusPolicy(Qt.NoFocus)
        self.btn_lang_en.setMinimumHeight(44)
        self.btn_lang_en.setMinimumWidth(120)
        self.btn_lang_en.clicked.connect(lambda: self._on_language_selected("en"))

        btn_layout.addWidget(self.btn_lang_ru)
        btn_layout.addWidget(self.btn_lang_en)
        btn_layout.addStretch()

        vbox.addLayout(btn_layout)
        return card

    def _create_card(self, title: str, rows: list[tuple[str, str, str]]) -> QFrame:
        """Переходный метод создания карточек для обратной совместимости."""
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

    def _on_language_selected(self, lang_code: str) -> None:
        """
        Обработка выбора языка.
        Идемпотентна: при повторном клике на активный язык не производит операций ввода-вывода.
        """
        if self.config.language == lang_code:
            return

        self.config.language = lang_code
        save_config(self.config, self.config_path)
        I18nManager().set_language(lang_code, emit_signal=True)
        self._update_language_buttons()

    def _update_language_buttons(self) -> None:
        """Синхронизировать визуальное состояние кнопок переключения языка."""
        is_ru = self.config.language == "ru"
        self.btn_lang_ru.setProperty("active", "true" if is_ru else "false")
        self.btn_lang_en.setProperty("active", "true" if not is_ru else "false")

        for btn in (self.btn_lang_ru, self.btn_lang_en):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def retranslate_ui(self) -> None:
        """
        Прямое обновление всех текстовых меток интерфейса в соответствии с активным языком.
        Служит единым источником правды для текстов экрана настроек.
        """
        self.lbl_title.setText(t("settings.title"))
        self.lbl_sub.setText(t("settings.subtitle"))
        self.btn_reload.setText(t("settings.actions.reload_json"))

        # Карточка 1: Дисплей
        self.lbl_display_header.setText(t("settings.display.title"))
        self.lbl_field_screen_idx.setText(t("settings.display.screen_index"))
        self.lbl_field_resolution.setText(t("settings.display.resolution"))
        self.lbl_field_target_fps.setText(t("settings.display.target_fps"))
        self.lbl_field_geometry.setText(t("settings.display.fallback_geometry"))

        # Карточка 2: Диммер
        self.lbl_dimmer_header.setText(t("settings.dimmer.title"))
        self.lbl_field_dimmer_default.setText(t("settings.dimmer.default_opacity"))
        self.lbl_field_dimmer_night.setText(t("settings.dimmer.night_mode_opacity"))
        self.lbl_field_dimmer_step.setText(t("settings.dimmer.step"))

        # Карточка 3: Защита фокуса (Stealth)
        self.lbl_stealth_header.setText(t("settings.stealth.title"))
        self.lbl_field_ws_noactivate.setText(t("settings.stealth.ws_noactivate"))
        self.lbl_field_anti_warp.setText(t("settings.stealth.anti_cursor_warp"))
        self.lbl_field_focus_delay.setText(t("settings.stealth.focus_delay"))
        self.lbl_field_cursor_delay.setText(t("settings.stealth.cursor_delay"))

        # Карточка 4: Макет рабочей области
        self.lbl_layout_header.setText(t("settings.layout.title"))
        self.lbl_field_sidebar_width.setText(t("settings.layout.sidebar_width"))
        self.lbl_field_workspace_width.setText(t("settings.layout.workspace_width"))
        self.lbl_field_btn_size.setText(t("settings.layout.button_size"))
        self.lbl_field_corner_radius.setText(t("settings.layout.corner_radius"))

        # Карточка 5: Язык интерфейса
        self.lbl_lang_header.setText(t("settings.language.title"))
        self.lbl_lang_desc.setText(t("settings.language.description"))
        self.btn_lang_ru.setText(t("settings.language.ru"))
        self.btn_lang_en.setText(t("settings.language.en"))

        self._update_ui_values()
        self._update_language_buttons()

    def reload_config(self) -> None:
        """Перезагрузить конфигурацию из файла и обновить текстовые метки."""
        self.config = load_config(self.config_path)
        self._update_ui_values()
        self._update_language_buttons()

    def _update_ui_values(self) -> None:
        """Синхронизировать отображаемые значения интерфейса с текущим объектом config."""
        px_unit = t("common.units.px")
        fps_unit = t("common.units.fps")
        ms_unit = t("common.units.ms")
        enabled_str = t("common.state.enabled")
        disabled_str = t("common.state.disabled")

        if "screen_idx" in self._labels:
            self._labels["screen_idx"].setText(f"{self.config.display.screen_index}")
        if "resolution" in self._labels:
            self._labels["resolution"].setText(f"{self.config.display.width}x{self.config.display.height} {px_unit}")
        if "target_fps" in self._labels:
            self._labels["target_fps"].setText(f"{self.config.display.target_fps} {fps_unit}")
        if "geometry" in self._labels:
            self._labels["geometry"].setText(f"{self.config.display.fallback_geometry}")

        if "dimmer_default" in self._labels:
            self._labels["dimmer_default"].setText(f"{int(self.config.dimmer.default_opacity * 100)}%")
        if "dimmer_night" in self._labels:
            self._labels["dimmer_night"].setText(f"{int(self.config.dimmer.night_mode_opacity * 100)}%")
        if "dimmer_step" in self._labels:
            self._labels["dimmer_step"].setText(f"{self.config.dimmer.step:.2f}")

        if "stealth_enabled" in self._labels:
            self._labels["stealth_enabled"].setText(enabled_str if self.config.stealth.enable_stealth_focus else disabled_str)
        if "warp_enabled" in self._labels:
            self._labels["warp_enabled"].setText(enabled_str if self.config.stealth.anti_cursor_warp else disabled_str)
        if "focus_delay" in self._labels:
            self._labels["focus_delay"].setText(f"{self.config.stealth.focus_restore_delay_ms} {ms_unit}")
        if "cursor_delay" in self._labels:
            self._labels["cursor_delay"].setText(f"{self.config.stealth.cursor_restore_delay_ms} {ms_unit}")

        if "sidebar_width" in self._labels:
            self._labels["sidebar_width"].setText(f"{self.config.layout.sidebar_width} {px_unit}")
        if "workspace_width" in self._labels:
            self._labels["workspace_width"].setText(f"{self.config.layout.workspace_width} {px_unit}")
        if "btn_size" in self._labels:
            self._labels["btn_size"].setText(f"{self.config.layout.button_size}x{self.config.layout.button_size} {px_unit}")
        if "corner_radius" in self._labels:
            self._labels["corner_radius"].setText(f"{self.config.layout.corner_radius} {px_unit}")

    def cleanup(self) -> None:
        """Очистка ресурсов и отписка от событий при закрытии модуля."""
        super().cleanup()


__all__ = ["SettingsView", "SETTINGS_QSS"]
