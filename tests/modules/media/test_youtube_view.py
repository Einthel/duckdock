"""
Unit-тесты для YouTubeView, MiniMediaBar и MarqueeLabel (Спринт 4).
"""
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QUrl

from core.event_bus import bus
from core.i18n import I18nManager
from modules.media.view import HAS_WEBENGINE, YouTubeView
from ui.sidebar import MarqueeLabel, MiniMediaBar, SidebarDock


@pytest.mark.unit
def test_marquee_label_ticker(qapp):
    """Проверка бегущей строки MarqueeLabel."""
    label = MarqueeLabel("Short")
    assert label.focusPolicy() == Qt.NoFocus
    assert label.text() == "Short"
    assert not label._timer.isActive()

    # Длинный заголовок трека запускает таймер бегущей строки
    label.set_track_text("Daft Punk - Around the World")
    assert label._timer.isActive()
    initial_text = label.text()

    # Такт анимации сдвигает текст
    label._on_tick()
    assert label.text() != initial_text


@pytest.mark.unit
def test_mini_media_bar_stealth_focus_and_actions(qapp):
    """Проверка Stealth Focus и сигналов управления воспроизведением."""
    bar = MiniMediaBar()
    assert bar.focusPolicy() == Qt.NoFocus
    assert bar.btn_prev.focusPolicy() == Qt.NoFocus
    assert bar.btn_play.focusPolicy() == Qt.NoFocus
    assert bar.btn_next.focusPolicy() == Qt.NoFocus

    received_actions = []
    bus.media_action_requested.connect(lambda act: received_actions.append(act))

    # Клик по Prev
    bar.btn_prev.click()
    assert "prev" in received_actions

    # Клик по Play/Pause
    bar.btn_play.click()
    assert "toggle_play" in received_actions

    # Клик по Next
    bar.btn_next.click()
    assert "next" in received_actions

    # Обновление состояния плеера
    bus.media_state_changed.emit({
        "title": "Starboy",
        "artist": "The Weeknd",
        "is_playing": True
    })
    assert bar.btn_play.text() == "⏸"

    bus.media_state_changed.emit({
        "title": "Starboy",
        "artist": "The Weeknd",
        "is_playing": False
    })
    assert bar.btn_play.text() == "▶"


@pytest.mark.unit
def test_mini_media_bar_click_navigates_to_youtube_tab(qapp):
    """Проверка перехода на вкладку YouTube (индекс 0) при тапе по мини-бару."""
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    bar = MiniMediaBar()
    tabs_switched = []
    bus.tab_changed.connect(lambda idx: tabs_switched.append(idx))

    # Имитация клика мыши/тача по виджету через реальный QMouseEvent
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5.0, 5.0),
        QPointF(5.0, 5.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    bar.mousePressEvent(event)
    assert 0 in tabs_switched


@pytest.mark.unit
def test_sidebar_contains_mini_media_bar(qapp):
    """Проверка наличия MiniMediaBar в SidebarDock."""
    sidebar = SidebarDock()
    assert hasattr(sidebar, "mini_media_bar")
    assert sidebar.mini_media_bar is not None
    assert sidebar.btn_lock.focusPolicy() == Qt.NoFocus
    assert not hasattr(sidebar, "btn_dimmer")


@pytest.mark.unit
def test_youtube_view_initialization(qapp):
    """Проверка создания YouTubeView, Stealth Focus на кнопках и навигации."""
    view = YouTubeView()
    assert view is not None

    if HAS_WEBENGINE:
        assert hasattr(view, "web_view")
        assert view.web_view.page() is not None
        # Проверка флага воспроизведения без жеста пользователя
        from PySide6.QtWebEngineCore import QWebEngineSettings
        assert not view.web_view.settings().testAttribute(
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture
        )
    else:
        assert hasattr(view, "lbl_fallback_title")

    # Проверка вызова навигации
    with patch.object(view, "navigate") as mock_nav:
        view.navigate("https://music.youtube.com")
        mock_nav.assert_called_once_with("https://music.youtube.com")

    # Проверка получения медиа-состояния
    media_states = []
    bus.media_state_changed.connect(lambda st: media_states.append(st))

    test_state = {"title": "One More Time", "artist": "Daft Punk", "is_playing": True}
    view._on_media_state_received(test_state)
    assert len(media_states) > 0
    assert media_states[-1]["title"] == "One More Time"

    if HAS_WEBENGINE:
        from core.web_interceptor import DESKTOP_CHROME_UA, FIREFOX_UA
        from core.web_profile import WebProfileManager
        profile = WebProfileManager.get_instance().get_profile()

        # Редирект на Google Accounts -> переключение на Firefox UA
        view._on_url_changed(QUrl("https://accounts.google.com/signin/v2/identifier"))
        assert profile.httpUserAgent() == FIREFOX_UA

        # Возврат на YouTube Music -> восстановление Chrome UA
        view._on_url_changed(QUrl("https://music.youtube.com/"))
        assert profile.httpUserAgent() == DESKTOP_CHROME_UA

        # Проверка createWindow возвращает self
        assert view.web_view.page().createWindow(0) is view.web_view.page()

    view.close()


@pytest.mark.unit
def test_youtube_view_retranslate_ui(qapp):
    """Проверка смены локализации в заголовках, тултипах и fallback-плеере YouTubeView."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)

    # Принудительно тестируем fallback-плеер (без WebEngine)
    with patch("modules.media.view.HAS_WEBENGINE", False):
        view = YouTubeView()
        try:
            # 1. Русский язык
            assert view.lbl_header.text() == "▶ MEDIA & YOUTUBE"
            assert view.btn_ytm.text() == "YouTube Music"
            assert view.btn_login.text() == "🔑 Войти"
            assert view.btn_login.toolTip() == "Авторизация в аккаунте Google / YouTube Music"
            assert view.btn_reload.toolTip() == "Перезагрузить страницу"

            # Fallback плеер
            assert view.lbl_fallback_title.text() == "Системный медиаплеер (iGPU Low-Power Mode)"
            assert "944x600" in view.lbl_fallback_subtitle.text()
            assert view.lbl_vol.text() == "Громкость:"
            assert view.btn_prev.toolTip() == "Предыдущий трек"
            assert view.btn_next.toolTip() == "Следующий трек"
            assert view.btn_play_fallback.toolTip() == "Воспроизведение"

            # 2. Горячая смена на английский
            mgr.set_language("en")
            # TouchModuleView автоматически вызывает retranslate_ui()

            assert view.btn_login.text() == "🔑 Sign In"
            assert view.btn_login.toolTip() == "Sign in with Google / YouTube Music account"
            assert view.btn_reload.toolTip() == "Reload page"

            assert view.lbl_fallback_title.text() == "System Media Player (iGPU Low-Power Mode)"
            assert "touchscreen" in view.lbl_fallback_subtitle.text()
            assert view.lbl_vol.text() == "Volume:"
            assert view.btn_prev.toolTip() == "Previous track"
            assert view.btn_next.toolTip() == "Next track"
            assert view.btn_play_fallback.toolTip() == "Play"

            # 3. Возврат на русский
            mgr.set_language("ru")
            assert view.btn_login.text() == "🔑 Войти"
            assert view.lbl_vol.text() == "Громкость:"
        finally:
            mgr.set_language("ru", emit_signal=False)
            view.cleanup()
            view.deleteLater()
