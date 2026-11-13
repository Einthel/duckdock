"""
Тач-оптимизированный медиаплеер / YouTube контейнер (720x600).
Поддерживает работу через QWebEngineView (при наличии модуля)
или встроенный легковесный медиа-дашборд с кнопками управления.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame
)
from PySide6.QtCore import Qt, QUrl, QSize

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings
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
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton.quick-btn:hover {
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

class YouTubeView(QWidget):
    """Контейнер медиаплеера с крупными тач-контролами под 720x600."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(YOUTUBE_QSS)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Верхняя панель быстрых ссылок
        quick_bar = QHBoxLayout()
        quick_bar.setSpacing(8)

        lbl_header = QLabel("▶ MEDIA & YOUTUBE")
        lbl_header.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: bold;")
        quick_bar.addWidget(lbl_header)
        quick_bar.addStretch()

        btn_music = QPushButton("YouTube Music")
        btn_music.setProperty("class", "quick-btn")
        btn_music.setFocusPolicy(Qt.NoFocus)
        quick_bar.addWidget(btn_music)

        btn_streams = QPushButton("Twitch / Streams")
        btn_streams.setProperty("class", "quick-btn")
        btn_streams.setFocusPolicy(Qt.NoFocus)
        quick_bar.addWidget(btn_streams)

        layout.addLayout(quick_bar)

        # Основная область контента
        if HAS_WEBENGINE:
            self.web_view = QWebEngineView()
            self.web_view.settings().setAttribute(
                QWebEngineSettings.PlaybackRequiresUserGesture, False
            )
            self.web_view.setUrl(QUrl("https://music.youtube.com"))
            layout.addWidget(self.web_view)
        else:
            # Fallback плеер с крупными сенсорными кнопками управления
            card = QFrame()
            card.setProperty("class", "media-card")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(16)

            now_playing_title = QLabel("System Media Player (iGPU Low-Power Mode)")
            now_playing_title.setStyleSheet("color: #e2e8f0; font-size: 18px; font-weight: bold;")
            card_layout.addWidget(now_playing_title)

            sub_info = QLabel("Оптимизировано для сенсорного экрана 800x600. Stealth Focus активен.")
            sub_info.setStyleSheet("color: #64748b; font-size: 13px;")
            card_layout.addWidget(sub_info)

            card_layout.addStretch()

            # Кнопки управления воспроизведением (крупные тач-мишени)
            ctrl_layout = QHBoxLayout()
            ctrl_layout.addStretch()

            btn_prev = QPushButton("⏮")
            btn_prev.setProperty("class", "media-ctrl-btn")
            btn_prev.setFocusPolicy(Qt.NoFocus)
            ctrl_layout.addWidget(btn_prev)

            btn_play = QPushButton("▶")
            btn_play.setProperty("class", "media-ctrl-btn")
            btn_play.setFocusPolicy(Qt.NoFocus)
            ctrl_layout.addWidget(btn_play)

            btn_next = QPushButton("⏭")
            btn_next.setProperty("class", "media-ctrl-btn")
            btn_next.setFocusPolicy(Qt.NoFocus)
            ctrl_layout.addWidget(btn_next)

            ctrl_layout.addStretch()
            card_layout.addLayout(ctrl_layout)

            # Громкость
            vol_layout = QHBoxLayout()
            lbl_vol = QLabel("Громкость:")
            lbl_vol.setStyleSheet("color: #94a3b8; font-size: 13px;")
            vol_layout.addWidget(lbl_vol)

            vol_slider = QSlider(Qt.Horizontal)
            vol_slider.setRange(0, 100)
            vol_slider.setValue(70)
            vol_slider.setFocusPolicy(Qt.NoFocus)
            vol_layout.addWidget(vol_slider)

            card_layout.addLayout(vol_layout)
            layout.addWidget(card)
