"""
Модульные тесты для подсистемы интернационализации core/i18n.
Проверяют паттерн Singleton, развертывание dot-notation, SafeFormatter,
плюрализацию (RU/EN), fallback-каскад, сигналы EventBus, паритет словарей и валидацию конфигурации.
"""
import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from core.event_bus import bus
from core.i18n import (
    I18nManager,
    SafeFormatter,
    get_plural_category_en,
    get_plural_category_ru,
    resolve_plural_category,
    t,
    tp,
)
from core.i18n.manager import _flatten_dict
from modules.settings.config import AppConfig, load_config


@pytest.fixture(autouse=True)
def reset_i18n_state():
    """Сброс состояния синглтона перед каждым тестом для изоляции."""
    I18nManager._reset_instance()
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)
    yield
    I18nManager._reset_instance()


@pytest.mark.unit
def test_i18n_singleton():
    """Валидация паттерна Singleton: создание возвращает один и тот же объект."""
    mgr1 = I18nManager()
    mgr2 = I18nManager()
    assert mgr1 is mgr2
    assert mgr1.current_language == "ru"


@pytest.mark.unit
def test_i18n_flattening_and_lookup():
    """Развертывание вложенных JSON в плоскую dot-notation таблицу и доступ за O(1)."""
    raw_data = {
        "sidebar": {
            "tabs": {
                "audio": "Микшер",
                "settings": "Настройки",
            }
        },
        "audio": {
            "devices_count": {
                "one": "{count} устройство",
                "few": "{count} устройства",
                "many": "{count} устройств",
            }
        },
        "flat_key": "Значение",
    }
    flattened = _flatten_dict(raw_data)
    assert flattened["sidebar.tabs.audio"] == "Микшер"
    assert flattened["sidebar.tabs.settings"] == "Настройки"
    assert flattened["flat_key"] == "Значение"

    # Проверка, что конечный объект плюрализации сохранен как dict
    assert isinstance(flattened["audio.devices_count"], dict)
    assert flattened["audio.devices_count"]["one"] == "{count} устройство"


@pytest.mark.unit
def test_i18n_safe_formatter():
    """Устойчивость SafeFormatter к неполным/неправильным аргументам без исключений."""
    formatter = SafeFormatter()

    # Корректная интерполяция
    res = formatter.safe_format("Hello {name}, count: {count}", name="World", count=42)
    assert res == "Hello World, count: 42"

    # Неполный набор аргументов (плейсхолдер остается неизменным)
    res_partial = formatter.safe_format("Hello {name}, extra: {missing}", name="Alice")
    assert res_partial == "Hello Alice, extra: {missing}"

    # Отсутствуют все аргументы
    res_none = formatter.safe_format("Value is {val}")
    assert res_none == "Value is {val}"

    # Позиционные аргументы
    res_pos = formatter.safe_format("Item {0} and {1}", "First")
    assert res_pos == "Item First and {1}"

    # Некорректные спецификаторы формата для строки
    res_bad_spec = formatter.safe_format("Val: {val:05d}")
    assert "Val: {val}" in res_bad_spec or "Val: {val:05d}" in res_bad_spec

    # Непарные скобки
    res_broken = formatter.safe_format("Broken {bracket")
    assert res_broken == "Broken {bracket"


@pytest.mark.unit
def test_i18n_pluralization_ru():
    """Детальная проверка плюрализации для русского языка (RU: one/few/many)."""
    # Категория 'one' (1, 21, 31, 101, но не 11)
    for n in (1, 21, 31, 41, 101, 121):
        assert get_plural_category_ru(n) == "one", f"Failed for {n}"
        assert resolve_plural_category("ru", n) == "one"

    # Категория 'few' (2-4, 22-24, 102-104, но не 12-14)
    for n in (2, 3, 4, 22, 23, 24, 102, 103, 104):
        assert get_plural_category_ru(n) == "few", f"Failed for {n}"
        assert resolve_plural_category("ru", n) == "few"

    # Категория 'many' (0, 5-20, 25-30, 11-14, 111-114)
    for n in (0, 5, 6, 10, 11, 12, 13, 14, 15, 19, 20, 25, 30, 111, 112, 114):
        assert get_plural_category_ru(n) == "many", f"Failed for {n}"
        assert resolve_plural_category("ru", n) == "many"

    # Проверка работы с отрицательными числами
    assert get_plural_category_ru(-1) == "one"
    assert get_plural_category_ru(-2) == "few"
    assert get_plural_category_ru(-5) == "many"


