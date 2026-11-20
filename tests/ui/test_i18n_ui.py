"""
Модульные тесты для интеграции локализации в базовый UI-каркас DuckDock (Фаза 2).
Проверяют:
1. TouchModuleView: автоподписка на bus.language_changed, вызов retranslate_ui, сохранение Stealth Focus (Qt.NoFocus).
2. TouchModuleView: разрыв подписки и предотвращение утечек при cleanup() и destroyed.
3. SidebarDock: динамическое обновление всплывающих подсказок кнопок навигации при смене RU <-> EN без деформации геометрии (80px).
4. SidebarDock: подсказки кнопки блокировки ввода (Stealth Focus vs Interactive) на обоих языках.
5. MiniMediaBar: переключение подсказок кнопок плеера (prev, play/pause, next) и открытие плеера при смене локали.
6. MainWindow: холодный старт с config.language (emit_signal=False), первичный retranslate_ui и динамическое обновление заголовка окна.
"""
from unittest.mock import MagicMock
import pytest
from PySide6.QtCore import Qt

from core.event_bus import bus
from core.i18n import I18nManager, t
from core.ui_base import TouchModuleView
from modules.media.widgets.mini_media_bar import MiniMediaBar
from modules.settings.config import AppConfig
from ui.main_window import MainWindow
from ui.sidebar import SidebarDock


@pytest.fixture(autouse=True)
def reset_i18n_state():
    """Сброс состояния синглтона I18nManager перед каждым тестом."""
    I18nManager._reset_instance()
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)
    yield
    I18nManager._reset_instance()


class DummyTouchView(TouchModuleView):
    """Тестовый наследник TouchModuleView для проверки жизненного цикла локализации."""

    def __init__(self, parent=None):
        self.retranslate_call_count = 0
        self.last_retranslated_lang = None
        super().__init__(parent)

    def retranslate_ui(self):
        self.retranslate_call_count += 1
        self.last_retranslated_lang = I18nManager().current_language


@pytest.mark.unit
def test_touch_module_view_auto_subscription(qapp):
    """
    Проверка реактивной автоподписки TouchModuleView:
    - Конструктор НЕ вызывает retranslate_ui() (защита от AttributeError неинициализированных дочерних виджетов).
    - При смене языка через bus.language_changed вызывается retranslate_ui().
    - Сохраняется инвариант Stealth Focus (Qt.NoFocus).
    """
    view = DummyTouchView()
    try:
        assert view.focusPolicy() == Qt.NoFocus
        # Во время инициализации retranslate_ui не вызывается автоматически
        assert view.retranslate_call_count == 0

        # Переключаем язык на English
        I18nManager().set_language("en")
        assert view.retranslate_call_count == 1
        assert view.last_retranslated_lang == "en"

        # Переключаем обратно на Russian
        I18nManager().set_language("ru")
        assert view.retranslate_call_count == 2
        assert view.last_retranslated_lang == "ru"
    finally:
        view.cleanup()
        view.deleteLater()


@pytest.mark.unit
def test_touch_module_view_cleanup_prevents_leaks(qapp):
    """
    Проверка гарантированного разрыва подписки при cleanup():
    - После вызова cleanup() события шины не должны вызывать retranslate_ui.
    - Повторный вызов cleanup() идемпотентен и безопасен.
    """
    view = DummyTouchView()
    try:
        I18nManager().set_language("en")
        assert view.retranslate_call_count == 1

        # Отключаем через cleanup
        view.cleanup()

        # При последующей смене языка метод НЕ должен вызываться
        I18nManager().set_language("ru")
        assert view.retranslate_call_count == 1

        # Повторный cleanup не вызывает исключений
        view.cleanup()
    finally:
        view.deleteLater()


@pytest.mark.unit
def test_sidebar_tooltips_retranslation(qapp):
    """
    Проверка динамического обновления всплывающих подсказок кнопок сайдбара
    при переключении RU <-> EN без изменения физических размеров элементов.
    """
    I18nManager().set_language("ru", emit_signal=False)
    sidebar = SidebarDock()
    try:
        # Проверяем русские подсказки по умолчанию
        assert sidebar.btn_yt.toolTip() == "YouTube и медиа"
        assert sidebar.btn_sensors.toolTip() == "Датчики AIDA64"
        assert sidebar.btn_deck.toolTip() == "DuckDeck (Макро-панель и управление)"
        assert sidebar.btn_audio.toolTip() == "Аудиомикшер"
        assert sidebar.btn_showcase.toolTip() == "Диагностика системы"

        # Физическая геометрия (80px ширина)
        assert sidebar.width() == 80
        assert sidebar.btn_yt.width() == 64
        assert sidebar.btn_yt.height() == 60

        # Переключаем язык на English
        I18nManager().set_language("en")

        assert sidebar.btn_yt.toolTip() == "YouTube & Media"
        assert sidebar.btn_sensors.toolTip() == "AIDA64 Sensors"
        assert sidebar.btn_deck.toolTip() == "DuckDeck (Macro Panel)"
        assert sidebar.btn_audio.toolTip() == "Audio Mixer"
        assert sidebar.btn_showcase.toolTip() == "System Showcase"

        # Геометрия не должна деформироваться
        assert sidebar.width() == 80
        assert sidebar.btn_yt.width() == 64
        assert sidebar.btn_yt.height() == 60

        # Возвращаем на русский
        I18nManager().set_language("ru")
        assert sidebar.btn_yt.toolTip() == "YouTube и медиа"
        assert sidebar.btn_audio.toolTip() == "Аудиомикшер"
    finally:
        sidebar.cleanup()
        sidebar.deleteLater()


