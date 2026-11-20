"""
Тач-оптимизированный медиаплеер / YouTube контейнер под 944x600.
Поддерживает изолированный профиль Chromium на iGPU с блокировкой рекламы,
инжекцией тач-стилей, обходом детекции авторизации Google Accounts
и двунаправленным обменом состояния с MiniMediaBar.
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame
)
from PySide6.QtCore import Qt, QUrl, QTimer

from core.event_bus import bus
from core.i18n import t
from core.ui_base import TouchModuleView
from modules.media.web_profile import WebProfileManager
from modules.media.interceptor import DESKTOP_CHROME_UA, FIREFOX_UA

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

YOUTUBE_QSS = """
QFrame.media-card {
    background-color: #161b26;
    border: 1px solid #232b3e;
    border-radius: 12px;
    padding: 16px;
}

QPushButton.media-ctrl-btn {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 24px;
    font-size: 18px;
    min-width: 48px;
    min-height: 48px;
}

QPushButton.media-ctrl-btn:hover {
    background-color: #2563eb;
    border-color: #60a5fa;
}

QPushButton.quick-btn {
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton.quick-btn:hover {
    background-color: #3b82f6;
    color: #ffffff;
}

QPushButton.reload-btn {
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 8px;
    font-size: 14px;
    min-width: 36px;
    min-height: 32px;
}

QPushButton.reload-btn:hover {
    background-color: #3b82f6;
    color: #ffffff;
}

QSlider::groove:horizontal {
    background-color: #1e293b;
    height: 8px;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background-color: #3b82f6;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background-color: #60a5fa;
    width: 20px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 10px;
}
"""

if HAS_WEBENGINE:
    class DuckDockWebPage(QWebEnginePage):
        """
        Кастомный WebEnginePage:
        1. Перенаправляет всплывающие окна авторизации OAuth/Google в текущий web_view.
        2. Гарантирует бесшовную работу диалогов входа без потери сессии.
        """

        def createWindow(self, type_):
            # Перенаправляем popups и редиректы авторизации в текущий виджет
            return self
else:
    class DuckDockWebPage:
        pass


class YouTubeView(TouchModuleView):
    """Контейнер медиаплеера с поддержкой QWebEngine и аппаратного ускорения iGPU."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(YOUTUBE_QSS)

        self._current_media_state = {
            "title": "YouTube Music",
            "artist": "",
            "is_playing": False
        }

        self._init_ui()

        # Подписка на внешние запросы управления (от MiniMediaBar в сайдбаре)
        bus.media_action_requested.connect(self._handle_media_action)

        # Таймер периодического опроса состояния плеера (1000 мс)
        self._state_poll_timer = QTimer(self)
        self._state_poll_timer.setInterval(1000)
        self._state_poll_timer.timeout.connect(self._poll_media_state)
        self._state_poll_timer.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Верхняя панель быстрых переходов
        quick_bar = QHBoxLayout()
        quick_bar.setSpacing(8)

        self.lbl_header = QLabel(t("media.header.title"))
        self.lbl_header.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        quick_bar.addWidget(self.lbl_header)
        quick_bar.addStretch()

        self.btn_ytm = QPushButton(t("media.nav.youtube_music"))
        self.btn_ytm.setProperty("class", "quick-btn")
        self.btn_ytm.setFocusPolicy(Qt.NoFocus)
        self.btn_ytm.clicked.connect(lambda: self.navigate("https://music.youtube.com"))
        quick_bar.addWidget(self.btn_ytm)

        self.btn_yt = QPushButton(t("media.nav.youtube"))
        self.btn_yt.setProperty("class", "quick-btn")
        self.btn_yt.setFocusPolicy(Qt.NoFocus)
        self.btn_yt.clicked.connect(lambda: self.navigate("https://www.youtube.com"))
        quick_bar.addWidget(self.btn_yt)

        self.btn_twitch = QPushButton(t("media.nav.twitch"))
        self.btn_twitch.setProperty("class", "quick-btn")
        self.btn_twitch.setFocusPolicy(Qt.NoFocus)
        self.btn_twitch.clicked.connect(lambda: self.navigate("https://www.twitch.tv"))
        quick_bar.addWidget(self.btn_twitch)

        self.btn_login = QPushButton(t("media.nav.login"))
        self.btn_login.setProperty("class", "quick-btn")
        self.btn_login.setFocusPolicy(Qt.NoFocus)
        self.btn_login.setToolTip(t("media.nav.login_tooltip"))
        self.btn_login.clicked.connect(
            lambda: self.navigate(
                "https://accounts.google.com/AccountChooser?continue=https%3A%2F%2Fmusic.youtube.com"
            )
        )
        quick_bar.addWidget(self.btn_login)

        self.btn_reload = QPushButton("🔄")
        self.btn_reload.setProperty("class", "reload-btn")
        self.btn_reload.setFocusPolicy(Qt.NoFocus)
        self.btn_reload.setToolTip(t("media.player.reload_tooltip"))
        self.btn_reload.clicked.connect(self.reload_page)
        quick_bar.addWidget(self.btn_reload)

        layout.addLayout(quick_bar)

        # Основная область контента
        if HAS_WEBENGINE:
            self.web_view = QWebEngineView(self)
            profile = WebProfileManager.get_instance().get_profile()
            if profile:
                self.web_page = DuckDockWebPage(profile, self.web_view)
                self.web_view.setPage(self.web_page)

            self.web_view.settings().setAttribute(
                QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False
            )
            self.web_view.urlChanged.connect(self._on_url_changed)
            self.web_view.setUrl(QUrl("https://music.youtube.com"))
            layout.addWidget(self.web_view)
        else:
            self._create_fallback_player(layout)

        self.retranslate_ui()

    def _create_fallback_player(self, parent_layout: QVBoxLayout):
        """Fallback плеер для окружений без установленного QtWebEngine."""
        card = QFrame()
        card.setProperty("class", "media-card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        self.lbl_fallback_title = QLabel(t("media.fallback.title"))
        self.lbl_fallback_title.setStyleSheet("color: #e2e8f0; font-size: 18px; font-weight: bold;")
        card_layout.addWidget(self.lbl_fallback_title)

        self.lbl_fallback_subtitle = QLabel(t("media.fallback.subtitle"))
        self.lbl_fallback_subtitle.setStyleSheet("color: #64748b; font-size: 13px;")
        card_layout.addWidget(self.lbl_fallback_subtitle)

        card_layout.addStretch()

        # Кнопки управления воспроизведением
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addStretch()

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setProperty("class", "media-ctrl-btn")
        self.btn_prev.setFocusPolicy(Qt.NoFocus)
        self.btn_prev.setToolTip(t("media.player.prev"))
        self.btn_prev.clicked.connect(lambda: self._handle_media_action("prev"))
        ctrl_layout.addWidget(self.btn_prev)

        self.btn_play_fallback = QPushButton("▶")
        self.btn_play_fallback.setProperty("class", "media-ctrl-btn")
        self.btn_play_fallback.setFocusPolicy(Qt.NoFocus)
        self.btn_play_fallback.setToolTip(t("media.player.play"))
        self.btn_play_fallback.clicked.connect(lambda: self._handle_media_action("toggle_play"))
        ctrl_layout.addWidget(self.btn_play_fallback)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setProperty("class", "media-ctrl-btn")
        self.btn_next.setFocusPolicy(Qt.NoFocus)
        self.btn_next.setToolTip(t("media.player.next"))
        self.btn_next.clicked.connect(lambda: self._handle_media_action("next"))
        ctrl_layout.addWidget(self.btn_next)

        ctrl_layout.addStretch()
        card_layout.addLayout(ctrl_layout)

        # Слайдер громкости
        vol_layout = QHBoxLayout()
        self.lbl_vol = QLabel(t("media.fallback.volume_label"))
        self.lbl_vol.setStyleSheet("color: #94a3b8; font-size: 13px;")
        vol_layout.addWidget(self.lbl_vol)

        vol_slider = QSlider(Qt.Horizontal)
        vol_slider.setRange(0, 100)
        vol_slider.setValue(70)
        vol_slider.setFocusPolicy(Qt.NoFocus)
        vol_layout.addWidget(vol_slider)

        card_layout.addLayout(vol_layout)
        parent_layout.addWidget(card)

    def retranslate_ui(self) -> None:
        """Обновление всех текстовых элементов интерфейса при смене языка."""
        if hasattr(self, "lbl_header"):
            self.lbl_header.setText(t("media.header.title"))
        if hasattr(self, "btn_ytm"):
            self.btn_ytm.setText(t("media.nav.youtube_music"))
        if hasattr(self, "btn_yt"):
            self.btn_yt.setText(t("media.nav.youtube"))
        if hasattr(self, "btn_twitch"):
            self.btn_twitch.setText(t("media.nav.twitch"))
        if hasattr(self, "btn_login"):
            self.btn_login.setText(t("media.nav.login"))
            self.btn_login.setToolTip(t("media.nav.login_tooltip"))
        if hasattr(self, "btn_reload"):
            self.btn_reload.setToolTip(t("media.player.reload_tooltip"))
        if hasattr(self, "lbl_fallback_title"):
            self.lbl_fallback_title.setText(t("media.fallback.title"))
        if hasattr(self, "lbl_fallback_subtitle"):
            self.lbl_fallback_subtitle.setText(t("media.fallback.subtitle"))
        if hasattr(self, "lbl_vol"):
            self.lbl_vol.setText(t("media.fallback.volume_label"))
        if hasattr(self, "btn_prev"):
            self.btn_prev.setToolTip(t("media.player.prev"))
        if hasattr(self, "btn_next"):
            self.btn_next.setToolTip(t("media.player.next"))
        if hasattr(self, "btn_play_fallback"):
            is_playing = self._current_media_state.get("is_playing", False)
            self.btn_play_fallback.setToolTip(t("media.player.pause") if is_playing else t("media.player.play"))

    def navigate(self, url: str):
        """Переход по URL."""
        if HAS_WEBENGINE and hasattr(self, "web_view"):
            self.web_view.setUrl(QUrl(url))

    def reload_page(self):
        """Перезагрузка текущей страницы."""
        if HAS_WEBENGINE and hasattr(self, "web_view"):
            self.web_view.reload()

    def _on_url_changed(self, qurl: QUrl):
        """Адаптивное переключение User-Agent при переходе на шлюзы авторизации Google."""
        host = qurl.host().lower()
        profile = WebProfileManager.get_instance().get_profile()
        if not profile:
            return
        if "accounts.google" in host or "accounts.youtube" in host:
            profile.setHttpUserAgent(FIREFOX_UA)
        else:
            profile.setHttpUserAgent(DESKTOP_CHROME_UA)

    def _poll_media_state(self):
        """Асинхронный опрос состояния воспроизведения через Chromium JS Bridge."""
        if HAS_WEBENGINE and hasattr(self, "web_view") and self.web_view.page():
            js_code = (
                "typeof window.__duckdock_get_media_state === 'function' "
                "? window.__duckdock_get_media_state() : null;"
            )
            self.web_view.page().runJavaScript(js_code, self._on_media_state_received)

    def _on_media_state_received(self, result):
        """Обработка ответа JS Bridge со статусом трека."""
        if isinstance(result, dict) and "title" in result:
            self._current_media_state = result
            bus.media_state_changed.emit(result)

    def _handle_media_action(self, action: str):
        """Управление воспроизведением по сигналу от EventBus."""
        if HAS_WEBENGINE and hasattr(self, "web_view") and self.web_view.page():
            js_code = f"typeof window.__duckdock_media_action === 'function' ? window.__duckdock_media_action('{action}') : false;"
            self.web_view.page().runJavaScript(js_code)
        else:
            # Fallback обработка
            if action in ("toggle_play", "play_pause"):
                is_playing = not self._current_media_state.get("is_playing", False)
                self._current_media_state["is_playing"] = is_playing
                if hasattr(self, "btn_play_fallback"):
                    self.btn_play_fallback.setText("⏸" if is_playing else "▶")
                bus.media_state_changed.emit(self._current_media_state)

    def cleanup(self) -> None:
        """Очистка таймеров и отписка от шины EventBus."""
        try:
            self._state_poll_timer.stop()
        except Exception:
            pass
        try:
            bus.media_action_requested.disconnect(self._handle_media_action)
        except Exception:
            pass


__all__ = [
    "YouTubeView",
    "DuckDockWebPage",
    "HAS_WEBENGINE",
    "YOUTUBE_QSS",
]
