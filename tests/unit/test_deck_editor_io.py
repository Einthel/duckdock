"""
Комплексный набор тестов I/O, Singleton и реактивности DuckDeck (tests/unit/test_deck_editor_io.py).
Покрывает интеграцию Спринта 2 (Шаг 2.6):
  1. DeckEditorManager:
     - Синглтон-паттерн, повторный вызов не создает второго окна.
     - Инварианты Stealth Focus (parent=None, isWindow=True).
     - Вызовы show(), raise_(), activateWindow().
     - Корректное закрытие и пересоздание после разрушения.
  2. DeckConfigAdapter:
     - Прямая конвертация DeckButtonConfig -> ButtonSlotDTO.
     - Обратная конвертация ButtonSlotDTO -> DeckButtonConfig со 100% сохранением расширенных полей:
       (color_accent, status_source, sound_override, toggle_action).
     - Изоляция многостраничной структуры (Pages 1..N) в apply_slots_to_page.
     - Атомарное сохранение: запись во временный файл .tmp с fsync, создание .bak, атомарная замена os.replace.
     - Устойчивость к сбоям I/O (очистка .tmp, сохранность целевого файла) и откат к дефолту при битых данных.
  3. Реактивность EventBus и Hot Reload:
     - Эмиссия сигнала bus.deck_config_updated.
     - In-place обновление слотов 2x5 в DeckView без мерцания и пересоздания виджетов.
     - Отображение статуса в тикер интерактивной панели.
     - Корректная отписка от шины при cleanup() без утечек.
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from core.i18n import t
from modules.deck.editor.adapter import DeckConfigAdapter
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.manager import DeckEditorManager
from modules.deck.editor.window import DeckEditorWindow
from modules.deck.models import (
    DeckActionConfig,
    DeckButtonConfig,
    DeckConfigLoader,
    DeckPageConfig,
    DeckRootConfig,
)
from modules.deck.view import DeckView


# ============================================================================
# Фикстуры
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_editor_manager_fixture(qapp: QApplication):
    """Гарантирует чистое состояние DeckEditorManager до и после каждого теста."""
    DeckEditorManager.close_editor()
    qapp.processEvents()
    yield
    DeckEditorManager.close_editor()
    qapp.processEvents()


@pytest.fixture
def sample_button_config() -> DeckButtonConfig:
    """Эталонный объект DeckButtonConfig со всеми расширенными полями."""
    return DeckButtonConfig(
        id="btn_io_test_0",
        slot_index=2,
        name="Mute Microphone",
        title="Mic Control",
        category="system",
        icon="🎙",
        icon_path="resources/deck/icons/mic.png",
        icon_size=48,
        color_accent="#ff0055",
        background_color="#1e1e2e",
        status_source="mic_mute",
        sound_override="resources/deck/sounds/click.wav",
        action=DeckActionConfig(
            action_type="hotkey",
            params={"keys": ["ctrl", "shift", "m"]},
        ),
        toggle_action=DeckActionConfig(
            action_type="system",
            params={"command": "toggle_mic_mute"},
        ),
    )


@pytest.fixture
def multi_page_root_config(sample_button_config: DeckButtonConfig) -> DeckRootConfig:
    """Многостраничный DeckRootConfig с 3 страницами для проверки изоляции."""
    p1 = DeckPageConfig(
        id="page_main",
        name="Main Page",
        grid_rows=2,
        grid_cols=5,
        buttons=[
            DeckButtonConfig(
                id="btn_p1_0",
                slot_index=0,
                title="P1 Slot 0",
                category="system",
                icon="⚡",
                color_accent="#38bdf8",
                action=DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"}),
            ),
            sample_button_config,
        ],
    )
    p2 = DeckPageConfig(
        id="page_media",
        name="Media Page",
        grid_rows=2,
        grid_cols=5,
        buttons=[
            DeckButtonConfig(
                id="btn_p2_1",
                slot_index=1,
                title="P2 Slot 1",
                category="shortcut",
                icon="🎵",
                color_accent="#a855f7",
                action=DeckActionConfig(action_type="hotkey", params={"keys": ["media_play_pause"]}),
            )
        ],
    )
    p3 = DeckPageConfig(
        id="page_dev",
        name="Dev Page",
        grid_rows=2,
        grid_cols=5,
        buttons=[],
    )
    return DeckRootConfig(pages=[p1, p2, p3])


@pytest.fixture
def isolated_config_file(tmp_path: Any) -> str:
    """Создает изолированный временный файл deck_config.json."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = config_dir / "deck_config.json"
    default_root = DeckConfigLoader.get_default_config()
    default_root.pages[0].buttons = [
        DeckButtonConfig(
            id="btn_default_test_0",
            slot_index=0,
            name="Test Slot 0",
            title="Initial Title",
            category="system",
            icon="⚡",
            color_accent="#38bdf8",
            action=DeckActionConfig(action_type="system", params={"command": "dimmer"}),
        )
    ]
    with open(cfg_file, "w", encoding="utf-8") as f:
        f.write(default_root.model_dump_json(indent=2))
    return str(cfg_file)


