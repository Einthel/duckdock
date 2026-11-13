"""
Тестирование загрузки и валидации конфигурации.
"""
import pytest
from pathlib import Path
from core.config import load_config, AppConfig

@pytest.mark.unit
def test_default_config_values():
    config = AppConfig()
    assert config.display.width == 1024
    assert config.display.height == 600
    assert config.layout.sidebar_width == 80
    assert config.layout.workspace_width == 944
    assert config.stealth.enable_stealth_focus is True
    assert config.dimmer.night_mode_opacity == 0.85

@pytest.mark.unit
def test_load_config_from_file(tmp_path):
    test_json = tmp_path / "test_config.json"
    test_json.write_text("""{
        "display": {"width": 1024, "height": 768},
        "layout": {"sidebar_width": 100}
    }""", encoding="utf-8")

    cfg = load_config(test_json)
    assert cfg.display.width == 1024
    assert cfg.display.height == 768
    assert cfg.layout.sidebar_width == 100
    # Проверка дефолтных значений для неуказанных полей
    assert cfg.stealth.enable_stealth_focus is True

@pytest.mark.unit
def test_load_nonexistent_config():
    cfg = load_config(Path("/nonexistent/path/config.json"))
    assert cfg.display.width == 1024
