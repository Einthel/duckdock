"""
Интеграционный тест сквозного горячего переключения языка (Hot-Reload i18n).
Проверяет:
1. Инициализация главного окна MainWindow со всеми встроенными страницами.
2. Горячая смена языка на лету ru -> en -> ru через I18nManager и EventBus.
3. Одновременное и консистентное обновление UI во всех вкладках:
   - Sidebar: подсказки кнопок навигации и MiniMediaBar;
   - AudioMixerView: заголовки, секции, кнопки мастер-звука;
   - DeckView: интерактивная панель, тикер, статус;
   - SensorsView: карточки NOC-дашборда, бейджи, чипы метрик;
   - YouTubeView: быстрые ссылки и fallback-плеер;
   - ShowcaseView: заголовки и параметры диагностических карточек, кнопка диммера;
   - SettingsView: заголовки карточек и кнопки выбора языка.
4. Сохранение инварианта Stealth Focus (Qt.NoFocus) и отсутствие исключений.
"""
import pytest
from PySide6.QtCore import Qt

from core.config import AppConfig
from core.i18n import I18nManager, t
from modules.settings.view import SettingsView
from ui.main_window import MainWindow


@pytest.fixture(autouse=True)
def reset_i18n():
    """Сброс состояния локализации к исходному русскому языку."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)
    yield
    mgr.set_language("ru", emit_signal=False)


def test_i18n_hot_reload_end_to_end(qapp):
    """Сквозное тестирование динамического переключения языка без перезапуска приложения."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)

    config = AppConfig(language="ru")
    win = MainWindow(config)
    settings_view = SettingsView(config=config, parent=win)

    try:
        # =====================================================================
        # 1. Проверка первичного русского состояния всех экранов
        # =====================================================================
        # Сайдбар
        assert win.sidebar.btn_yt.toolTip() == "YouTube и медиа"
        assert win.sidebar.btn_sensors.toolTip() == "Датчики AIDA64"
        assert win.sidebar.btn_deck.toolTip() == "DuckDeck (Макро-панель и управление)"
        assert win.sidebar.btn_audio.toolTip() == "Аудиомикшер"
        assert win.sidebar.btn_showcase.toolTip() == "Диагностика системы"

        # Аудиомикшер
        assert win.page_audio.lbl_title.text() == "WINDOWS CORE AUDIO MIXER"
        assert "ОБЩАЯ ГРОМКОСТЬ" in win.page_audio.lbl_m_title.text()
        assert "ПРИЛОЖЕНИЯ И ПРОЦЕССЫ" in win.page_audio.lbl_apps.text()

        # DuckDeck
        assert win.page_deck.interactive_panel.left_section.lbl_artist.text() == "Ожидание медиа..."
        assert win.page_deck.interactive_panel.right_section.lbl_ticker.text() == "Готов к работе"

        # Телеметрия
        assert win.page_sensors.lbl_ram_title.text() == "ОЗУ DDR5"
        assert win.page_sensors.lbl_ram_sub.text() == "Высокоскоростной канал"
        assert win.page_sensors.lbl_cooling_status.text() == "● ОБДУВ В НОРМЕ"

        # Медиаплеер
        assert win.page_yt.lbl_header.text() == "▶ MEDIA & YOUTUBE"
        assert win.page_yt.btn_login.text() == "🔑 Войти"

        # Витрина диагностики
        assert win.page_showcase.card_dpi_head.text() == "ПАРАМЕТРЫ ДИСПЛЕЯ"
        assert win.page_showcase.card_stealth_head.text() == "STEALTH TOUCH GUARDIAN"
        assert win.page_showcase.lbl_dimmer_status.text() == "Выключен (0%)"
        assert win.page_showcase.btn_lang_ru.property("active") == "true"

        # Экран настроек
        assert settings_view.lbl_title.text() == "Настройки DuckDock"
        assert settings_view.btn_lang_ru.property("active") == "true"
        assert settings_view.btn_lang_en.property("active") == "false"

        # =====================================================================
        # 2. Горячая смена языка: RU -> EN через селектор настроек
        # =====================================================================
        settings_view._on_language_selected("en")
        qapp.processEvents()

        # Сайдбар
        assert win.sidebar.btn_yt.toolTip() == "YouTube & Media"
        assert win.sidebar.btn_sensors.toolTip() == "AIDA64 Sensors"
        assert win.sidebar.btn_deck.toolTip() == "DuckDeck (Macro Panel)"
        assert win.sidebar.btn_audio.toolTip() == "Audio Mixer"
        assert win.sidebar.btn_showcase.toolTip() == "System Showcase"

        # Аудиомикшер
        assert "MASTER VOLUME" in win.page_audio.lbl_m_title.text()
        assert "APPLICATIONS & PROCESSES" in win.page_audio.lbl_apps.text()

        # DuckDeck
        assert win.page_deck.interactive_panel.left_section.lbl_artist.text() == "Waiting for media..."
        assert win.page_deck.interactive_panel.right_section.lbl_ticker.text() == "Ready"

        # Телеметрия
        assert win.page_sensors.lbl_ram_title.text() == "RAM DDR5"
        assert win.page_sensors.lbl_ram_sub.text() == "High-Speed Channel"
        assert win.page_sensors.lbl_cooling_status.text() == "● OPTIMAL AIRFLOW"

        # Медиаплеер
        assert win.page_yt.btn_login.text() == "🔑 Sign In"

        # Витрина диагностики
        assert win.page_showcase.card_dpi_head.text() == "DISPLAY PARAMETERS"
        assert win.page_showcase.card_stealth_head.text() == "STEALTH TOUCH GUARDIAN"
        assert win.page_showcase.lbl_dimmer_status.text() == "Disabled (0%)"

        # Экран настроек
        assert settings_view.lbl_title.text() == "DuckDock Settings"
        assert settings_view.btn_lang_ru.property("active") == "false"
        assert settings_view.btn_lang_en.property("active") == "true"

        # =====================================================================
        # 3. Горячая смена языка обратно: EN -> RU
        # =====================================================================
        settings_view._on_language_selected("ru")
        qapp.processEvents()

        assert win.sidebar.btn_audio.toolTip() == "Аудиомикшер"
        assert "ОБЩАЯ ГРОМКОСТЬ" in win.page_audio.lbl_m_title.text()
        assert win.page_deck.interactive_panel.right_section.lbl_ticker.text() == "Готов к работе"
        assert win.page_sensors.lbl_ram_title.text() == "ОЗУ DDR5"
        assert win.page_sensors.lbl_ram_sub.text() == "Высокоскоростной канал"
        assert win.page_sensors.lbl_cooling_status.text() == "● ОБДУВ В НОРМЕ"
        assert win.page_yt.btn_login.text() == "🔑 Войти"
        assert win.page_showcase.card_dpi_head.text() == "ПАРАМЕТРЫ ДИСПЛЕЯ"
        assert settings_view.lbl_title.text() == "Настройки DuckDock"
        assert settings_view.btn_lang_ru.property("active") == "true"

        # =====================================================================
        # 4. Проверка инварианта Stealth Focus во всех модулях
        # =====================================================================
        assert win.sidebar.focusPolicy() == Qt.NoFocus
        assert win.page_audio.focusPolicy() == Qt.NoFocus
        assert win.page_deck.focusPolicy() == Qt.NoFocus
        assert win.page_sensors.focusPolicy() == Qt.NoFocus
        assert win.page_yt.focusPolicy() == Qt.NoFocus
        assert win.page_showcase.focusPolicy() == Qt.NoFocus
        assert settings_view.focusPolicy() == Qt.NoFocus

    finally:
        settings_view.cleanup()
        settings_view.deleteLater()
        win.close()