@pytest.mark.unit
def test_i18n_pluralization_en():
    """Проверка плюрализации для английского языка (EN: one/other)."""
    assert get_plural_category_en(1) == "one"
    assert resolve_plural_category("en", 1) == "one"

    for n in (0, 2, 3, 5, 10, 11, 21, 100):
        assert get_plural_category_en(n) == "other", f"Failed for {n}"
        assert resolve_plural_category("en", n) == "other"

    assert get_plural_category_en(-1) == "one"
    assert get_plural_category_en(-2) == "other"


@pytest.mark.unit
def test_i18n_tp_function(tmp_path):
    """Проверка функции tp() с динамической подстановкой шаблонов и каскадом."""
    ru_dict = {
        "items": {
            "one": "{count} элемент",
            "few": "{count} элемента",
            "many": "{count} элементов",
        }
    }
    en_dict = {
        "items": {
            "one": "{count} item",
            "other": "{count} items",
        }
    }
    (tmp_path / "ru.json").write_text(json.dumps(ru_dict), encoding="utf-8")
    (tmp_path / "en.json").write_text(json.dumps(en_dict), encoding="utf-8")

    mgr = I18nManager(locales_dir=tmp_path)
    mgr.set_language("ru", emit_signal=False)

    assert tp("items", count=1) == "1 элемент"
    assert tp("items", count=3) == "3 элемента"
    assert tp("items", count=12) == "12 элементов"

    mgr.set_language("en", emit_signal=False)
    assert tp("items", count=1) == "1 item"
    assert tp("items", count=2) == "2 items"
    assert tp("items", count=0) == "0 items"


@pytest.mark.unit
def test_i18n_fallback_cascade(tmp_path):
    """Симметричный fallback: ru -> en -> raw_key."""
    ru_dict = {
        "common": {"only_ru": "Только по-русски"},
        "shared": {"title": "Заголовок"},
    }
    en_dict = {
        "common": {"only_en": "English only"},
        "shared": {"title": "Title"},
    }
    (tmp_path / "ru.json").write_text(json.dumps(ru_dict), encoding="utf-8")
    (tmp_path / "en.json").write_text(json.dumps(en_dict), encoding="utf-8")

    mgr = I18nManager(locales_dir=tmp_path)
    mgr.set_language("ru", emit_signal=False)

    # Доступен в RU
    assert t("common.only_ru") == "Только по-русски"
    # Отсутствует в RU, но есть в EN (fallback)
    assert t("common.only_en") == "English only"
    # Отсутствует в обоих -> raw_key
    assert t("unknown.missing_key") == "unknown.missing_key"

    # Переключение на EN:
    mgr.set_language("en", emit_signal=False)
    assert t("common.only_en") == "English only"
    # Отсутствует в EN, но есть в RU (fallback)
    assert t("common.only_ru") == "Только по-русски"
    assert t("unknown.missing_key") == "unknown.missing_key"


