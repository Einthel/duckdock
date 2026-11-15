"""
Сенсорный слайдер DuckDock (TouchSlider).
Поддерживает мгновенный прыжок значения (Jump-to-touch) в точку касания
и политику Qt.NoFocus для сохранения фокуса на основном мониторе.
"""
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider, QStyle, QWidget


class TouchSlider(QSlider):
    """
    Слайдер с мгновенной реакцией на касание в любой точке трека
    и политикой Qt.NoFocus для сохранения фокуса на основном экране.
    """

    def __init__(self, orientation: Qt.Orientation = Qt.Horizontal, parent: Optional[QWidget] = None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.NoFocus)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val = QStyle.sliderValueFromPosition(
                self.minimum(),
                self.maximum(),
                int(event.position().x()),
                self.width(),
            )
            self.setValue(val)
            event.accept()
        super().mousePressEvent(event)


__all__ = ["TouchSlider"]
