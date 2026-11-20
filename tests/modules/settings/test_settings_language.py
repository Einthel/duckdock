"""
Модульные тесты для сенсорного селектора языка в настройках DuckDock (Фаза 3).
Проверяют:
1. Рендеринг сенсорных кнопок переключения языка и соблюдение инварианта Stealth Focus (Qt.NoFocus).
2. Начальное активное состояние кнопок (RU vs EN) в соответствии с AppConfig.
3. Сохранение выбранного языка в JSON через атомарную функцию save_config().
4. Эмиссию сигнала bus.language_changed и оповещение I18nManager.
5. Прямой метод retranslate_ui(): полное обновление всех текстовых меток, заголовков и статусов.
6. Идемпотентность: пропуск повторной записи и эмиссии сигналов при клике на уже активный язык.
7. Атомарное сохранение save_config() и обработку ошибок.
"""
import json
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtCore import Qt

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.settings.config import AppConfig, load_config, save_config
from modules.settings.view import SettingsView


@pytest.fixture(autouse=True)
def reset_i18n_state():
    """Сброс состояния синглтона I18nManager перед каждым тестом."""
    I18nManager._reset_instance()
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)
    yield
    I18nManager._reset_instance()


@pytest.mark.unit
def test_settings_view_language_buttons_render_and_focus(qapp):
    """
    Проверка рендеринга карточки языка и инварианта Stealth Focus:
    - Сам экран SettingsView имеет Qt.NoFocus.
    - Кнопки btn_lang_ru и btn_lang_en имеют Qt.NoFocus.
    - Кнопки имеют минимальную высоту не менее 44px для сенсорного ввода.
    - Вспомогательные элементы (btn_reload, заголовки) имеют Qt.NoFocus.
    """
    view = SettingsView()
    try:
        assert view.focusPolicy() == Qt.NoFocus
        assert hasattr(view, "btn_lang_ru")
        assert hasattr(view, "btn_lang_en")

        assert view.btn_lang_ru.focusPolicy() == Qt.NoFocus
        assert view.btn_lang_en.focusPolicy() == Qt.NoFocus
        assert view.btn_lang_ru.minimumHeight() >= 44
        assert view.btn_lang_en.minimumHeight() >= 44

        assert view.btn_reload.focusPolicy() == Qt.NoFocus
        assert view.lbl_lang_header.focusPolicy() == Qt.NoFocus
        assert view.lbl_lang_desc.focusPolicy() == Qt.NoFocus
    finally:
        view.cleanup()


@pytest.mark.unit
def test_settings_view_initial_active_state(qapp):
    """
    Проверка начального визуального состояния кнопок выбора языка:
    - При config.language == 'ru' кнопка btn_lang_ru активна (active="true").
    - При config.language == 'en' кнопка btn_lang_en активна (active="true").
    """
    cfg_ru = AppConfig(language="ru")
    view_ru = SettingsView(config=cfg_ru)
    try:
        assert view_ru.btn_lang_ru.property("active") == "true"
        assert view_ru.btn_lang_en.property("active") == "false"
    finally:
        view_ru.cleanup()

    cfg_en = AppConfig(language="en")
    view_en = SettingsView(config=cfg_en)
    try:
        assert view_en.btn_lang_ru.property("active") == "false"
        assert view_en.btn_lang_en.property("active") == "true"
    finally:
        view_en.cleanup()


