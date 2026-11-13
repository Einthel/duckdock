"""
Тестирование инициализации DPI Awareness.
"""
import sys
import pytest
from core.dpi import init_dpi_awareness

@pytest.mark.unit
def test_dpi_awareness_init():
    # На Windows вызов должен возвращать True или корректно отрабатывать без исключений
    result = init_dpi_awareness()
    if sys.platform == "win32":
        assert isinstance(result, bool)
    else:
        assert result is False