# ============================================================================
# 1. Тестирование DeckEditorManager (Singleton, Focus, Lifecycle)
# ============================================================================

def test_editor_manager_singleton_lifecycle(qapp: QApplication):
    """
    Проверка паттерна Singleton:
      - До вызова get_instance() возвращает None.
      - Первый вызов open_editor() создает окно.
      - Повторный вызов open_editor() возвращает тот же самый экземпляр.
      - close_editor() закрывает окно и сбрасывает ссылку.
    """
    assert DeckEditorManager.get_instance() is None

    win1 = DeckEditorManager.open_editor()
    assert isinstance(win1, DeckEditorWindow)
    assert DeckEditorManager.get_instance() is win1

    win2 = DeckEditorManager.open_editor()
    assert win2 is win1

    DeckEditorManager.close_editor()
    assert DeckEditorManager.get_instance() is None

    # Повторное создание после закрытия
    win3 = DeckEditorManager.open_editor()
    assert win3 is not None
    assert win3 is not win1
    assert DeckEditorManager.get_instance() is win3


def test_editor_manager_stealth_focus_invariants(qapp: QApplication):
    """
    Проверка инвариантов Stealth Focus:
      - Окно редактора является независимым top-level окном ОС (parent is None).
      - isWindow() возвращает True.
      - Вызовы show(), raise_(), activateWindow() выполняются при открытии.
    """
    dummy_parent = DeckView()
    try:
        with patch.object(DeckEditorWindow, "activateWindow") as mock_activate, \
             patch.object(DeckEditorWindow, "raise_") as mock_raise, \
             patch.object(DeckEditorWindow, "show") as mock_show:
            
            win = DeckEditorManager.open_editor(parent=dummy_parent)
            assert win.parent() is None
            assert win.isWindow()
            mock_show.assert_called()
            mock_raise.assert_called()
            mock_activate.assert_called()
    finally:
        dummy_parent.cleanup()
        dummy_parent.deleteLater()
        qapp.processEvents()


# ============================================================================
# 2. Тестирование DeckConfigAdapter (Mapping, Fidelity, Multi-Page)
# ============================================================================

def test_adapter_slot_to_dto_and_dto_to_slot_fidelity(sample_button_config: DeckButtonConfig):
    """
    Проверка двусторонней конвертации с сохранением 100% расширенных полей:
      - slot_to_dto() извлекает все параметры и сохраняет original_config.
      - dto_to_slot() обновляет title, icon, hotkey, сохраняя status_source,
        color_accent, sound_override и toggle_action.
    """
    # 1. Конвертация DeckButtonConfig -> ButtonSlotDTO
    dto = DeckConfigAdapter.slot_to_dto(sample_button_config)
    assert dto.slot_index == 2
    assert dto.title == "Mic Control"
    assert dto.icon == "🎙"
    assert dto.color_accent == "#ff0055"
    assert dto.status_source == "mic_mute"
    assert dto.sound_override == "resources/deck/sounds/click.wav"
    assert dto.toggle_action is not None
    assert dto.toggle_action.action_type == "audio"
    assert "Ctrl" in dto.hotkey
    assert dto.original_config is not None

    # 2. Модификация пользовательских полей в DTO
    dto.title = "Updated Mic"
    dto.icon = "🔇"
    dto.hotkey = "Ctrl + Alt + M"
    dto.color_accent = "#38bdf8"

    # 3. Обратная конвертация ButtonSlotDTO -> DeckButtonConfig с original_config
    updated_cfg = DeckConfigAdapter.dto_to_slot(dto, original_config=sample_button_config)
    assert updated_cfg.slot_index == 2
    assert updated_cfg.title == "Updated Mic"
    assert updated_cfg.icon == "🔇"
    assert updated_cfg.color_accent == "#38bdf8"
    # Расширенные поля сохранены
    assert updated_cfg.status_source == "mic_mute"
    assert updated_cfg.sound_override == "resources/deck/sounds/click.wav"
    assert updated_cfg.toggle_action is not None
    assert updated_cfg.toggle_action.action_type == "audio"
    # Хоткей распарсен
    assert updated_cfg.action.action_type == "hotkey"
    assert "ctrl" in updated_cfg.action.params["keys"]
    assert "alt" in updated_cfg.action.params["keys"]
    assert "m" in updated_cfg.action.params["keys"]


