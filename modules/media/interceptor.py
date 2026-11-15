"""
Сетевой перехватчик запросов (AdBlockInterceptor) для DuckDock WebEngine.
Блокирует рекламные скрипты, трекеры и баннерные сети на уровне сокетов Chromium,
а также осуществляет динамический спуфинг User-Agent на Firefox для шлюзов авторизации
Google Accounts (обход блокировки 'This browser or app may not be secure').
"""
from typing import Tuple
from PySide6.QtCore import QObject

try:
    from PySide6.QtWebEngineCore import (
        QWebEngineUrlRequestInterceptor,
        QWebEngineUrlRequestInfo,
    )
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    # Mock-класс для работы без установленного WebEngine
    class QWebEngineUrlRequestInterceptor(QObject):
        pass
    class QWebEngineUrlRequestInfo:
        pass


# Актуальный User-Agent Chrome Desktop для основного воспроизведения YouTube Music
DESKTOP_CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

# User-Agent Firefox для авторизации Google (Google не запускает проверки проприетарного Chrome)
FIREFOX_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) "
    "Gecko/20100101 Firefox/130.0"
)


class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    """
    Перехватчик URL-запросов для изоляции медиаплеера от рекламных ресурсов
    и обхода блокировки авторизации Google Accounts.
    """

    BLOCKED_DOMAINS: Tuple[str, ...] = (
        "googlesyndication.com",
        "doubleclick.net",
        "googleadservices.com",
        "google-analytics.com",
        "adservice.google.com",
        "pagead2.googlesyndication.com",
        "static.doubleclick.net",
    )

    BLOCKED_PATTERNS: Tuple[str, ...] = (
        "/api/stats/ads",
        "/pagead/",
        "/ptracking",
        "play.google.com/log",
    )

    AUTH_DOMAINS: Tuple[str, ...] = (
        "accounts.google.com",
        "accounts.youtube.com",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocked_count = 0
        self._auth_spoof_count = 0

    @property
    def blocked_count(self) -> int:
        """Возвращает суммарное количество заблокированных сетевых запросов."""
        return self._blocked_count

    @property
    def auth_spoof_count(self) -> int:
        """Возвращает количество запросов к авторизации Google с подменой User-Agent."""
        return self._auth_spoof_count

    def is_blocked_url(self, url: str) -> bool:
        """
        Проверяет, подлежит ли URL блокировке по сигнатурам доменов или путей.
        """
        if not url:
            return False

        lower_url = url.lower()

        # 1. Проверка совпадения по доменам
        for domain in self.BLOCKED_DOMAINS:
            if domain in lower_url:
                return True

        # 2. Проверка сигнатур путей
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in lower_url:
                return True

        return False

    def is_auth_url(self, url: str) -> bool:
        """
        Проверяет, направлен ли сетевой запрос к доменам авторизации Google / YouTube Accounts.
        """
        if not url:
            return False
        lower_url = url.lower()
        return any(domain in lower_url for domain in self.AUTH_DOMAINS)

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        """
        Обратный вызов Chromium при инициации сетевого запроса.
        """
        try:
            req_url = info.requestUrl().toString()
            if self.is_blocked_url(req_url):
                info.block(True)
                self._blocked_count += 1
            elif self.is_auth_url(req_url):
                # Подменяем заголовок на Firefox для беспрепятственного прохождения логина
                info.setHttpHeader(b"User-Agent", FIREFOX_UA.encode("ascii"))
                self._auth_spoof_count += 1
        except Exception:
            # Изолируем любые исключения внутри потока перехватчика WebEngine
            pass


__all__ = [
    "AdBlockInterceptor",
    "DESKTOP_CHROME_UA",
    "FIREFOX_UA",
]
