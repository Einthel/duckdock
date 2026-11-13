"""
Тестирование оверлея затемнения (DimmerOverlay).
"""
import pytest
from ui.dimmer_overlay import DimmerOverlay

@pytest.mark.gui
def test_dimmer_opacity_clamping(qapp):
    dimmer = DimmerOverlay()
    dimmer.opacity = -0.5
    assert dimmer.opacity == 0.0

    dimmer.opacity = 1.5
    assert dimmer.opacity == 0.95

    dimmer.opacity = 0.5
    assert dimmer.opacity == 0.5

@pytest.mark.gui
def test_dimmer_toggle(qapp):
    dimmer = DimmerOverlay()
    assert dimmer.opacity == 0.0

    # Включение затемнения
    dimmer.toggle(0.85)
    assert dimmer.opacity == 0.85

    # Выключение затемнения
    dimmer.toggle()
    assert dimmer.opacity == 0.0
