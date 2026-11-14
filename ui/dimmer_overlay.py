"""
Сквозной слой затемнения (Software Dimmer) для 7" экрана 1024x600.
Использует Qt.WA_TransparentForMouseEvents, позволяя кликать сквозь затемнение.
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor


class DimmerOverlay(QWidget):
    """Сквозной оверлей для регулировки яркости экрана без DDC/CI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Пропускает любые клики и тач-события на нижележащие контролы
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self._opacity: float = 0.0  # 0.0 (полная яркость) .. 0.95 (ночной режим)
        self._target_opacity: float = 0.0

        # Плавная анимация изменения уровня яркости (200 мс, OutCubic)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_value_changed)

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, value: float):
        if self._anim.state() == QVariantAnimation.State.Running:
            self._anim.stop()
        self._target_opacity = max(0.0, min(0.95, float(value)))
        self._apply_opacity(self._target_opacity)

    @property
    def target_opacity(self) -> float:
        return self._target_opacity

    @property
    def is_animating(self) -> bool:
        return self._anim.state() == QVariantAnimation.State.Running

    def _apply_opacity(self, value: float):
        self._opacity = round(max(0.0, min(0.95, float(value))), 4)
        self.update()
        try:
            from core.event_bus import bus
            bus.dimmer_opacity_changed.emit(self._opacity)
        except Exception:
            pass

    def _on_anim_value_changed(self, value):
        self._apply_opacity(float(value))

    def set_dimmer_level(self, level: float, animated: bool = True):
        clamped = max(0.0, min(0.95, float(level)))
        self._target_opacity = clamped

        if not animated or self._anim.duration() == 0:
            if self._anim.state() == QVariantAnimation.State.Running:
                self._anim.stop()
            self._apply_opacity(clamped)
            return

        if self._anim.state() == QVariantAnimation.State.Running:
            self._anim.stop()

        if abs(self._opacity - clamped) < 0.001:
            return

        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(clamped)
        self._anim.start()

    def toggle(self, target_level: float = 0.50, animated: bool = True):
        """
        Переключение между 0.0 и target_level (по умолчанию 0.50).
        При анимации учитывает текущее целевое направление, предотвращая рывки.
        """
        if self._anim.state() == QVariantAnimation.State.Running:
            is_active = self._target_opacity > 0.05
        else:
            is_active = self._opacity > 0.05

        if is_active:
            self.set_dimmer_level(0.0, animated=animated)
        else:
            self.set_dimmer_level(target_level, animated=animated)

    def paintEvent(self, event):
        if self._opacity <= 0.001:
            return

        painter = QPainter(self)
        alpha = int(self._opacity * 255)
        painter.fillRect(self.rect(), QColor(0, 0, 0, alpha))
