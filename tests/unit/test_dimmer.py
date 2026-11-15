"""
Тестирование оверлея затемнения (DimmerOverlay) и кинетики анимации.
"""
import pytest
from PySide6.QtCore import Qt, QEasingCurve
from PySide6.QtTest import QTest
from core.config import AppConfig
from core.event_bus import bus
from ui.dimmer_overlay import DimmerOverlay
from ui.main_window import MainWindow
from ui.showcase_view import ShowcaseView


@pytest.mark.unit
def test_dimmer_opacity_clamping(qapp):
    dimmer = DimmerOverlay()
    dimmer.opacity = -0.5
    assert dimmer.opacity == 0.0

    dimmer.opacity = 1.5
    assert dimmer.opacity == 0.95

    dimmer.opacity = 0.5
    assert dimmer.opacity == 0.5


@pytest.mark.unit
def test_dimmer_toggle(qapp):
    dimmer = DimmerOverlay()
    assert dimmer.opacity == 0.0

    # Включение затемнения (анимация 200 мс)
    dimmer.toggle(0.50)
    assert dimmer.target_opacity == 0.50
    assert dimmer.is_animating is True
    QTest.qWait(250)
    assert pytest.approx(dimmer.opacity, abs=0.02) == 0.50
    assert dimmer.is_animating is False

    # Выключение затемнения (анимация 200 мс)
    dimmer.toggle()
    assert dimmer.target_opacity == 0.0
    assert dimmer.is_animating is True
    QTest.qWait(250)
    assert pytest.approx(dimmer.opacity, abs=0.02) == 0.0
    assert dimmer.is_animating is False


@pytest.mark.unit
def test_dimmer_toggle_instant(qapp):
    dimmer = DimmerOverlay()
    assert dimmer.opacity == 0.0

    # Мгновенное переключение без анимации
    dimmer.toggle(0.50, animated=False)
    assert dimmer.opacity == 0.50

    dimmer.toggle(animated=False)
    assert dimmer.opacity == 0.0


@pytest.mark.unit
def test_dimmer_animation_configuration(qapp):
    """Проверка конфигурации аниматора: длительность 200 мс и кривая OutCubic."""
    dimmer = DimmerOverlay()
    assert hasattr(dimmer, "_anim")
    assert dimmer._anim.duration() == 200
    assert dimmer._anim.easingCurve().type() == QEasingCurve.Type.OutCubic
    assert dimmer.is_animating is False


@pytest.mark.unit
def test_dimmer_animation_reversal_mid_flight(qapp):
    """Проверка смены направления анимации на лету без рывков."""
    dimmer = DimmerOverlay()
    assert dimmer.opacity == 0.0

    # Запуск включения (цель 0.50)
    dimmer.toggle(0.50)
    assert dimmer.target_opacity == 0.50
    assert dimmer.is_animating is True

    # Ждем 60 мс (промежуточная фаза анимации)
    QTest.qWait(60)
    mid_opacity = dimmer.opacity
    assert 0.0 < mid_opacity < 0.50

    # Повторный вызов во время анимации вверх должен реверсировать цель к 0.0
    dimmer.toggle()
    assert dimmer.target_opacity == 0.0
    assert dimmer.is_animating is True

    # Дожидаемся завершения обратной анимации
    QTest.qWait(250)
    assert pytest.approx(dimmer.opacity, abs=0.02) == 0.0
    assert dimmer.is_animating is False


@pytest.mark.unit
def test_dimmer_rapid_toggle_calls(qapp):
    """Проверка устойчивости при многократном быстром нажатии (bounce / rapid taps)."""
    dimmer = DimmerOverlay()

    # Быстрые последовательные клики
    dimmer.toggle(0.50)
    dimmer.toggle(0.50)
    dimmer.toggle(0.50)

    # После нечетного числа переключений цель должна быть 0.50
    assert dimmer.target_opacity == 0.50
    QTest.qWait(250)
    assert pytest.approx(dimmer.opacity, abs=0.02) == 0.50
    assert dimmer.is_animating is False


