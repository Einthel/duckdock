"""
Аппаратный Sparkline-виджет на QPainter для дашборда NOC DuckDock.
Обеспечивает легковесный рендеринг сглаженной кривой телеметрии (QPainterPath)
с полупрозрачным градиентом, адаптивной пороговой палитрой (<60°C / 60-78°C / >80°C)
и 0% нагрузки на dGPU (полная изоляция на iGPU).
"""
from collections import deque
from typing import Optional, Sequence, Union

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from core.telemetry_history import RingBuffer


class SparklineWidget(QWidget):
    """
    Высокопроизводительный виджет Sparkline-графика на базе QPainter.
    Поддерживает:
      - Сглаженную кривую Bezier и полупрозрачный градиентный фон.
      - Адаптивную цветовую палитру (Cyan / Amber / Crimson) по порогам значений.
      - Фиксированные или автоматически масштабируемые диапазоны (min/max).
      - Подключение через RingBuffer или прямой вызов add_value / set_data.
      - Строгий инвариант Stealth Focus (Qt.NoFocus).
    """

    COLOR_CYAN = "#38bdf8"     # Норма: <60°C
    COLOR_AMBER = "#f59e0b"    # Предупреждение: 60-78°C
    COLOR_CRIMSON = "#ef4444"  # Критично: >=80°C

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        maxlen: int = 60,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        warning_threshold: float = 60.0,
        critical_threshold: float = 80.0,
        fixed_color: Optional[Union[QColor, str]] = None,
        line_width: float = 2.0,
        fill_opacity: float = 0.25,
        show_beacon: bool = True,
        show_grid: bool = True,
        auto_scale: bool = True,
    ):
        super().__init__(parent)

        # Инвариант Stealth Focus: элемент не должен перехватывать фокус мыши/тача
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, False)

        self._maxlen = max(2, maxlen)
        self._buffer: deque = deque(maxlen=self._maxlen)

        self._min_val = min_val
        self._max_val = max_val
        self._auto_scale = auto_scale

        self._warning_threshold = float(warning_threshold)
        self._critical_threshold = float(critical_threshold)
        self._fixed_color = QColor(fixed_color) if fixed_color else None

        self._line_width = float(line_width)
        self._fill_opacity = float(fill_opacity)
        self._show_beacon = show_beacon
        self._show_grid = show_grid

        # По умолчанию компактный размер для карточек NOC
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(80, 28)

    # ------------------------------------------------------------------
    # Управление данными
    # ------------------------------------------------------------------

    def add_value(self, value: float) -> None:
        """Добавить единичное значение в буфер и запросить перерисовку."""
        try:
            val = float(value)
        except (ValueError, TypeError):
            val = 0.0
        self._buffer.append(val)
        self.update()

    def set_data(self, data: Sequence[float]) -> None:
        """Перезаписать буфер последовательностью значений."""
        self._buffer.clear()
        for item in data[-self._maxlen:]:
            try:
                self._buffer.append(float(item))
            except (ValueError, TypeError):
                self._buffer.append(0.0)
        self.update()

    def set_ring_buffer(self, ring_buf: RingBuffer) -> None:
        """Синхронизировать виджет с кольцевым буфером ядра."""
        if ring_buf is not None:
            self.set_data(ring_buf.to_list())

    def clear(self) -> None:
        """Очистить буфер графика."""
        self._buffer.clear()
        self.update()

    # ------------------------------------------------------------------
    # Настройки и палитра
    # ------------------------------------------------------------------

    def set_thresholds(self, warning: float, critical: float) -> None:
        """Настроить пороги для цветовой индикации."""
        self._warning_threshold = float(warning)
        self._critical_threshold = float(critical)
        self.update()

    def set_fixed_color(self, color: Optional[Union[QColor, str]]) -> None:
        """Установить фиксированный цвет (None для возврата к адаптивному)."""
        self._fixed_color = QColor(color) if color else None
        self.update()

    def set_range(self, min_val: Optional[float], max_val: Optional[float]) -> None:
        """Задать жесткий диапазон оси Y."""
        self._min_val = min_val
        self._max_val = max_val
        self.update()

    def get_current_color(self) -> QColor:
        """
        Возвращает актуальный цвет на основе последнего значения буфера:
          - fixed_color (если задан)
          - Crimson (#ef4444) при значении >= critical_threshold
          - Amber (#f59e0b) при значении >= warning_threshold
          - Cyan (#38bdf8) при норме (< warning_threshold)
        """
        if self._fixed_color is not None:
            return self._fixed_color

        if not self._buffer:
            return QColor(self.COLOR_CYAN)

        latest = self._buffer[-1]
        if latest >= self._critical_threshold:
            return QColor(self.COLOR_CRIMSON)
        elif latest >= self._warning_threshold:
            return QColor(self.COLOR_AMBER)
        else:
            return QColor(self.COLOR_CYAN)

    @property
    def latest_value(self) -> float:
        """Последнее значение в буфере (или 0.0 при пустом буфере)."""
        return self._buffer[-1] if self._buffer else 0.0

    @property
    def count(self) -> int:
        """Количество накопленных точек."""
        return len(self._buffer)

    # ------------------------------------------------------------------
    # Отрисовка QPainter
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        w = self.width()
        h = self.height()
        if w < 10 or h < 6:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pad_top = 4.0
        pad_bottom = 4.0
        pad_left = 2.0
        pad_right = 6.0 if self._show_beacon else 2.0

        usable_w = max(1.0, float(w) - pad_left - pad_right)
        usable_h = max(1.0, float(h) - pad_top - pad_bottom)
        base_y = pad_top + usable_h

        # 1. Тонкая сетка ориентиров (Grid)
        if self._show_grid:
            self._draw_grid(painter, pad_left, pad_top, usable_w, usable_h)

        data = list(self._buffer)
        if not data:
            painter.end()
            return

        # 2. Вычисление диапазона Y
        y_min, y_max = self._compute_bounds(data)
        span = max(0.001, y_max - y_min)

        # 3. Построение экранных координат точек
        points = []
        n = len(data)
        if n == 1:
            norm_y = (data[0] - y_min) / span
            py = pad_top + usable_h * (1.0 - norm_y)
            points.append(QPointF(pad_left + usable_w, py))
        else:
            step_x = usable_w / (n - 1)
            for i, val in enumerate(data):
                px = pad_left + i * step_x
                norm_y = max(0.0, min(1.0, (val - y_min) / span))
                py = pad_top + usable_h * (1.0 - norm_y)
                points.append(QPointF(px, py))

        # 4. Построение сглаженной кривой Безье
        curve_path = QPainterPath()
        curve_path.moveTo(points[0])

        if len(points) == 2:
            curve_path.lineTo(points[1])
        elif len(points) > 2:
            for i in range(len(points) - 1):
                p0 = points[i]
                p1 = points[i + 1]
                mid_x = (p0.x() + p1.x()) / 2.0
                # Кубическая кривая для плавности без осцилляционных выбросов
                curve_path.cubicTo(QPointF(mid_x, p0.y()), QPointF(mid_x, p1.y()), p1)

        active_color = self.get_current_color()

        # 5. Градиентная заливка области под графиком
        if len(points) > 1 and self._fill_opacity > 0.0:
            fill_path = QPainterPath(curve_path)
            fill_path.lineTo(points[-1].x(), base_y)
            fill_path.lineTo(points[0].x(), base_y)
            fill_path.closeSubpath()

            gradient = QLinearGradient(0, pad_top, 0, base_y)
            top_color = QColor(active_color)
            top_color.setAlpha(int(255 * self._fill_opacity))
            bottom_color = QColor(active_color)
            bottom_color.setAlpha(0)

            gradient.setColorAt(0.0, top_color)
            gradient.setColorAt(1.0, bottom_color)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawPath(fill_path)

        # 6. Отрисовка основной линии тренда
        stroke_pen = QPen(active_color, self._line_width)
        stroke_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroke_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(stroke_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(curve_path)

        # 7. Индикатор последней точки (Beacon Dot)
        if self._show_beacon and points:
            last_pt = points[-1]

            # Внешний ореол (Halo)
            halo_color = QColor(active_color)
            halo_color.setAlpha(70)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo_color)
            painter.drawEllipse(last_pt, 4.0, 4.0)

            # Внутреннее яркое ядро
            painter.setBrush(active_color)
            painter.drawEllipse(last_pt, 2.0, 2.0)

        painter.end()

    def _draw_grid(
        self,
        painter: QPainter,
        left: float,
        top: float,
        width: float,
        height: float,
    ) -> None:
        """Отрисовка деликатных направляющих сетки дашборда."""
        grid_pen = QPen(QColor(255, 255, 255, 14), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        right = left + width
        # 50% линия
        mid_y = top + height * 0.5
        painter.drawLine(QPointF(left, mid_y), QPointF(right, mid_y))

        # Базовая линия внизу
        base_y = top + height
        painter.drawLine(QPointF(left, base_y), QPointF(right, base_y))

    def _compute_bounds(self, data: Sequence[float]) -> tuple[float, float]:
        """Расчет диапазона оси Y с учетом фиксированных границ и автошкалы."""
        if self._min_val is not None and self._max_val is not None:
            return float(self._min_val), float(self._max_val)

        d_min = min(data)
        d_max = max(data)

        if self._min_val is not None:
            y_min = float(self._min_val)
        else:
            y_min = d_min

        if self._max_val is not None:
            y_max = float(self._max_val)
        else:
            y_max = d_max

        if self._auto_scale and (self._min_val is None or self._max_val is None):
            span = y_max - y_min
            if span < 5.0:
                # Минимальный искусственный диапазон для предотвращения вырождения при константах
                mid = (y_max + y_min) / 2.0
                y_min = mid - 2.5
                y_max = mid + 2.5
            else:
                padding = span * 0.05
                if self._min_val is None:
                    y_min -= padding
                if self._max_val is None:
                    y_max += padding

        return y_min, y_max