@pytest.mark.unit
def test_i18n_set_language_signals():
    """Валидация эмиссии сигнала bus.language_changed при смене языка."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)

    received_signals = []

    def on_lang_changed(lang: str):
        received_signals.append(lang)

    bus.language_changed.connect(on_lang_changed)
    try:
        # Переключение на 'en' должно вызвать сигнал
        mgr.set_language("en", emit_signal=True)
        assert received_signals == ["en"]
        assert mgr.current_language == "en"

        # Идемпотентность: повторный вызов с тем же языком не отправляет повторный сигнал
        mgr.set_language("en", emit_signal=True)
        assert received_signals == ["en"]

        # Переключение обратно на 'ru'
        mgr.set_language("ru", emit_signal=True)
        assert received_signals == ["en", "ru"]
        assert mgr.current_language == "ru"
    finally:
        bus.language_changed.disconnect(on_lang_changed)


@pytest.mark.unit
def test_i18n_set_language_invalid():
    """Отклонение неподдерживаемых кодов языка."""
    mgr = I18nManager()
    with pytest.raises(ValueError, match="Unsupported language code"):
        mgr.set_language("de")


@pytest.mark.unit
def test_i18n_parity_guard():
    """100% паритет ключей между реальными locales/ru.json и locales/en.json."""
    locales_dir = Path(__file__).resolve().parents[2] / "locales"
    ru_path = locales_dir / "ru.json"
    en_path = locales_dir / "en.json"

    assert ru_path.exists(), "locales/ru.json does not exist"
    assert en_path.exists(), "locales/en.json does not exist"

    with open(ru_path, "r", encoding="utf-8") as f:
        ru_raw = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en_raw = json.load(f)

    ru_flat = _flatten_dict(ru_raw)
    en_flat = _flatten_dict(en_raw)

    ru_keys = set(ru_flat.keys())
    en_keys = set(en_flat.keys())

    diff = ru_keys ^ en_keys
    assert not diff, f"Discrepancy in translation keys between ru.json and en.json: {diff}"


@pytest.mark.unit
def test_app_config_language_validation(tmp_path):
    """Валидация поля language в AppConfig через Pydantic."""
    # По умолчанию язык 'ru'
    cfg = AppConfig()
    assert cfg.language == "ru"

    # Явное задание 'en'
    cfg_en = AppConfig(language="en")
    assert cfg_en.language == "en"

    # Недопустимый язык вызывает ValidationError
    with pytest.raises(ValidationError):
        AppConfig(language="fr")

    # Проверка загрузки из файла
    config_file = tmp_path / "custom_config.json"
    config_file.write_text('{"language": "en"}', encoding="utf-8")
    loaded = load_config(config_file)
    assert loaded.language == "en"

    # Поврежденный язык откатывается на дефолт при load_config
    bad_config = tmp_path / "bad_config.json"
    bad_config.write_text('{"language": "invalid_code"}', encoding="utf-8")
    fallback_loaded = load_config(bad_config)
    assert fallback_loaded.language == "ru"


@pytest.mark.unit
def test_i18n_t_sub_key_plural_access():
    """Прямой доступ к дочерним ключам плюрализации через t() (например, key.one)."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)
    assert t("audio.devices_count.one", count=1) == "1 активное устройство"
    assert t("audio.devices_count.few", count=2) == "2 активных устройства"
    assert t("audio.devices_count.many", count=5) == "5 активных устройств"


@pytest.mark.unit
def test_i18n_manager_reload(tmp_path):
    """Проверка метода reload() для обновления словарей на лету."""
    ru_dict = {"title": "Старый заголовок"}
    (tmp_path / "ru.json").write_text(json.dumps(ru_dict), encoding="utf-8")
    (tmp_path / "en.json").write_text(json.dumps({}), encoding="utf-8")

    mgr = I18nManager(locales_dir=tmp_path)
    mgr.set_language("ru", emit_signal=False)
    assert t("title") == "Старый заголовок"

    # Изменяем файл и вызываем reload
    ru_dict["title"] = "Новый заголовок"
    (tmp_path / "ru.json").write_text(json.dumps(ru_dict), encoding="utf-8")
    mgr.reload()
    assert t("title") == "Новый заголовок"


@pytest.mark.unit
def test_i18n_invalid_locale_file_handled(tmp_path):
    """Корректная обработка поврежденного JSON-файла словаря без фатального сбоя."""
    (tmp_path / "ru.json").write_text("INVALID_JSON{", encoding="utf-8")
    (tmp_path / "en.json").write_text("{}", encoding="utf-8")

    mgr = I18nManager(locales_dir=tmp_path)
    mgr.set_language("ru", emit_signal=False)
    assert t("any.key") == "any.key"