@pytest.mark.unit
def test_sidebar_lock_button_tooltip_states(qapp):
    """
    Проверка подсказок кнопки блокировки ввода в зависимости от состояния и языка:
    - Stealth Focus активен (locked=False) -> подсказка предлагает разблокировать клавиатуру.
    - Interactive активен (locked=True) -> подсказка предлагает вернуть Stealth.
    """
    I18nManager().set_language("ru", emit_signal=False)
    sidebar = SidebarDock()
    try:
        # 1. По умолчанию Stealth Mode (ru)
        assert sidebar.btn_lock.toolTip() == "Режим Stealth Focus (нажмите для ввода с клавиатуры)"

        # 2. Смена языка на en при активном Stealth Mode
        I18nManager().set_language("en")
        assert sidebar.btn_lock.toolTip() == "Stealth Focus Mode (Click to allow keyboard input)"

        # 3. Переключение в режим интерактивного ввода (en)
        sidebar._toggle_input_lock()
        assert sidebar._input_locked is True
        assert sidebar.btn_lock.toolTip() == "Interactive Input (Click to restore Stealth)"

        # 4. Смена языка на ru при активном интерактивном вводе
        I18nManager().set_language("ru")
        assert sidebar.btn_lock.toolTip() == "Интективный ввод (нажмите для возврата Stealth)" or "Интерактивный ввод" in sidebar.btn_lock.toolTip()

        # 5. Возврат в Stealth Mode
        sidebar._toggle_input_lock()
        assert sidebar._input_locked is False
        assert sidebar.btn_lock.toolTip() == "Режим Stealth Focus (нажмите для ввода с клавиатуры)"
    finally:
        sidebar.cleanup()
        sidebar.deleteLater()


@pytest.mark.unit
def test_mini_media_bar_retranslation(qapp):
    """
    Проверка локализации подсказок кнопок MiniMediaBar и поведения бегущей строки:
    - Подсказки кнопок prev, play/pause, next и самого бара.
    - Динамическое переключение при сигнале смены языка.
    """
    I18nManager().set_language("ru", emit_signal=False)
    bar = MiniMediaBar()
    try:
        assert bar.toolTip() == "Открыть плеер"
        assert bar.btn_prev.toolTip() == "Предыдущий трек"
        assert bar.btn_play.toolTip() == "Воспроизведение"
        assert bar.btn_next.toolTip() == "Следующий трек"

        # Имитируем начало воспроизведения трека
        bar._on_media_state_changed({"title": "Test Track", "artist": "Band", "is_playing": True})
        assert bar.btn_play.toolTip() == "Пауза"

        # Переключаем на English
        I18nManager().set_language("en")
        assert bar.toolTip() == "Open Player"
        assert bar.btn_prev.toolTip() == "Previous track"
        assert bar.btn_play.toolTip() == "Pause"
        assert bar.btn_next.toolTip() == "Next track"

        # Имитируем остановку воспроизведения
        bar._on_media_state_changed({"title": "", "artist": "", "is_playing": False})
        assert bar.btn_play.toolTip() == "Play"
    finally:
        bar.cleanup()
        bar.deleteLater()


@pytest.mark.unit
def test_main_window_language_initialization(qapp):
    """
    Проверка инициализации языка в MainWindow:
    - При холодном старте с config.language="en" язык менеджера инициализируется без паразитного сигнала.
    - Заголовок окна DuckDock формируется с учетом локализованного подзаголовка.
    - Сайдбар сразу получает подсказки на нужном языке.
    - При смене языка заголовок окна динамически обновляется.
    """
    lang_signals = []
    def _track_lang(lang):
        lang_signals.append(lang)

    bus.language_changed.connect(_track_lang)
    config = AppConfig(language="en")

    win = MainWindow(config)
    try:
        # Проверяем, что emit_signal=False не вызвал паразитного сигнала при холодном старте
        assert len(lang_signals) == 0
        assert I18nManager().current_language == "en"

        # Проверяем заголовок окна и подсказки сайдбара
        assert win.windowTitle() == "DuckDock - Touch Control Panel"
        assert win.sidebar.btn_yt.toolTip() == "YouTube & Media"
        assert win.sidebar.btn_audio.toolTip() == "Audio Mixer"

        # Динамическая смена языка на ru
        I18nManager().set_language("ru")
        assert win.windowTitle() == "DuckDock - Сенсорная панель управления"
        assert win.sidebar.btn_yt.toolTip() == "YouTube и медиа"
        assert win.sidebar.btn_audio.toolTip() == "Аудиомикшер"
    finally:
        try:
            bus.language_changed.disconnect(_track_lang)
        except Exception:
            pass
        win.close()
