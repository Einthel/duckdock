"""
Менеджер подсистемы интернационализации (I18nManager).
Обеспечивает быстрое разрешение ключей dot-notation за O(1), симметричный fallback,
безопасную интерполяцию параметров и переключение языка на лету через EventBus.
"""
import json
import logging
import string
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.i18n.plural import resolve_plural_category

logger = logging.getLogger("duckdock.i18n")

Number = Union[int, float]
VALID_PLURAL_KEYS = {"one", "few", "many", "other"}


def _is_plural_leaf(d: Any) -> bool:
    """Проверяет, является ли словарь конечным объектом плюрализации."""
    if not isinstance(d, dict) or not d:
        return False
    return set(d.keys()).issubset(VALID_PLURAL_KEYS)


def _flatten_dict(nested: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """
    Рекурсивно разворачивает вложенный словарь в плоскую структуру dot-notation.
    Конечные объекты плюрализации сохраняются как единый dict под составным ключом родителя.
    """
    flattened: Dict[str, Any] = {}
    for key, value in nested.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            if _is_plural_leaf(value):
                flattened[full_key] = value
            else:
                flattened.update(_flatten_dict(value, prefix=full_key))
        else:
            flattened[full_key] = value
    return flattened


class SafeFormatter(string.Formatter):
    """
    Безопасный форматтер строк.
    Предотвращает фатальные сбои (KeyError, IndexError, ValueError) при вызове с неполным набором аргументов.
    Непереданные плейсхолдеры остаются в строке в неизменном виде {param}.
    """

    def get_value(self, key: Union[str, int], args: tuple, kwargs: dict) -> Any:
        if isinstance(key, str):
            return kwargs.get(key, f"{{{key}}}")
        if isinstance(key, int):
            if 0 <= key < len(args):
                return args[key]
            return f"{{{key}}}"
        return f"{{{key}}}"

    def format_field(self, value: Any, format_spec: str) -> str:
        try:
            return super().format_field(value, format_spec)
        except Exception:
            return str(value)

    def safe_format(self, format_string: str, *args: Any, **kwargs: Any) -> str:
        """Безопасное форматирование строки с подавлением синтаксических ошибок в шаблоне."""
        if not format_string or not ("{" in format_string and "}" in format_string):
            return format_string
        try:
            return self.vformat(format_string, args, kwargs)
        except Exception:
            return format_string


class I18nManager:
    """
    Singleton-менеджер подсистемы локализации DuckDock.
    Хранит предзагруженные словари в оперативной памяти для доступа за O(1).
    """

    _instance: Optional["I18nManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> "I18nManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        locales_dir: Optional[Union[Path, str]] = None,
        default_lang: str = "ru",
    ) -> None:
        if getattr(self, "_initialized", False) and locales_dir is None:
            return

        with self._lock:
            target_dir = Path(locales_dir) if locales_dir else self._resolve_default_locales_dir()
            if getattr(self, "_initialized", False) and getattr(self, "_locales_dir", None) == target_dir:
                return

            self._formatter = SafeFormatter()
            self._locales_dir = target_dir
            self._current_lang = default_lang
            self._catalogs: Dict[str, Dict[str, Any]] = {"ru": {}, "en": {}}
            self._load_all_catalogs()
            self._active_catalog = self._catalogs.get(self._current_lang, {})
            self._initialized = True

    @staticmethod
    def _resolve_default_locales_dir() -> Path:
        """Определяет путь к каталогу locales как в исходном коде, так и в собранном exe."""
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            if (exe_dir / "locales").exists():
                return exe_dir / "locales"
            elif hasattr(sys, "_MEIPASS") and (Path(sys._MEIPASS) / "locales").exists():
                return Path(sys._MEIPASS) / "locales"
        return Path(__file__).resolve().parents[2] / "locales"

    def _load_all_catalogs(self) -> None:
        """Загружает и разворачивает все словари locales/*.json в память."""
        for lang in ("ru", "en"):
            file_path = self._locales_dir / f"{lang}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._catalogs[lang] = _flatten_dict(data)
                except Exception as e:
                    logger.error("Failed to load locale file '%s': %s", file_path, e)
                    self._catalogs[lang] = {}
            else:
                logger.warning("Locale file not found: '%s'", file_path)
                self._catalogs[lang] = {}

    def reload(self, locales_dir: Optional[Union[Path, str]] = None) -> None:
        """Перезагружает словари из указанного каталога (полезно для тестов)."""
        with self._lock:
            if locales_dir:
                self._locales_dir = Path(locales_dir)
            self._catalogs = {"ru": {}, "en": {}}
            self._load_all_catalogs()
            self._active_catalog = self._catalogs.get(self._current_lang, {})

    @classmethod
    def _reset_instance(cls) -> None:
        """Сброс экземпляра синглтона (для изоляции модульных тестов)."""
        with cls._lock:
            cls._instance = None

    @property
    def current_language(self) -> str:
        """Код текущего активного языка ('ru' | 'en')."""
        return self._current_lang

    def get_catalog(self, lang_code: str) -> Dict[str, Any]:
        """Возвращает плоский словарь переводов для указанного языка."""
        return dict(self._catalogs.get(lang_code, {}))

    def set_language(self, lang_code: str, emit_signal: bool = True) -> None:
        """
        Переключает активный язык интерфейса.
        Смена ссылки происходит атомарно за O(1).
        При emit_signal=True отправляет сигнал через EventBus.
        """
        if lang_code not in ("ru", "en"):
            raise ValueError(f"Unsupported language code '{lang_code}'. Supported languages: 'ru', 'en'")

        if self._current_lang == lang_code and self._active_catalog:
            return

        self._current_lang = lang_code
        self._active_catalog = self._catalogs.get(lang_code, {})

        if emit_signal:
            try:
                from core.event_bus import bus
                bus.language_changed.emit(lang_code)
            except Exception as e:
                logger.warning("Failed to emit language_changed signal: %s", e)

    def translate(self, key: str, **kwargs: Any) -> Any:
        """
        Возвращает локализованную строку по dot-notation ключу.
        Каскад поиска:
        1. Активный словарь (self._active_catalog)
        2. Резервный словарь противоположного языка (ru <-> en)
        3. Исходный ключ (с логированием warning)
        """
        val = self._active_catalog.get(key)
        if val is None and "." in key:
            parent_key, _, sub_key = key.rpartition(".")
            parent_val = self._active_catalog.get(parent_key)
            if isinstance(parent_val, dict) and sub_key in parent_val:
                val = parent_val[sub_key]

        if val is None:
            fallback_lang = "en" if self._current_lang == "ru" else "ru"
            fallback_catalog = self._catalogs.get(fallback_lang, {})
            val = fallback_catalog.get(key)
            if val is None and "." in key:
                parent_key, _, sub_key = key.rpartition(".")
                parent_val = fallback_catalog.get(parent_key)
                if isinstance(parent_val, dict) and sub_key in parent_val:
                    val = parent_val[sub_key]

            if val is not None:
                logger.debug("Translation key '%s' fell back to '%s'", key, fallback_lang)

        if val is None:
            logger.warning("Translation key not found: '%s'", key)
            return key

        if isinstance(val, str):
            return self._formatter.safe_format(val, **kwargs)
        return val

    def translate_plural(self, key: str, count: Number, **kwargs: Any) -> str:
        """
        Возвращает локализованную строку с учетом грамматической числовой формы (плюрализации).
        Автоматически передает параметр count в интерполяцию.
        """
        kwargs_with_count = dict(kwargs)
        kwargs_with_count.setdefault("count", count)

        plural_obj = self._active_catalog.get(key)
        lang_used = self._current_lang

        if plural_obj is None:
            fallback_lang = "en" if self._current_lang == "ru" else "ru"
            plural_obj = self._catalogs.get(fallback_lang, {}).get(key)
            if plural_obj is not None:
                lang_used = fallback_lang

        if plural_obj is None:
            logger.warning("Translation plural key not found: '%s'", key)
            return key

        if isinstance(plural_obj, dict):
            cat = resolve_plural_category(lang_used, count)
            template = None
            for candidate in (cat, "other", "many", "few", "one"):
                if candidate in plural_obj:
                    template = plural_obj[candidate]
                    break
            if template is None and plural_obj:
                template = next(iter(plural_obj.values()))

            if template is None:
                return key
            return self._formatter.safe_format(template, **kwargs_with_count)

        if isinstance(plural_obj, str):
            return self._formatter.safe_format(plural_obj, **kwargs_with_count)

        return str(plural_obj)


def t(key: str, **kwargs: Any) -> Any:
    """Глобальная функция локализации строки по ключу dot-notation."""
    return I18nManager().translate(key, **kwargs)


def tp(key: str, count: Number, **kwargs: Any) -> str:
    """Глобальная функция плюрализации строки по ключу и числу."""
    return I18nManager().translate_plural(key, count, **kwargs)


__all__ = [
    "I18nManager",
    "SafeFormatter",
    "t",
    "tp",
]
