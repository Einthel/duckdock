"""
Панель системной диагностики и витрина компонентов (Showcase View).
Позволяет в реальном времени отслеживать состояние WinAPI хуков,
координаты дисплеев и работу защитника фокуса.
Наследуется от TouchModuleView (Qt.NoFocus, авто-локализация).
"""
from typing import List, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt

from core.event_bus import bus
from core.i18n import I18nManager, t
from core.ui_base import TouchModuleView
from modules.settings.config import AppConfig, load_config, save_config

SHOWCASE_QSS = """
QFrame.diag-card {
    background-color: #161b26;
    border: 1px solid #232b3e;
    border-radius: 12px;
    padding: 14px;
}

QLabel.diag-label {
    color: #94a3b8;
    font-size: 13px;
}

QLabel.diag-value {
    color: #38bdf8;
    font-size: 14px;
    font-weight: bold;
}

QPushButton.test-btn {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: bold;
}

QPushButton.test-btn:hover {
    background-color: #3b82f6;
}

QPushButton.lang-btn {
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
    font-size: 13px;
    min-height: 42px;
    min-width: 140px;
}

QPushButton.lang-btn:hover {
    background-color: #2563eb;
    color: #ffffff;
    border-color: #60a5fa;
}

QPushButton.lang-btn[active="true"] {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #60a5fa;
}
"""


