"""
Подсистема сенсорного аудиомикшера DuckDock.
"""
from modules.audio.models import APP_FRIENDLY_NAMES, AudioDeviceInfo, AudioSessionInfo
from modules.audio.service import AudioManager
from modules.audio.view import AudioMixerView

__all__ = [
    "AudioManager",
    "AudioDeviceInfo",
    "AudioSessionInfo",
    "APP_FRIENDLY_NAMES",
    "AudioMixerView",
]
