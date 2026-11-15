"""
Подсистема настроек и конфигурации DuckDock.
"""
from modules.settings.config import (
    AppConfig,
    DimmerConfig,
    DisplayConfig,
    LayoutConfig,
    StealthConfig,
    TrackedAppConfig,
    load_config,
)
from modules.settings.view import SETTINGS_QSS, SettingsView

__all__ = [
    "AppConfig",
    "DisplayConfig",
    "LayoutConfig",
    "StealthConfig",
    "DimmerConfig",
    "TrackedAppConfig",
    "load_config",
    "SettingsView",
    "SETTINGS_QSS",
]
