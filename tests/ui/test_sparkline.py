"""
Модульные тесты для аппаратного Sparkline-виджета (ui/widgets/sparkline.py).
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from modules.telemetry.history import RingBuffer
from ui.widgets.sparkline import SparklineWidget


def test_sparkline_initialization(qapp):
    """Проверка начального состояния и инварианта Stealth Focus (Qt.NoFocus)."""
    sparkline = SparklineWidget(maxlen=60)

    # Инвариант Stealth Focus
    assert sparkline.focusPolicy() == Qt.FocusPolicy.NoFocus

    assert sparkline.count == 0
    assert sparkline.latest_value == 0.0
    assert sparkline.get_current_color().name().lower() == "#38bdf8"


def test_sparkline_data_ingestion(qapp):
    """Проверка добавления данных, очистки и ограничения размера буфера."""
    sparkline = SparklineWidget(maxlen=5)

    # Добавление единичных значений
    sparkline.add_value(10.0)
    sparkline.add_value(20.5)
    assert sparkline.count == 2
    assert sparkline.latest_value == 20.5

    # Переполнение буфера
    for v in [30.0, 40.0, 50.0, 60.0]:
        sparkline.add_value(v)

    assert sparkline.count == 5
    assert sparkline.latest_value == 60.0

    # Обработка некорректных значений без падений
    sparkline.add_value("invalid")
    assert sparkline.latest_value == 0.0

    # Очистка
    sparkline.clear()
    assert sparkline.count == 0
    assert sparkline.latest_value == 0.0


def test_sparkline_set_data_and_ring_buffer(qapp):
    """Проверка пакетной загрузки данных и связки с RingBuffer."""
    sparkline = SparklineWidget(maxlen=10)

    sparkline.set_data([1.0, 2.0, 3.0, 4.0])
    assert sparkline.count == 4
    assert sparkline.latest_value == 4.0

    # Интеграция с RingBuffer ядра
    ring = RingBuffer(maxlen=5)
    ring.append(45.0)
    ring.append(55.0)
    ring.append(72.0)

    sparkline.set_ring_buffer(ring)
    assert sparkline.count == 3
    assert sparkline.latest_value == 72.0


def test_sparkline_adaptive_palette(qapp):
    """
    Проверка адаптивной пороговой палитры:
      - <60°C: Cyan (#38bdf8)
      - 60–78°C / <80°C: Amber (#f59e0b)
      - >=80°C: Crimson (#ef4444)
    """
    sparkline = SparklineWidget(warning_threshold=60.0, critical_threshold=80.0)

    # Норма: <60°C
    sparkline.add_value(45.0)
    assert sparkline.get_current_color().name().lower() == "#38bdf8"

    # Предупреждение: 60-78°C
    sparkline.add_value(65.0)
    assert sparkline.get_current_color().name().lower() == "#f59e0b"

    # Критично: >=80°C
    sparkline.add_value(82.0)
    assert sparkline.get_current_color().name().lower() == "#ef4444"

    # Граничные значения
    sparkline.add_value(60.0)
    assert sparkline.get_current_color().name().lower() == "#f59e0b"

    sparkline.add_value(80.0)
    assert sparkline.get_current_color().name().lower() == "#ef4444"


def test_sparkline_custom_thresholds_and_fixed_color(qapp):
    """Проверка кастомных порогов и режима фиксированного цвета."""
    sparkline = SparklineWidget(fixed_color="#10b981")
    sparkline.add_value(99.0)
    # Фиксированный цвет должен игнорировать пороги
    assert sparkline.get_current_color().name().lower() == "#10b981"

    # Сброс фиксированного цвета возвращает адаптивную логику
    sparkline.set_fixed_color(None)
    assert sparkline.get_current_color().name().lower() == "#ef4444"

    # Настройка новых порогов
    sparkline.set_thresholds(warning=30.0, critical=50.0)
    sparkline.add_value(40.0)
    assert sparkline.get_current_color().name().lower() == "#f59e0b"


def test_sparkline_paint_event_render(qapp):
    """Проверка рендеринга QPainter без исключений (0, 1, 2 и много точек)."""
    sparkline = SparklineWidget(maxlen=60)
    sparkline.resize(200, 60)

    # 1. Рендеринг пустого виджета
    pixmap = QPixmap(200, 60)
    sparkline.render(pixmap)

    # 2. Рендеринг с 1 точкой
    sparkline.add_value(50.0)
    sparkline.render(pixmap)

    # 3. Рендеринг с 2 точками (линия)
    sparkline.add_value(55.0)
    sparkline.render(pixmap)

    # 4. Рендеринг сглаженной Bezier-кривой (60 точек)
    sparkline.set_data([40.0 + (i % 15) for i in range(60)])
    sparkline.render(pixmap)

    # 5. Проверка константных данных (защита от деления на ноль)
    sparkline.set_data([42.0] * 30)
    sparkline.render(pixmap)
    assert sparkline.count == 30


def test_sparkline_high_frequency_memory_stability(qapp):
    """
    Проверка SparklineWidget на непрерывный высокочастотный поток данных (50 000 точек).
    Размер внутреннего буфера строго фиксирован maxlen=60 без утечек памяти.
    """
    sparkline = SparklineWidget(maxlen=60)

    for i in range(50_000):
        sparkline.add_value(float(i % 100))

    assert sparkline.count == 60
    assert sparkline.latest_value == float((50_000 - 1) % 100)


def test_sparkline_non_finite_and_extreme_values(qapp):
    """Проверка устойчивости к нечисловым и экстремальным значениям (NaN, Inf, Overflow)."""
    import math

    sparkline = SparklineWidget(maxlen=10)
    pixmap = QPixmap(200, 60)

    # Добавление некорректных значений не должно вызывать исключений
    sparkline.add_value(float("nan"))
    sparkline.add_value(float("inf"))
    sparkline.add_value(float("-inf"))
    sparkline.add_value(1e15)
    sparkline.add_value(-1e15)

    assert sparkline.count == 5
    # Рендеринг с экстремальными/NaN значениями должен безопасно завершаться
    sparkline.render(pixmap)


def test_sparkline_geometry_edge_cases(qapp):
    """Проверка рендеринга при критических и нулевых геометрических размерах виджета."""
    sparkline = SparklineWidget(maxlen=20)
    sparkline.set_data([10.0, 20.0, 30.0, 40.0])

    for size in [(0, 0), (1, 1), (5, 5), (9, 5), (10, 6), (944, 600)]:
        sparkline.resize(*size)
        pixmap = QPixmap(*size if size[0] > 0 and size[1] > 0 else (1, 1))
        sparkline.render(pixmap)