@pytest.mark.unit
def test_language_switch_saves_config(qapp, tmp_path):
    """
    Проверка записи изменений в config.json при переключении языка:
    - Клик по кнопке English переключает config.language на 'en'.
    - Файл на диске атомарно обновляется и содержит language: 'en'.
    - Клик обратно на Русский обновляет файл до language: 'ru'.
    """
    config_file = tmp_path / "config.json"
    cfg = AppConfig(language="ru")
    save_config(cfg, config_file)

    view = SettingsView(config_path=config_file)
    try:
        assert view.config.language == "ru"

        # Переключение на английский
        view.btn_lang_en.click()
        assert view.config.language == "en"
        assert view.btn_lang_en.property("active") == "true"
        assert view.btn_lang_ru.property("active") == "false"

        # Проверка содержимого файла на диске
        with open(config_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["language"] == "en"

        # Переключение обратно на русский
        view.btn_lang_ru.click()
        assert view.config.language == "ru"
        assert view.btn_lang_ru.property("active") == "true"
        assert view.btn_lang_en.property("active") == "false"

        with open(config_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["language"] == "ru"
    finally:
        view.cleanup()


@pytest.mark.unit
def test_language_switch_emits_eventbus_signal(qapp, tmp_path):
    """
    Проверка эмиссии сигнала bus.language_changed при выборе языка:
    - Смена языка инициирует сигнал через центральную шину EventBus.
    - I18nManager обновляет свое глобальное состояние.
    """
    config_file = tmp_path / "config.json"
    cfg = AppConfig(language="ru")
    save_config(cfg, config_file)

    view = SettingsView(config_path=config_file)
    spy = MagicMock()
    bus.language_changed.connect(spy)

    try:
        view.btn_lang_en.click()
        spy.assert_called_once_with("en")
        assert I18nManager().current_language == "en"
    finally:
        try:
            bus.language_changed.disconnect(spy)
        except Exception:
            pass
        view.cleanup()


@pytest.mark.unit
def test_settings_view_retranslate_ui_full_update(qapp):
    """
    Проверка полного обновления текстов через retranslate_ui():
    - Заголовки экрана, карточек и полей обновляются при смене локали.
    - Динамические значения (статусы 'Включен' / 'Enabled', единицы измерения) обновляются без хардкода.
    """
    view = SettingsView(config=AppConfig(language="ru"))
    try:
        # Проверка русских текстов
        assert view.lbl_title.text() == "Настройки DuckDock"
        assert view.lbl_sub.text() == "Параметры дополнительного сенсорного экрана, диммера и защиты фокуса"
        assert view.btn_reload.text() == "Перезагрузить JSON"
        assert view.lbl_display_header.text() == "Экран и геометрия"
        assert view.lbl_stealth_header.text() == "Защита фокуса (Stealth)"
        assert view.lbl_lang_header.text() == "Язык интерфейса"
        assert view.btn_lang_ru.text() == "Русский"
        assert view.btn_lang_en.text() == "English"
        assert view._labels["stealth_enabled"].text() == "Включен"
        assert view._labels["resolution"].text().endswith("px")
        assert view._labels["focus_delay"].text().endswith("мс")

        # Переключение на английский через I18nManager (эмитирует bus.language_changed)
        I18nManager().set_language("en", emit_signal=True)

        # Проверка английских текстов
        assert view.lbl_title.text() == "DuckDock Settings"
        assert view.lbl_sub.text() == "Secondary touchscreen, dimmer and focus guardian parameters"
        assert view.btn_reload.text() == "Reload JSON"
        assert view.lbl_display_header.text() == "Display & Geometry"
        assert view.lbl_stealth_header.text() == "Focus Guardian (Stealth)"
        assert view.lbl_lang_header.text() == "Interface Language"
        assert view._labels["stealth_enabled"].text() == "Enabled"
        assert view._labels["focus_delay"].text().endswith("ms")

        # Возврат на русский
        I18nManager().set_language("ru", emit_signal=True)
        assert view.lbl_title.text() == "Настройки DuckDock"
        assert view._labels["stealth_enabled"].text() == "Включен"
    finally:
        view.cleanup()


@pytest.mark.unit
def test_language_switch_idempotency(qapp, tmp_path):
    """
    Проверка идемпотентности:
    - Повторный клик на уже активный язык не производит запись на диск и не вызывает I18nManager.
    """
    config_file = tmp_path / "config.json"
    cfg = AppConfig(language="ru")
    save_config(cfg, config_file)

    view = SettingsView(config_path=config_file)
    try:
        with patch("modules.settings.view.save_config") as mock_save, \
             patch.object(I18nManager, "set_language") as mock_set_lang:
            # Клик по уже активной кнопке 'ru'
            view.btn_lang_ru.click()

            mock_save.assert_not_called()
            mock_set_lang.assert_not_called()
    finally:
        view.cleanup()


@pytest.mark.unit
def test_atomic_save_config(tmp_path):
    """
    Проверка функции save_config:
    - Атомарная запись во временный файл и последующая замена.
    - Автоматическое создание недостающих директорий.
    - Корректная обработка ошибок и очистка .tmp при сбоях.
    """
    nested_dir = tmp_path / "sub" / "config"
    target_file = nested_dir / "config.json"

    cfg = AppConfig(language="en")
    success = save_config(cfg, target_file)
    assert success is True
    assert target_file.exists()

    loaded = load_config(target_file)
    assert loaded.language == "en"

    # Проверка очистки tmp файла при ошибке записи
    with patch("pathlib.Path.replace", side_effect=OSError("Simulated disk error")):
        fail_target = tmp_path / "fail_config.json"
        res = save_config(cfg, fail_target)
        assert res is False
        tmp_file = tmp_path / "fail_config.json.tmp"
        assert not tmp_file.exists()