@pytest.mark.unit
def test_dimmer_set_level_animated_vs_immediate(qapp):
    """Проверка раздельного поведения set_dimmer_level: с анимацией и мгновенно."""
    dimmer = DimmerOverlay()

    # С анимацией
    dimmer.set_dimmer_level(0.40, animated=True)
    assert dimmer.target_opacity == 0.40
    assert dimmer.is_animating is True
    QTest.qWait(250)
    assert pytest.approx(dimmer.opacity, abs=0.02) == 0.40

    # Мгновенно прерывает и устанавливает уровень
    dimmer.set_dimmer_level(0.20, animated=False)
    assert dimmer.opacity == 0.20
    assert dimmer.target_opacity == 0.20
    assert dimmer.is_animating is False


@pytest.mark.unit
def test_dimmer_stealth_focus_and_transparency_invariants(qapp):
    """Проверка инвариантов Stealth Focus и сквозного клика."""
    dimmer = DimmerOverlay()

    # Сквозной клик
    assert dimmer.testAttribute(Qt.WA_TransparentForMouseEvents) is True
    assert dimmer.testAttribute(Qt.WA_NoSystemBackground) is True
    assert dimmer.testAttribute(Qt.WA_ShowWithoutActivating) is True

    # Защитник фокуса
    assert dimmer.focusPolicy() == Qt.NoFocus


@pytest.mark.unit
def test_dimmer_event_bus_emission_during_animation(qapp):
    """Проверка регулярной эмиссии сигнала dimmer_opacity_changed во время анимации."""
    dimmer = DimmerOverlay()
    emitted_values = []

    def on_change(val):
        emitted_values.append(val)

    bus.dimmer_opacity_changed.connect(on_change)
    try:
        dimmer.toggle(0.50)
        QTest.qWait(250)
        assert len(emitted_values) > 1
        assert pytest.approx(emitted_values[-1], abs=0.02) == 0.50
    finally:
        bus.dimmer_opacity_changed.disconnect(on_change)


@pytest.mark.unit
def test_dimmer_paint_event_render(qapp):
    """Проверка paintEvent при нулевой и ненулевой непрозрачности."""
    dimmer = DimmerOverlay()
    dimmer.resize(1024, 600)

    # При 0.0 paintEvent оптимизирован и не вызывает падений
    dimmer.opacity = 0.0
    dimmer.repaint()

    # При 0.50 paintEvent заполняет оверлей полупрозрачным цветом
    dimmer.opacity = 0.50
    dimmer.repaint()
    assert dimmer.opacity == 0.50


@pytest.mark.unit
def test_main_window_dimmer_integration(qapp):
    config = AppConfig()
    win = MainWindow(config)
    assert hasattr(win, "dimmer")
    assert win.dimmer.opacity == 0.0

    # Запрос на переключение диммера через EventBus
    bus.dimmer_toggle_requested.emit()
    assert win.dimmer.target_opacity == config.dimmer.night_mode_opacity
    QTest.qWait(350)
    assert pytest.approx(win.dimmer.opacity, abs=0.02) == config.dimmer.night_mode_opacity

    # Повторный запрос — отключение
    bus.dimmer_toggle_requested.emit()
    assert win.dimmer.target_opacity == 0.0
    QTest.qWait(350)
    assert pytest.approx(win.dimmer.opacity, abs=0.02) == 0.0

    win.close()


@pytest.mark.unit
def test_showcase_view_dimmer_button_toggle(qapp):
    config = AppConfig()
    view = ShowcaseView(config)

    # Проверяем начальное состояние кнопки
    assert "Включить" in view.btn_test_dimmer.text()

    # Эмулируем включение диммера
    bus.dimmer_opacity_changed.emit(0.50)
    assert "Выключить" in view.btn_test_dimmer.text()
    assert view.lbl_dimmer_status is not None
    assert "50%" in view.lbl_dimmer_status.text()

    # Эмулируем выключение диммера
    bus.dimmer_opacity_changed.emit(0.0)
    assert "Включить" in view.btn_test_dimmer.text()
    assert "0%" in view.lbl_dimmer_status.text()

    view.close()