def test_adapter_dto_to_slot_brand_new_button():
    """Проверка генерации новой валидной кнопки из DTO без original_config."""
    dto = ButtonSlotDTO(
        slot_index=7,
        title="New Macro",
        icon="🚀",
        hotkey="Ctrl + Shift + F12",
        color_accent="#10b981",
    )
    new_slot = DeckConfigAdapter.dto_to_slot(dto, original_config=None)
    assert isinstance(new_slot, DeckButtonConfig)
    assert new_slot.slot_index == 7
    assert new_slot.title == "New Macro"
    assert new_slot.icon == "🚀"
    assert new_slot.color_accent == "#10b981"
    assert new_slot.action.action_type == "hotkey"
    assert "f12" in new_slot.action.params["keys"]


def test_adapter_multipage_isolation_and_apply(multi_page_root_config: DeckRootConfig):
    """
    Проверка изоляции многостраничной структуры:
      - load_page_slots() корректно извлекает слоты целевой страницы.
      - apply_slots_to_page() изменяет только целевую страницу,
        сохраняя все остальные страницы (Pages 1..N) нетронутыми.
    """
    # Загружаем слоты 2-й страницы (Media Page)
    media_slots = DeckConfigAdapter.load_page_slots(multi_page_root_config, "page_media")
    assert media_slots[1].title == "P2 Slot 1"
    assert media_slots[0].title == ""  # Пустой слот инициализирован дефолтом

    # Модифицируем слот 0 и 1 на странице Media
    media_slots[0] = ButtonSlotDTO(slot_index=0, title="New Media Button", icon="🎧")
    media_slots[1].title = "P2 Slot 1 Modified"

    # Применяем изменения к root config
    updated_root = DeckConfigAdapter.apply_slots_to_page(
        multi_page_root_config,
        "page_media",
        media_slots,
    )

    # Проверяем, что Page 1 осталась неизменной
    assert len(updated_root.pages[0].buttons) == 2
    assert updated_root.pages[0].buttons[0].title == "P1 Slot 0"
    assert updated_root.pages[0].buttons[1].title == "Mic Control"

    # Проверяем, что Page 2 обновилась
    p2_buttons = {b.slot_index: b for b in updated_root.pages[1].buttons}
    assert 0 in p2_buttons
    assert p2_buttons[0].title == "New Media Button"
    assert p2_buttons[1].title == "P2 Slot 1 Modified"

    # Проверяем, что Page 3 осталась пустой
    assert len(updated_root.pages[2].buttons) == 0


# ============================================================================
# 3. Тестирование атомарности I/O и обработки сбоев
# ============================================================================

def test_atomic_save_tmp_and_bak_lifecycle(isolated_config_file: str):
    """
    Проверка жизненного цикла атомарной записи:
      - Данные записываются во временный файл .tmp.
      - Создается резервная копия .bak при наличии исходного файла.
      - Вызывается атомарная замена os.replace().
      - После успешной записи .tmp не остается на диске.
    """
    abs_path = os.path.abspath(isolated_config_file)
    bak_path = f"{abs_path}.bak"
    tmp_path = f"{abs_path}.tmp"

    root = DeckConfigAdapter.load_deck_config(isolated_config_file)
    root.pages[0].buttons[0].title = "Atomic Verified Title"

    success = DeckConfigAdapter.save_deck_config_atomic(root, isolated_config_file)
    assert success is True

    # .tmp файл должен отсутствовать
    assert not os.path.exists(tmp_path)

    # .bak файл должен быть создан
    assert os.path.exists(bak_path)

    # Проверяем, что целевой файл содержит обновленные данные
    reloaded_root = DeckConfigAdapter.load_deck_config(isolated_config_file)
    assert reloaded_root.pages[0].buttons[0].title == "Atomic Verified Title"


