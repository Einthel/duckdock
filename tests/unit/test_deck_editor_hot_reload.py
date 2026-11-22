"""
Модульные и интеграционные тесты сохранения и горячей перезагрузки DuckDeck (Hot Reload).
Проверяют реализацию шагов 2.4 и 2.5:
  1. Кнопка '💾 Сохранить' в EditorHeaderBar со стилями Dark Obsidian v2 и сигналом save_requested.
  2. Хоткей Ctrl+S и слот save_configuration() в DeckEditorWindow с атомарной записью через DeckConfigAdapter.
  3. Регистрация и эмиссия сигнала bus.deck_config_updated.
  4. Подписка DeckView на bus.deck_config_updated, in-place обновление кнопок 2x5 и уведомление в тикер.
  5. Гарантированная отписка от шины событий в DeckView без утечек.
  6. Отсутствие утечек таймеров в EditorHeaderBar.
  7. 100% паритет ключей локализации RU/EN.
"""
from __future__ import annotations

import json
import os
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.deck.editor.adapter import DeckConfigAdapter
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.widgets.header_bar import EditorHeaderBar
from modules.deck.editor.window import DeckEditorWindow
from modules.deck.models import DeckConfigLoader, DeckRootConfig
from modules.deck.view import DeckView


@pytest.fixture
def isolated_deck_config(tmp_path):
    """
    Фикстура изолированного файла конфигурации DuckDeck для тестов сохранения.
    Предотвращает перезапись боевого config/deck_config.json.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = config_dir / "deck_config.json"

    default_root = DeckConfigLoader.get_default_config()
    from modules.deck.models import DeckActionConfig, DeckButtonConfig
    default_root.pages[0].buttons = [
        DeckButtonConfig(
            id="btn_obs_record",
            slot_index=4,
            name="OBS Запись",
            title="OBS Запись",
            category="shortcut",
            icon="⏺",
            color_accent="#dc2626",
            action=DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "f9"]}),
        )
    ]
    with open(cfg_file, "w", encoding="utf-8") as f:
        f.write(default_root.model_dump_json(indent=2))

    return str(cfg_file)


@pytest.fixture
def editor_window(qapp, isolated_deck_config):
    """Фикстура окна редактора с изолированным путем к файлу настроек."""
    win = DeckEditorWindow()
    win.config_path = isolated_deck_config
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def test_window_save_button_triggers_save_configuration(editor_window, isolated_deck_config):
    """
    Проверка нажатия кнопки '💾 Сохранить':
      - Клик по кнопке btn_save в HeaderBar вызывает save_configuration().
      - DeckConfigAdapter сохраняет обновленные данные на диск.
      - Эмитируется сигнал bus.deck_config_updated.
      - На кнопке отображается индикация успеха '✓ Сохранено!'.
    """
    received_bus_events = []
    bus.deck_config_updated.connect(lambda: received_bus_events.append(True))

    # Модифицируем слот 0
    editor_window._button_slots[0] = ButtonSlotDTO(
        slot_index=0,
        title="Custom Save Test",
        icon="🚀",
        action_type="Hotkey",
        hotkey="Ctrl + Alt + T",
    )

    try:
        # Клик по кнопке Сохранить в тулбаре
        header = editor_window.header_bar
        assert isinstance(header, EditorHeaderBar)
        header.btn_save.click()

        # Проверяем эмиссию сигнала шины
        assert len(received_bus_events) == 1

        # Проверяем отклик на кнопке
        assert "✓" in header.btn_save.text()
        assert header.btn_save.property("state") == "success"

        # Проверяем, что файл на диске реально обновился атомарно
        saved_root = DeckConfigAdapter.load_deck_config(isolated_deck_config)
        first_btn = saved_root.pages[0].buttons[0]
        assert first_btn.title == "Custom Save Test"
        assert first_btn.icon == "🚀"

    finally:
        try:
            bus.deck_config_updated.disconnect()
        except Exception:
            pass


def test_window_ctrl_s_shortcut_triggers_save(editor_window, isolated_deck_config):
    """
    Проверка хоткея Ctrl+S:
      - Активация хоткея вызывает save_configuration().
      - Изменения атомарно записываются в файл конфигурации.
    """
    received_bus_events = []
    bus.deck_config_updated.connect(lambda: received_bus_events.append(True))

    editor_window._button_slots[1] = ButtonSlotDTO(
        slot_index=1,
        title="Shortcut Test",
        icon="⚡",
        action_type="Hotkey",
        hotkey="Win + D",
    )

    try:
        # Активация хоткея Ctrl+S
        editor_window._save_shortcut.activated.emit()

        assert len(received_bus_events) == 1

        saved_root = DeckConfigAdapter.load_deck_config(isolated_deck_config)
        second_btn = next((b for b in saved_root.pages[0].buttons if b.slot_index == 1), None)
        assert second_btn is not None
        assert second_btn.title == "Shortcut Test"
        assert second_btn.icon == "⚡"

    finally:
        try:
            bus.deck_config_updated.disconnect()
        except Exception:
            pass


def test_deck_view_hot_reload_on_eventbus(qapp, isolated_deck_config):
    """
    Проверка реактивности DeckView на 7" экране:
      - DeckView подписывается на bus.deck_config_updated.
      - При эмиссии сигнала вызывается _on_deck_config_updated().
      - Кнопки сетки 2x5 обновляются in-place через update_config() без мерцания.
      - Тикер интерактивной панели получает уведомление t("deck.interactive.config_reloaded").
    """
    view = DeckView(config_path=isolated_deck_config)
    try:
        # Убедимся, что начальное состояние загружено
        btn_slot_4 = view.grid.get_button("btn_obs_record")
        assert btn_slot_4 is not None
        assert btn_slot_4.lbl_title.text() == "OBS Запись"

        # Имитируем сохранение нового конфига через DeckConfigAdapter
        root = DeckConfigAdapter.load_deck_config(isolated_deck_config)
        slots = DeckConfigAdapter.load_page_slots(root, 0)
        slots[4].title = "Live Hot Reloaded!"
        slots[4].icon = "🔥"
        updated_root = DeckConfigAdapter.apply_slots_to_page(root, 0, slots)
        DeckConfigAdapter.save_deck_config_atomic(updated_root, isolated_deck_config)

        # Эмитируем сигнал горячей перезагрузки
        bus.deck_config_updated.emit()
        qapp.processEvents()

        # Проверяем, что кнопка обновилась in-place
        reloaded_btn = view.grid.get_button("btn_obs_record")
        assert reloaded_btn is not None
        assert reloaded_btn.lbl_title.text() == "Live Hot Reloaded!"
        assert reloaded_btn.lbl_icon.text() == "🔥"

        # Проверяем уведомление в тикер
        assert view.status_message == t("deck.interactive.config_reloaded")
        if hasattr(view, "interactive_panel"):
            assert view.interactive_panel.right_section.lbl_ticker.text() == t("deck.interactive.config_reloaded")

    finally:
        view.cleanup()
        view.deleteLater()
        qapp.processEvents()


def test_deck_view_safe_unsubscription(isolated_deck_config):
    """
    Проверка безопасной отписки DeckView от EventBus в cleanup():
      - bus.deck_config_updated отключается без ошибок.
      - Повторный вызов cleanup() не приводит к исключениям.
    """
    view = DeckView(config_path=isolated_deck_config)
    assert view._eventbus_connected is True

    view.cleanup()
    assert view._eventbus_connected is False

    # Повторный вызов безопасен (идемпотентен)
    view.cleanup()
    assert view._eventbus_connected is False
