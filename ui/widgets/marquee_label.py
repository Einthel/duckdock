"""
Бегущая строка DuckDock (MarqueeLabel).
Предназначена для отображения длинных заголовков треков в компактном сайдбаре (64px)
с сохранением политики Qt.NoFocus.
"""
from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget


class MarqueeLabel(QLabel):
    """Сенсорная метка с бегущей строкой названия трека."""

    def __init__(self, text: str = "YouTube Music", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setObjectName("media_title")
        self.setAlignment(Qt.AlignCenter)
        self.setFocusPolicy(Qt.NoFocus)
        self._raw_text = text
        self._offset = 0
        self._timer = QTimer(self)
        self._timer.setInterval(280)
        self._timer.timeout.connect(self._on_tick)

    def set_track_text(self, text: str):
        self._raw_text = text or "YouTube Music"
        self._offset = 0
        if len(self._raw_text) > 8:
            if not self._timer.isActive():
                self._timer.start()
            self._on_tick()
        else:
            self._timer.stop()
            self.setText(self._raw_text)

    def _on_tick(self):
        if not self._raw_text:
            return
        if len(self._raw_text) <= 8:
            self.setText(self._raw_text)
            return
        padded = self._raw_text + "   •   "
        self._offset = (self._offset + 1) % len(padded)
        self.setText(padded[self._offset:self._offset + 8])


__all__ = ["MarqueeLabel"]