def test_atomic_save_handles_io_error_and_cleans_tmp(isolated_config_file: str):
    """
    Проверка устойчивости к сбоям записи:
      - При возникновении IOError во время сброса буферов временный файл .tmp удаляется.
      - Исходный файл конфигурации остается неповрежденным.
      - Функция возвращает False.
    """
    abs_path = os.path.abspath(isolated_config_file)
    original_mtime = os.path.getmtime(abs_path)
    root = DeckConfigAdapter.load_deck_config(isolated_config_file)

    with patch("os.fsync", side_effect=IOError("Simulated disk write failure")):
        success = DeckConfigAdapter.save_deck_config_atomic(root, isolated_config_file)
        assert success is False

    # Временный файл должен быть удален
    assert not os.path.exists(f"{abs_path}.tmp")

    # Исходный файл не должен быть перезаписан
    assert os.path.getmtime(abs_path) == original_mtime


def test_load_deck_config_corrupted_fallback(tmp_path: Any):
    """При чтении поврежденного JSON load_deck_config откатывается к валидному дефолту."""
    corrupted_file = tmp_path / "corrupted_deck.json"
    corrupted_file.write_text("{ broken json content: invalid syntax", encoding="utf-8")

    fallback_root = DeckConfigAdapter.load_deck_config(str(corrupted_file))
    assert isinstance(fallback_root, DeckRootConfig)
    assert len(fallback_root.pages) > 0


# ============================================================================
# 4. Тестирование реактивности EventBus и Hot Reload
# ============================================================================

def test_deck_view_hot_reload_on_bus_signal(isolated_config_file: str, qapp: QApplication):
    """
    Проверка реактивности Hot Reload:
      - DeckView подписывается на bus.deck_config_updated.
      - Эмиссия сигнала приводит к in-place обновлению кнопок текущей страницы.
      - Обновляется статус в бегущей строке / тикер панели.
      - cleanup() корректно отписывается от шины.
    """
    view = DeckView(config_path=isolated_config_file)
    qapp.processEvents()

    try:
        # Проверяем исходное состояние первой кнопки
        first_btn = view.grid.get_button(view.root_config.pages[0].buttons[0].id)
        original_title = first_btn.lbl_title.text()

        # Модифицируем файл на диске через атомарное сохранение
        root = DeckConfigAdapter.load_deck_config(isolated_config_file)
        root.pages[0].buttons[0].title = "Live Hot Reloaded!"
        DeckConfigAdapter.save_deck_config_atomic(root, isolated_config_file)

        # Эмитируем сигнал обновления
        bus.deck_config_updated.emit()
        qapp.processEvents()

        # Проверяем in-place обновление надписи без пересоздания виджета
        assert first_btn.lbl_title.text() == "Live Hot Reloaded!"
        assert first_btn.lbl_title.text() != original_title

        # Проверяем сообщение в строке статуса
        expected_status = t("deck.interactive.config_reloaded")
        assert view._status_message == expected_status

    finally:
        view.cleanup()
        view.deleteLater()
        qapp.processEvents()

    # Проверяем, что после cleanup отписка прошла чисто (повторная эмиссия не вызывает сбоев)
    bus.deck_config_updated.emit()
    qapp.processEvents()


def test_deck_editor_window_save_triggers_bus_signal(isolated_config_file: str, qapp: QApplication):
    """
    Интеграционный тест: DeckEditorWindow.save_configuration()
      - Сохраняет DTO на диск.
      - Эмитирует сигнал bus.deck_config_updated.
      - Показывает визуальную обратную связь в HeaderBar ('✓ Сохранено!').
    """
    win = DeckEditorWindow(config_path=isolated_config_file)
    qapp.processEvents()

    events_received: list[bool] = []
    bus.deck_config_updated.connect(lambda: events_received.append(True))

    try:
        # Модифицируем первый слот в редакторе
        win._button_slots[0] = ButtonSlotDTO(
            slot_index=0,
            title="Integrated Save Test",
            icon="🎯",
            action_type="Hotkey",
            hotkey="Ctrl + Shift + S",
        )

        # Вызываем сохранение
        win.save_configuration()
        qapp.processEvents()

        # Проверяем сигнал
        assert len(events_received) == 1

        # Проверяем индикацию кнопки
        assert "✓" in win.header_bar.btn_save.text()
        assert win.header_bar.btn_save.property("state") == "success"

        # Проверяем сохранение на диске
        saved_root = DeckConfigAdapter.load_deck_config(isolated_config_file)
        assert saved_root.pages[0].buttons[0].title == "Integrated Save Test"

    finally:
        win.close()
        win.deleteLater()
        qapp.processEvents()
