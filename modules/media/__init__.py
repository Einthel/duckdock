"""
Подсистема медиа, браузерного профиля и YouTube Music для DuckDock.
"""
from modules.media.interceptor import (
    AdBlockInterceptor,
    DESKTOP_CHROME_UA,
    FIREFOX_UA,
)
from modules.media.web_profile import (
    WebProfileManager,
    MAX_DISK_CACHE_BYTES,
)
from modules.media.view import YouTubeView

__all__ = [
    "AdBlockInterceptor",
    "DESKTOP_CHROME_UA",
    "FIREFOX_UA",
    "WebProfileManager",
    "MAX_DISK_CACHE_BYTES",
    "YouTubeView",
]
