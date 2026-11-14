"""
Синглтон управления постоянным профилем Chromium WebEngine (WebProfileManager).
Обеспечивает сохранение cookies авторизации Google, ограничение дискового кэша до 256 МБ,
динамический обход блокировки 'This browser or app may not be secure'
и внедрение CSS/JS скриптов тач-интерфейса и блокировки рекламы.
"""
import os
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject

from core.web_interceptor import (
    AdBlockInterceptor,
    DESKTOP_CHROME_UA,
    FIREFOX_UA,
)

try:
    from PySide6.QtWebEngineCore import (
        QWebEngineProfile,
        QWebEngineSettings,
        QWebEngineScript,
    )
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    class QWebEngineProfile(QObject):
        pass
    class QWebEngineSettings:
        PlaybackRequiresUserGesture = 0
        JavascriptEnabled = 1
        LocalStorageEnabled = 2
        LocalContentCanAccessRemoteUrls = 3
        ScrollAnimatorEnabled = 4
    class QWebEngineScript:
        class InjectionPoint:
            DocumentReady = 0
            DocumentCreation = 1
        class ScriptWorldId:
            MainWorld = 0


# Жесткий лимит кэша на диске: 256 МБ
MAX_DISK_CACHE_BYTES = 256 * 1024 * 1024


class WebProfileManager:
    """
    Менеджер постоянного изолированного профиля QWebEngineProfile.
    """
    _instance: Optional["WebProfileManager"] = None

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                self.base_dir = Path(local_appdata) / "DuckDock" / "web_profile"
            else:
                self.base_dir = Path.home() / ".duckdock" / "web_profile"
        else:
            self.base_dir = Path(base_dir)

        self.storage_path = self.base_dir / "storage"
        self.cache_path = self.base_dir / "cache"

        # Создаем необходимые директории профиля
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.cache_path.mkdir(parents=True, exist_ok=True)

        self.profile: Optional[QWebEngineProfile] = None
        self.interceptor: Optional[AdBlockInterceptor] = None

        if HAS_WEBENGINE:
            self._init_profile()

    @classmethod
    def get_instance(cls, base_dir: Optional[Path] = None) -> "WebProfileManager":
        """Возвращает глобальный синглтон менеджера веб-профиля."""
        if cls._instance is None:
            cls._instance = cls(base_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Сброс синглтона (используется для изоляции тестов)."""
        cls._instance = None

    def _init_profile(self):
        """Инициализация и тюнинг параметров QWebEngineProfile."""
        self.profile = QWebEngineProfile("DuckDock_WebProfile")
        self.profile.setPersistentStoragePath(str(self.storage_path))
        self.profile.setCachePath(str(self.cache_path))

        # Принудительное постоянное хранение cookies для долговременной авторизации
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        # Ограничение дискового кэша до 256 МБ
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setHttpCacheMaximumSize(MAX_DISK_CACHE_BYTES)

        # Подмена User-Agent по умолчанию на актуальный Chrome Desktop
        self.profile.setHttpUserAgent(DESKTOP_CHROME_UA)

        # Настройки рендерера и безопасности
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        # Установка сетевого блокировщика рекламы и спуфера User-Agent
        self.interceptor = AdBlockInterceptor(self.profile)
        self.profile.setUrlRequestInterceptor(self.interceptor)

        # Внедрение скриптов темы оформления, DOM-блокировщика и обхода проверки Google Auth
        self._inject_user_scripts()

    def _inject_user_scripts(self):
        """Загрузка и инжекция CSS-темы и JS-скриптов в DOM через QWebEngineScript."""
        if not HAS_WEBENGINE or self.profile is None:
            return

        project_root = Path(__file__).resolve().parent.parent
        css_file = project_root / "resources" / "css" / "ytm_touch_theme.css"
        js_file = project_root / "resources" / "js" / "ytm_touch_adblock.js"

        # 1. Инжекция CSS темы через JS-обертку на DocumentReady
        if css_file.exists():
            css_content = css_file.read_text(encoding="utf-8")
            safe_css = css_content.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            theme_js = f"""
            (function() {{
                function injectTheme() {{
                    if (document.getElementById('duckdock-ytm-theme')) return;
                    const style = document.createElement('style');
                    style.id = 'duckdock-ytm-theme';
                    style.textContent = `{safe_css}`;
                    (document.head || document.documentElement).appendChild(style);
                }}
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', injectTheme);
                }} else {{
                    injectTheme();
                }}
            }})();
            """
            script_theme = QWebEngineScript()
            script_theme.setName("DuckDock_Touch_Theme")
            script_theme.setSourceCode(theme_js)
            script_theme.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
            script_theme.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script_theme.setRunsOnSubFrames(False)
            self.profile.scripts().insert(script_theme)

        # 2. Инжекция JS AdBlock & Media Watcher
        if js_file.exists():
            js_content = js_file.read_text(encoding="utf-8")
            script_adblock = QWebEngineScript()
            script_adblock.setName("DuckDock_AdBlock_Watcher")
            script_adblock.setSourceCode(js_content)
            script_adblock.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
            script_adblock.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script_adblock.setRunsOnSubFrames(False)
            self.profile.scripts().insert(script_adblock)

        # 3. Инжекция скрипта обхода анти-бот детекции Google Auth ('This browser or app may not be secure')
        # Запускается на этапе DocumentCreation ДО выполнения любых скриптов страницы
        auth_evasion_js = f"""
        (function() {{
            const host = (window.location && window.location.hostname) || '';
            if (host.includes('accounts.google') || host.includes('accounts.youtube')) {{
                const ffUA = '{FIREFOX_UA}';
                try {{
                    Object.defineProperty(navigator, 'userAgent', {{
                        get: function() {{ return ffUA; }},
                        configurable: true
                    }});
                    Object.defineProperty(navigator, 'appVersion', {{
                        get: function() {{ return '5.0 (Windows)'; }},
                        configurable: true
                    }});
                    Object.defineProperty(navigator, 'platform', {{
                        get: function() {{ return 'Win32'; }},
                        configurable: true
                    }});
                    Object.defineProperty(navigator, 'webdriver', {{
                        get: function() {{ return false; }},
                        configurable: true
                    }});
                    Object.defineProperty(navigator, 'userAgentData', {{
                        get: function() {{ return undefined; }},
                        configurable: true
                    }});
                    if (window.chrome) {{
                        try {{
                            delete window.chrome;
                        }} catch (e) {{}}
                    }}
                }} catch (e) {{
                    console.debug('[DuckDock] Google Auth evasion patch error:', e);
                }}
            }}
        }})();
        """
        script_evasion = QWebEngineScript()
        script_evasion.setName("DuckDock_Google_Auth_Evasion")
        script_evasion.setSourceCode(auth_evasion_js)
        script_evasion.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script_evasion.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script_evasion.setRunsOnSubFrames(True)
        self.profile.scripts().insert(script_evasion)

    def get_profile(self) -> Optional[QWebEngineProfile]:
        """Возвращает настроенный экземпляр QWebEngineProfile."""
        return self.profile
