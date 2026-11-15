"""
Платформенные Win32/COM драйверы управления аудиосистемой Windows.
"""
from modules.audio.platform.device_switcher import (
    ALL_ROLES,
    CLSID_PolicyConfigClient,
    DEVICE_STATE_ACTIVE,
    IID_IPolicyConfig,
    IPolicyConfig,
    PKEY_DEVICE_FRIENDLY_NAME,
    RENDER_DEVICE_PREFIX,
    ROLE_COMMUNICATIONS,
    ROLE_CONSOLE,
    ROLE_MULTIMEDIA,
    get_default_playback_device_id,
    get_playback_devices,
    switch_default_device,
    toggle_audio_device,
)

__all__ = [
    "ALL_ROLES",
    "CLSID_PolicyConfigClient",
    "DEVICE_STATE_ACTIVE",
    "IID_IPolicyConfig",
    "IPolicyConfig",
    "PKEY_DEVICE_FRIENDLY_NAME",
    "RENDER_DEVICE_PREFIX",
    "ROLE_COMMUNICATIONS",
    "ROLE_CONSOLE",
    "ROLE_MULTIMEDIA",
    "get_default_playback_device_id",
    "get_playback_devices",
    "switch_default_device",
    "toggle_audio_device",
]