class ShowcaseView(TouchModuleView):
    """Экран статуса подсистем DuckDock."""

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config if config is not None else load_config()
        self._current_opacity = 0.0
        self.lbl_dimmer_status: QLabel = None
        self.setStyleSheet(SHOWCASE_QSS)
        self._init_ui()
        bus.dimmer_opacity_changed.connect(self._on_dimmer_opacity_changed)

    def _on_dimmer_opacity_changed(self, opacity: float):
        self._current_opacity = opacity
        pct = int(opacity * 100)
        if opacity > 0.05:
            self.btn_test_dimmer.setText(t("showcase.dimmer.disable_btn", percent=pct))
            self.btn_test_dimmer.setStyleSheet("background-color: #f59e0b; color: #000000;")
            if self.lbl_dimmer_status:
                self.lbl_dimmer_status.setText(t("showcase.dimmer.active_status", percent=pct))
                self.lbl_dimmer_status.setStyleSheet("color: #f59e0b; font-size: 14px; font-weight: bold;")
        else:
            self.btn_test_dimmer.setText(t("showcase.dimmer.enable_btn"))
            self.btn_test_dimmer.setStyleSheet("")
            if self.lbl_dimmer_status:
                self.lbl_dimmer_status.setText(t("showcase.dimmer.inactive_status"))
                self.lbl_dimmer_status.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: bold;")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.lbl_title = QLabel(t("showcase.title"))
        self.lbl_title.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: bold;")
        layout.addWidget(self.lbl_title)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Карточка 1: Дисплей и DPI
        card_dpi, self.card_dpi_head, self.lbl_dpi_res_key, self.val_dpi_res, self.lbl_dpi_aware_key, self.val_dpi_aware, self.lbl_dpi_render_key, self.val_dpi_render = self._create_card_dpi()
        grid.addWidget(card_dpi, 0, 0)

        # Карточка 2: Stealth Focus
        card_focus, self.card_stealth_head, self.lbl_stealth_ws_key, self.val_stealth_ws, self.lbl_stealth_warp_key, self.val_stealth_warp, self.lbl_stealth_restore_key, self.val_stealth_restore = self._create_card_stealth()
        grid.addWidget(card_focus, 0, 1)

        # Карточка 3: Менеджер сторонних окон
        card_wm, self.card_tiling_head, self.lbl_tiling_zone_key, self.val_tiling_zone, self.lbl_tiling_frame_key, self.val_tiling_frame, self.lbl_tiling_target_key, self.val_tiling_target = self._create_card_tiling()
        grid.addWidget(card_wm, 1, 0)

        # Карточка 4: Сервисные функции
        card_qol, self.card_services_head, self.lbl_services_dimmer_key, self.val_services_dimmer, self.lbl_services_barrier_key, self.val_services_barrier, self.lbl_services_hotplug_key, self.val_services_hotplug = self._create_card_services()
        self.lbl_dimmer_status = self.val_services_dimmer
        grid.addWidget(card_qol, 1, 1)

        layout.addLayout(grid)

        # Интерактивные тесты
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_test_dimmer = QPushButton(t("showcase.dimmer.enable_btn"))
        self.btn_test_dimmer.setProperty("class", "test-btn")
        self.btn_test_dimmer.setFocusPolicy(Qt.NoFocus)
        self.btn_test_dimmer.clicked.connect(lambda: bus.dimmer_toggle_requested.emit())
        btn_layout.addWidget(self.btn_test_dimmer)

        layout.addLayout(btn_layout)

        # Карточка 5: Выбор языка интерфейса
        card_lang = self._create_language_card()
        layout.addWidget(card_lang)
        layout.addStretch()

        self.retranslate_ui()

    def _create_language_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "diag-card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        self.lbl_lang_head = QLabel()
        self.lbl_lang_head.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.lbl_lang_head.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.lbl_lang_head)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_lang_ru = QPushButton()
        self.btn_lang_ru.setProperty("class", "lang-btn")
        self.btn_lang_ru.setFocusPolicy(Qt.NoFocus)
        self.btn_lang_ru.clicked.connect(lambda: self._on_language_selected("ru"))

        self.btn_lang_en = QPushButton()
        self.btn_lang_en.setProperty("class", "lang-btn")
        self.btn_lang_en.setFocusPolicy(Qt.NoFocus)
        self.btn_lang_en.clicked.connect(lambda: self._on_language_selected("en"))

        btn_layout.addWidget(self.btn_lang_ru)
        btn_layout.addWidget(self.btn_lang_en)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        return card

    def _on_language_selected(self, lang_code: str) -> None:
        mgr = I18nManager()
        if mgr.current_language == lang_code:
            return
        if self.config:
            self.config.language = lang_code
            save_config(self.config)
        mgr.set_language(lang_code, emit_signal=True)
        self._update_language_buttons()

    def _update_language_buttons(self) -> None:
        if hasattr(self, "btn_lang_ru") and hasattr(self, "btn_lang_en"):
            curr = I18nManager().current_language
            is_ru = curr == "ru"
            self.btn_lang_ru.setProperty("active", "true" if is_ru else "false")
            self.btn_lang_en.setProperty("active", "true" if not is_ru else "false")
            if self.btn_lang_ru.style():
                self.btn_lang_ru.style().unpolish(self.btn_lang_ru)
                self.btn_lang_ru.style().polish(self.btn_lang_ru)
            if self.btn_lang_en.style():
                self.btn_lang_en.style().unpolish(self.btn_lang_en)
                self.btn_lang_en.style().polish(self.btn_lang_en)

    def _create_card_dpi(self):
        card = QFrame()
        card.setProperty("class", "diag-card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        head = QLabel(t("showcase.cards.display"))
        head.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        layout.addWidget(head)

        k1, v1 = self._add_row(layout, t("showcase.display.resolution"), t("showcase.display.resolution_val"))
        k2, v2 = self._add_row(layout, t("showcase.display.dpi_awareness"), t("showcase.display.dpi_val"))
        k3, v3 = self._add_row(layout, t("showcase.display.rendering"), t("showcase.display.rendering_val"))
        return card, head, k1, v1, k2, v2, k3, v3

    def _create_card_stealth(self):
        card = QFrame()
        card.setProperty("class", "diag-card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        head = QLabel(t("showcase.cards.stealth"))
        head.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        layout.addWidget(head)

        k1, v1 = self._add_row(layout, t("showcase.stealth.ws_noactivate"), t("showcase.stealth.ws_noactivate_val"))
        k2, v2 = self._add_row(layout, t("showcase.stealth.anti_cursor_warp"), t("showcase.stealth.anti_cursor_warp_val"))
        k3, v3 = self._add_row(layout, t("showcase.stealth.focus_restore"), t("showcase.stealth.focus_restore_val"))
        return card, head, k1, v1, k2, v2, k3, v3

    def _create_card_tiling(self):
        card = QFrame()
        card.setProperty("class", "diag-card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        head = QLabel(t("showcase.cards.tiling"))
        head.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        layout.addWidget(head)

        k1, v1 = self._add_row(layout, t("showcase.tiling.tiling_zone"), t("showcase.tiling.tiling_zone_val"))
        k2, v2 = self._add_row(layout, t("showcase.tiling.frame_cutting"), t("showcase.tiling.frame_cutting_val"))
        k3, v3 = self._add_row(layout, t("showcase.tiling.target_process"), t("showcase.tiling.target_process_val"))
        return card, head, k1, v1, k2, v2, k3, v3

    def _create_card_services(self):
        card = QFrame()
        card.setProperty("class", "diag-card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        head = QLabel(t("showcase.cards.services"))
        head.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        layout.addWidget(head)

        k1, v1 = self._add_row(layout, t("showcase.services.dimmer"), t("showcase.dimmer.inactive_status"))
        k2, v2 = self._add_row(layout, t("showcase.services.mouse_barrier"), t("showcase.services.mouse_barrier_val"))
        k3, v3 = self._add_row(layout, t("showcase.services.hotplug"), t("showcase.services.hotplug_val"))
        return card, head, k1, v1, k2, v2, k3, v3

    def _add_row(self, layout: QVBoxLayout, label_text: str, val_text: str) -> Tuple[QLabel, QLabel]:
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setProperty("class", "diag-label")
        val = QLabel(val_text)
        val.setProperty("class", "diag-value")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)
        return lbl, val

    def retranslate_ui(self) -> None:
        """Обновление всех текстов витрины диагностики."""
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText(t("showcase.title"))
        # Card 1
        if hasattr(self, "card_dpi_head"):
            self.card_dpi_head.setText(t("showcase.cards.display"))
            self.lbl_dpi_res_key.setText(t("showcase.display.resolution"))
            self.val_dpi_res.setText(t("showcase.display.resolution_val"))
            self.lbl_dpi_aware_key.setText(t("showcase.display.dpi_awareness"))
            self.val_dpi_aware.setText(t("showcase.display.dpi_val"))
            self.lbl_dpi_render_key.setText(t("showcase.display.rendering"))
            self.val_dpi_render.setText(t("showcase.display.rendering_val"))
        # Card 2
        if hasattr(self, "card_stealth_head"):
            self.card_stealth_head.setText(t("showcase.cards.stealth"))
            self.lbl_stealth_ws_key.setText(t("showcase.stealth.ws_noactivate"))
            self.val_stealth_ws.setText(t("showcase.stealth.ws_noactivate_val"))
            self.lbl_stealth_warp_key.setText(t("showcase.stealth.anti_cursor_warp"))
            self.val_stealth_warp.setText(t("showcase.stealth.anti_cursor_warp_val"))
            self.lbl_stealth_restore_key.setText(t("showcase.stealth.focus_restore"))
            self.val_stealth_restore.setText(t("showcase.stealth.focus_restore_val"))
        # Card 3
        if hasattr(self, "card_tiling_head"):
            self.card_tiling_head.setText(t("showcase.cards.tiling"))
            self.lbl_tiling_zone_key.setText(t("showcase.tiling.tiling_zone"))
            self.val_tiling_zone.setText(t("showcase.tiling.tiling_zone_val"))
            self.lbl_tiling_frame_key.setText(t("showcase.tiling.frame_cutting"))
            self.val_tiling_frame.setText(t("showcase.tiling.frame_cutting_val"))
            self.lbl_tiling_target_key.setText(t("showcase.tiling.target_process"))
            self.val_tiling_target.setText(t("showcase.tiling.target_process_val"))
        # Card 4
        if hasattr(self, "card_services_head"):
            self.card_services_head.setText(t("showcase.cards.services"))
            self.lbl_services_dimmer_key.setText(t("showcase.services.dimmer"))
            self.lbl_services_barrier_key.setText(t("showcase.services.mouse_barrier"))
            self.val_services_barrier.setText(t("showcase.services.mouse_barrier_val"))
            self.lbl_services_hotplug_key.setText(t("showcase.services.hotplug"))
            self.val_services_hotplug.setText(t("showcase.services.hotplug_val"))
        # Dimmer button & status
        if hasattr(self, "btn_test_dimmer"):
            self._on_dimmer_opacity_changed(getattr(self, "_current_opacity", 0.0))
        # Language card
        if hasattr(self, "lbl_lang_head"):
            self.lbl_lang_head.setText(t("settings.language.title"))
        if hasattr(self, "btn_lang_ru"):
            self.btn_lang_ru.setText(t("settings.language.ru"))
        if hasattr(self, "btn_lang_en"):
            self.btn_lang_en.setText(t("settings.language.en"))
        self._update_language_buttons()

    def cleanup(self) -> None:
        try:
            bus.dimmer_opacity_changed.disconnect(self._on_dimmer_opacity_changed)
        except Exception:
            pass
        super().cleanup()
