"""
Сквозной слой затемнения (Software Dimmer) для 7" экрана 800x600.
Использует Qt.WA_TransparentForMouseEvents, позволяя кликать сквозь затемнение.
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor

class DimmerOverlay(QWidget):
    """Сквозной оверлей для регулировки яркости экрана без DDC/CI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Пропускает любые клики и тач-события на нижележащие контролы
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self._opacity: float = 0.0  # 0.0 (полная яркость) .. 0.95 (ночной режим)

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, value: float):
        self._opacity = max(0.0, min(0.95, value))
        self.update()

    def set_dimmer_level(self, level: float):
        self.opacity = level

    def toggle(self, target_level: float = 0.85):
        if self._opacity > 0.05:
            self.opacity = 0.0
        else:
            self.opacity = target_level

    def paintEvent(self, event):
        if self._opacity <= 0.01:
            return

        painter = QPainter(self)
        alpha = int(self._opacity * 255)
        painter.fillRect(self.rect(), QColor(0, 0, 0, alpha))
