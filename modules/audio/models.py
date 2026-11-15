"""
Декларативные модели данных и схемы аудиоподсистемы DuckDock.
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field


# Словарь дружелюбных имен для известных приложений
APP_FRIENDLY_NAMES: Dict[str, str] = {
    "chrome.exe": "Google Chrome",
    "browser.exe": "Yandex Browser",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "opera.exe": "Opera",
    "discord.exe": "Discord",
    "telegram.exe": "Telegram",
    "spotify.exe": "Spotify",
    "steam.exe": "Steam",
    "vlc.exe": "VLC Media Player",
    "mpv.exe": "MPV Player",
    "foobar2000.exe": "Foobar2000",
    "obs64.exe": "OBS Studio",
    "xboxpcapp.exe": "Xbox App",
    "devenv.exe": "Visual Studio",
    "code.exe": "VS Code",
    "pycharm64.exe": "PyCharm",
    "happ.exe": "happ Proxy",
    "wmplayer.exe": "Windows Media Player",
}


class AudioSessionInfo(BaseModel):
    """Модель данных аудиосессии приложения."""
    pid: Optional[int] = Field(default=None, description="ID процесса (0 или None для системных звуков)")
    name: str = Field(default="Unknown", description="Понятное отображаемое имя")
    process_name: str = Field(default="", description="Имя процесса (например browser.exe)")
    exe_path: Optional[str] = Field(default=None, description="Полный путь к исполняемому файлу")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Уровень громкости от 0.0 до 1.0")
    is_muted: bool = Field(default=False, description="Флаг отключения звука")
    is_active: bool = Field(default=True, description="Флаг активности воспроизведения")


class AudioDeviceInfo(BaseModel):
    """Информация об аудиоустройстве вывода/ввода."""
    id: str = Field(description="Идентификатор устройства Windows Endpoint")
    name: str = Field(description="Отображаемое имя (FriendlyName)")
    is_default: bool = Field(default=False, description="Является ли текущим по умолчанию")
    state: int = Field(default=1, description="Состояние (1 = DEVICE_STATE_ACTIVE)")


__all__ = [
    "APP_FRIENDLY_NAMES",
    "AudioSessionInfo",
    "AudioDeviceInfo",
]
