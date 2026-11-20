"""
Тесты интернационализации витрины диагностики (ShowcaseView).
"""
import pytest
from PySide6.QtCore import Qt

from core.event_bus import bus
from core.i18n import I18nManager, t
from core.ui_base import TouchModuleView
from ui.showcase_view import ShowcaseView


@pytest.fixture(autouse=True)
def reset_i18n():
    """Гарантирует возврат к русскому языку после каждого теста."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)
    yield
    mgr.set_language("ru", emit_signal=False)


def test_showcase_view_stealth_focus_and_touch_module_view(qapp):
    """Проверка наследования от TouchModuleView и инварианта Stealth Focus."""
    view = ShowcaseView()
    try:
        assert isinstance(view, TouchModuleView)
        assert view.focusPolicy() == Qt.NoFocus
        assert view.btn_test_dimmer.focusPolicy() == Qt.NoFocus
        assert view.btn_lang_ru.focusPolicy() == Qt.NoFocus
        assert view.btn_lang_en.focusPolicy() == Qt.NoFocus
    finally:
        view.cleanup()
        view.deleteLater()


def test_showcase_view_retranslate_ui(qapp):
    """Проверка горячей смены языка во всех карточках диагностики и диммере."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)

    view = ShowcaseView()
    try:
        # 1. Русский язык
        assert view.card_dpi_head.text() == "ПАРАМЕТРЫ ДИСПЛЕЯ"
        assert view.card_stealth_head.text() == "STEALTH TOUCH GUARDIAN"
        assert view.card_tiling_head.text() == "BORDERLESS TILING (720x600)"
        assert view.card_services_head.text() == "СЕРВИСНЫЕ ФУНКЦИИ (QoL)"
        assert view.btn_test_dimmer.text() == "🌙 Включить ночной режим (Диммер)"
        assert view.lbl_dimmer_status.text() == "Выключен (0%)"
        assert view.lbl_lang_head.text() == "Язык интерфейса"
        assert view.btn_lang_ru.text() == "Русский"
        assert view.btn_lang_en.text() == "English"
        assert view.btn_lang_ru.property("active") == "true"
        assert view.btn_lang_en.property("active") == "false"

        # Включаем диммер на 50%
        bus.dimmer_opacity_changed.emit(0.5)
        assert view.btn_test_dimmer.text() == "☀️ Выключить затемнение (50%)"
        assert view.lbl_dimmer_status.text() == "Активен (50%)"

        # 2. Горячая смена на английский
        mgr.set_language("en")
        # TouchModuleView автоматически вызывает retranslate_ui()

        assert view.card_dpi_head.text() == "DISPLAY PARAMETERS"
        assert view.card_stealth_head.text() == "STEALTH TOUCH GUARDIAN"
        assert view.card_tiling_head.text() == "BORDERLESS TILING (720x600)"
        assert view.card_services_head.text() == "SERVICE FUNCTIONS (QoL)"
        assert view.lbl_dpi_res_key.text() == "Resolution:"
        assert view.val_dpi_res.text() == "800 x 600 px (4:3)"
        assert view.btn_test_dimmer.text() == "☀️ Disable Dimmer (50%)"
        assert view.lbl_dimmer_status.text() == "Active (50%)"

        # Выключаем диммер
        bus.dimmer_opacity_changed.emit(0.0)
        assert view.btn_test_dimmer.text() == "🌙 Enable Night Mode (Dimmer)"
        assert view.lbl_dimmer_status.text() == "Disabled (0%)"
        assert view.lbl_lang_head.text() == "Interface Language"
        assert view.btn_lang_ru.property("active") == "false"
        assert view.btn_lang_en.property("active") == "true"

        # 3. Интерактивное переключение через кнопку ShowcaseView
        view._on_language_selected("ru")
        assert mgr.current_language == "ru"
        assert view.card_dpi_head.text() == "ПАРАМЕТРЫ ДИСПЛЕЯ"
        assert view.lbl_dpi_res_key.text() == "Разрешение:"
        assert view.btn_test_dimmer.text() == "🌙 Включить ночной режим (Диммер)"
        assert view.lbl_dimmer_status.text() == "Выключен (0%)"
        assert view.btn_lang_ru.property("active") == "true"
        assert view.btn_lang_en.property("active") == "false"
    finally:
        bus.dimmer_opacity_changed.emit(0.0)
        view.cleanup()
        view.deleteLater()
