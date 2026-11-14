"""
Unit-тесты для WebProfileManager и AdBlockInterceptor (Спринт 4).
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from PySide6.QtCore import QUrl

from core.web_interceptor import AdBlockInterceptor
from core.web_profile import WebProfileManager, DESKTOP_CHROME_UA, MAX_DISK_CACHE_BYTES

try:
    from PySide6.QtWebEngineCore import (
        QWebEngineProfile,
        QWebEngineUrlRequestInfo,
    )
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False


@pytest.mark.unit
def test_adblock_interceptor_url_filtering():
    """Тестирование правил блокировки рекламных и трекерных URL."""
    interceptor = AdBlockInterceptor()

    # Заблокированные URL
    assert interceptor.is_blocked_url("https://pagead2.googlesyndication.com/pagead/js/ads.js")
    assert interceptor.is_blocked_url("https://static.doubleclick.net/instream/ad_status.js")
    assert interceptor.is_blocked_url("https://googleadservices.com/pagead/conversion/")
    assert interceptor.is_blocked_url("https://www.google-analytics.com/analytics.js")
    assert interceptor.is_blocked_url("https://adservice.google.com/adsid/integrator.js")
    assert interceptor.is_blocked_url("https://music.youtube.com/api/stats/ads?v=test")
    assert interceptor.is_blocked_url("https://www.youtube.com/pagead/parallel")
    assert interceptor.is_blocked_url("https://www.youtube.com/ptracking?video_id=123")
    assert interceptor.is_blocked_url("https://play.google.com/log?format=json&hasfast=true")

    # Разрешенные URL (контент и аудиопотоки)
    assert not interceptor.is_blocked_url("https://music.youtube.com/")
    assert not interceptor.is_blocked_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
    assert not interceptor.is_blocked_url("https://fonts.googleapis.com/css2?family=Roboto")
    assert not interceptor.is_blocked_url("https://lh3.googleusercontent.com/some_album_art")
    assert not interceptor.is_blocked_url("")


@pytest.mark.unit
def test_adblock_interceptor_request_blocking():
    """Проверка вызова info.block(True) при перехвате запроса."""
    interceptor = AdBlockInterceptor()
    assert interceptor.blocked_count == 0

    # Создаем mock для QWebEngineUrlRequestInfo
    mock_info = MagicMock()
    mock_info.requestUrl.return_value = QUrl("https://static.doubleclick.net/ads.js")

    interceptor.interceptRequest(mock_info)
    mock_info.block.assert_called_once_with(True)
    assert interceptor.blocked_count == 1

    # Запрос легитимного URL не должен блокироваться
    mock_info_clean = MagicMock()
    mock_info_clean.requestUrl.return_value = QUrl("https://music.youtube.com/browse")
    interceptor.interceptRequest(mock_info_clean)
    mock_info_clean.block.assert_not_called()
    assert interceptor.blocked_count == 1


@pytest.mark.unit
def test_adblock_interceptor_auth_spoofing():
    """Проверка подмены User-Agent на Firefox для доменов Google Accounts."""
    from core.web_interceptor import FIREFOX_UA
    interceptor = AdBlockInterceptor()

    assert interceptor.is_auth_url("https://accounts.google.com/v3/signin/identifier")
    assert interceptor.is_auth_url("https://accounts.youtube.com/accounts/SetSID")
    assert not interceptor.is_auth_url("https://music.youtube.com/")

    # Перехват запроса к Google Accounts
    mock_info_auth = MagicMock()
    mock_info_auth.requestUrl.return_value = QUrl("https://accounts.google.com/signin")
    interceptor.interceptRequest(mock_info_auth)

    mock_info_auth.block.assert_not_called()
    mock_info_auth.setHttpHeader.assert_called_once_with(
        b"User-Agent", FIREFOX_UA.encode("ascii")
    )
    assert interceptor.auth_spoof_count == 1


@pytest.mark.unit
def test_web_profile_manager_singleton_and_paths(qapp, tmp_path):
    """Проверка синглтона WebProfileManager, путей к хранилищу и кэшу."""
    WebProfileManager.reset_instance()
    mgr = WebProfileManager.get_instance(base_dir=tmp_path)

    assert mgr.storage_path.exists()
    assert mgr.cache_path.exists()
    assert mgr.storage_path == tmp_path / "storage"
    assert mgr.cache_path == tmp_path / "cache"

    profile = mgr.get_profile()
    if HAS_WEBENGINE:
        assert profile is not None
        assert profile.storageName() == "DuckDock_WebProfile"
        assert profile.httpUserAgent() == DESKTOP_CHROME_UA
        assert profile.httpCacheMaximumSize() == MAX_DISK_CACHE_BYTES
        assert profile.httpCacheType() == QWebEngineProfile.HttpCacheType.DiskHttpCache
        assert (
            profile.persistentCookiesPolicy()
            == QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        assert mgr.interceptor is not None

        # Проверка внедренных скриптов
        scripts = profile.scripts().toList()
        script_names = [s.name() for s in scripts]
        assert "DuckDock_Touch_Theme" in script_names
        assert "DuckDock_AdBlock_Watcher" in script_names
        assert "DuckDock_Google_Auth_Evasion" in script_names

    WebProfileManager.reset_instance()
