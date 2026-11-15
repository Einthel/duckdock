"""
Сенсорный компактный медиабар (MiniMediaBar) для DuckDock.
Ширина 64px, высота 54px.
Управление треками ⏮ ⏯ ⏭ и бегущая строка MarqueeLabel.
Обеспечивает сквозное управление воспроизведением и навигацию к вкладке плеера.
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton

from core.event_bus import bus
from ui.widgets.marquee_label import MarqueeLabel


class MiniMediaBar(QFrame):
    """
    Компактный сенсорный медиабар в сайдбаре (ширина 64px).
    Обеспечивает сквозное управление треками и отображение названия бегущей строкой.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mini_media_bar")
        self.setFixedWidth(64)
        self.setFixedHeight(54)
        self.setFocusPolicy(Qt.NoFocus)

        self._is_playing = False
        self._init_ui()

        # Подписка на изменение состояния медиаплеера
        bus.media_state_changed.connect(self._on_media_state_changed)
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self, *args):
        try:
            bus.media_state_changed.disconnect(self._on_media_state_changed)
        except Exception:
            pass

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(2)

        # Название трека бегущей строкой
        self.lbl_title = MarqueeLabel("YouTube", self)
        layout.addWidget(self.lbl_title)

        # Кнопки ⏮ ⏯ ⏭
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(2)

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setProperty("class", "mini-media-btn")
        self.btn_prev.setFixedSize(QSize(18, 22))
        self.btn_prev.setFocusPolicy(Qt.NoFocus)
        self.btn_prev.clicked.connect(lambda: bus.media_action_requested.emit("prev"))
        btn_layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setProperty("class", "mini-media-btn")
        self.btn_play.setFixedSize(QSize(22, 22))
        self.btn_play.setFocusPolicy(Qt.NoFocus)
        self.btn_play.clicked.connect(lambda: bus.media_action_requested.emit("toggle_play"))
        btn_layout.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setProperty("class", "mini-media-btn")
        self.btn_next.setFixedSize(QSize(18, 22))
        self.btn_next.setFocusPolicy(Qt.NoFocus)
        self.btn_next.clicked.connect(lambda: bus.media_action_requested.emit("next"))
        btn_layout.addWidget(self.btn_next)

        layout.addLayout(btn_layout)

    def _on_media_state_changed(self, state: dict):
        title = state.get("title", "")
        artist = state.get("artist", "")
        is_playing = state.get("is_playing", False)

        display_text = f"{title} - {artist}" if artist and title else (title or "YouTube")
        self.lbl_title.set_track_text(display_text)

        self._is_playing = is_playing
        self.btn_play.setText("⏸" if is_playing else "▶")

    def mousePressEvent(self, event):
        """Быстрый переход на вкладку YouTube по касанию панели мини-бара."""
        bus.tab_changed.emit(0)
        if event is not None:
            super().mousePressEvent(event)


__all__ = ["MiniMediaBar"]
