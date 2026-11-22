"""
Юнит-тесты двустороннего адаптера конфигурации DuckDeck (DeckConfigAdapter).
Проверяют:
  1. 100% сохранение расширенных полей Pydantic v2 (status_source, color_accent, sound_override, toggle_action)
     при двойной конвертации DeckButtonConfig <-> ButtonSlotDTO.
  2. Сохранение контекста многостраничного DeckRootConfig (Pages 1..N) и отсутствие утечек данных между страницами.
  3. Атомарное сохранение на диск с созданием .tmp, бэкапом .bak и устойчивость к сбоям I/O и ошибкам валидации.
"""
import json
import os
import shutil
import tempfile
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from modules.deck.editor.adapter import DeckConfigAdapter
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.models import (
    DeckActionConfig,
    DeckButtonConfig,
    DeckConfigLoader,
    DeckPageConfig,
    DeckRootConfig,
    SoundSettings,
)


@pytest.fixture
def sample_button_config() -> DeckButtonConfig:
    """Эталонный DeckButtonConfig со всеми расширенными полями."""
    return DeckButtonConfig(
        id="btn_sample_test",
        slot_index=3,
        name="Microphone Mute",
        title="Mic Control",
        category="system",
        icon="🎙",
        icon_path="resources/deck/icons/mic.png",
        icon_size=48,
        color_accent="#ff0055",
        background_color="#1a1a2e",
        status_source="mic_mute",
        sound_override="resources/deck/sounds/custom_click.wav",
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
    page1 = DeckPageConfig(
        id="page_main",
        name="Main Page",
        grid_rows=2,
        grid_cols=5,
        buttons=[
            DeckButtonConfig(
                id="btn_p1_0",
                slot_index=0,
                title="Page1 Button 0",
                category="system",
                icon="⚡",
                color_accent="#00ffcc",
                action=DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"}),
            ),
            sample_button_config,
        ],
    )
    page2 = DeckPageConfig(
        id="page_media",
        name="Media & Audio",
        grid_rows=2,
        grid_cols=5,
        buttons=[
            DeckButtonConfig(
                id="btn_p2_1",
                slot_index=1,
                title="Page2 Button 1",
                category="shortcut",
                icon="🎵",
                color_accent="#a855f7",
                action=DeckActionConfig(action_type="hotkey", params={"keys": ["media_play_pause"]}),
            )
        ],
    )
    page3 = DeckPageConfig(
        id="page_dev",
        name="Dev Tools",
        grid_rows=2,
        grid_cols=5,
        buttons=[
            DeckButtonConfig(
                id="btn_p3_5",
                slot_index=5,
                title="Terminal",
                category="program",
                icon="💻",
                color_accent="#10b981",
                action=DeckActionConfig(action_type="launch", params={"path": "wt.exe", "args": []}),
            )
        ],
    )
    return DeckRootConfig(
        active_profile="page_main",
        simulation_mode=False,
        sound_settings=SoundSettings(),
        pages=[page1, page2, page3],
    )


# ==============================================================================
# 1. Тесты целостности полей при двойной конвертации Config <-> DTO
# ==============================================================================


def test_slot_to_dto_and_back_preserves_all_extended_fields(sample_button_config: DeckButtonConfig):
    """
    Проверка 100% сохранения расширенных полей Pydantic v2:
    status_source, color_accent, sound_override, toggle_action при slot_to_dto -> dto_to_slot.
    """
    # 1. Конвертация Config -> DTO
    dto = DeckConfigAdapter.slot_to_dto(sample_button_config)

    assert dto.slot_index == 3
    assert dto.title == "Mic Control"
    assert dto.icon == "🎙"
    assert dto.color_accent == "#ff0055"
    assert dto.status_source == "mic_mute"
    assert dto.sound_override == "resources/deck/sounds/custom_click.wav"
    assert dto.toggle_action is not None
    assert dto.toggle_action.action_type == "system"
    assert dto.toggle_action.params["command"] == "toggle_mic_mute"
    assert dto.hotkey == "Ctrl + Shift + M"

    # 2. Конвертация DTO -> Config (обратно)
    reconstructed = DeckConfigAdapter.dto_to_slot(dto)

    assert reconstructed.id == sample_button_config.id
    assert reconstructed.slot_index == 3
    assert reconstructed.title == "Mic Control"
    assert reconstructed.icon == "🎙"
    assert reconstructed.color_accent == "#ff0055"
    assert reconstructed.status_source == "mic_mute"
    assert reconstructed.sound_override == "resources/deck/sounds/custom_click.wav"
    assert reconstructed.toggle_action is not None
    assert reconstructed.toggle_action.action_type == "system"
    assert reconstructed.toggle_action.params["command"] == "toggle_mic_mute"
    assert reconstructed.action.action_type == "hotkey"
    assert reconstructed.action.params["keys"] == ["ctrl", "shift", "m"]


def test_dto_modification_preserves_unmodified_extended_fields(sample_button_config: DeckButtonConfig):
    """
    При изменении пользователем только заголовка и хоткея в DTO,
    расширенные метаданные (status_source, sound_override, toggle_action) остаются неизменными.
    """
    dto = DeckConfigAdapter.slot_to_dto(sample_button_config)

    # Пользователь меняет заголовок и хоткей в инспекторе
    dto.title = "New Mute Hotkey"
    dto.hotkey = "Ctrl + Alt + F12"
    dto.color_accent = "#38bdf8"

    reconstructed = DeckConfigAdapter.dto_to_slot(dto)

    assert reconstructed.title == "New Mute Hotkey"
    assert reconstructed.color_accent == "#38bdf8"
    assert reconstructed.action.action_type == "hotkey"
    assert reconstructed.action.params["keys"] == ["ctrl", "alt", "f12"]

    # Расширенные поля сохранены из исходного объекта без потерь
    assert reconstructed.status_source == "mic_mute"
    assert reconstructed.sound_override == "resources/deck/sounds/custom_click.wav"
    assert reconstructed.toggle_action is not None
    assert reconstructed.toggle_action.params["command"] == "toggle_mic_mute"


def test_dto_to_slot_creates_valid_new_button_without_original():
    """
    Создание абсолютно нового слота без original_config
    порождает валидный DeckButtonConfig с соблюдением контракта Pydantic v2.
    """
    new_dto = ButtonSlotDTO(
        slot_index=7,
        title="Discord Deaf",
        icon="🎧",
        category="shortcut",
        action_type="Hotkey",
        hotkey="Ctrl + Shift + D",
        color_accent="#818cf8",
        status_source="audio_deaf",
        sound_override="sounds/tap.wav",
        toggle_action=DeckActionConfig(action_type="system", params={"command": "toggle_master_mute"}),
    )

    btn = DeckConfigAdapter.dto_to_slot(new_dto)

    assert isinstance(btn, DeckButtonConfig)
    assert btn.slot_index == 7
    assert btn.title == "Discord Deaf"
    assert btn.icon == "🎧"
    assert btn.category == "shortcut"
    assert btn.color_accent == "#818cf8"
    assert btn.status_source == "audio_deaf"
    assert btn.sound_override == "sounds/tap.wav"
    assert btn.toggle_action is not None
    assert btn.action.action_type == "hotkey"
    assert btn.action.params["keys"] == ["ctrl", "shift", "d"]


def test_slot_to_dto_handles_all_action_types():
    """Проверка корректной трансляции всех поддерживаемых ActionType."""
    action_types = [
        ("launch", {"path": "notepad.exe", "args": []}, "Open Application", "System: Open Application"),
        ("audio_device", {"mode": "toggle", "devices": ["A", "B"]}, "Audio Device", "System: Audio Device"),
        ("system", {"command": "toggle_dimmer"}, "System", "System"),
        ("screenshot", {"target": "primary_screen"}, "Screenshot", "System: Screenshot"),
        ("http_request", {"url": "http://127.0.0.1"}, "HTTP Request", "API: HTTP Request"),
        ("navigation", {"target_page_id": "page_2"}, "Navigation", "Navigation"),
    ]

    for act_type, params, exp_action, exp_cat in action_types:
        cfg = DeckButtonConfig(
            id=f"btn_{act_type}",
            slot_index=0,
            title=f"Test {act_type}",
            category="system",
            icon="⚡",
            action=DeckActionConfig(action_type=act_type, params=params),
        )
        dto = DeckConfigAdapter.slot_to_dto(cfg)
        assert dto.action_type == exp_action
        assert dto.category == exp_cat


# ==============================================================================
# 2. Тесты многостраничного контекста и изоляции страниц (Pages 1..N)
# ==============================================================================


def test_load_page_slots_returns_all_ten_slots(multi_page_root_config: DeckRootConfig):
    """
    load_page_slots загружает слоты для конкретной страницы:
    заполненные слоты конвертируются, отсутствующие инициализируются как пустые.
    """
    # Загрузка страницы "page_main" (содержит слоты 0 и 3)
    slots = DeckConfigAdapter.load_page_slots(multi_page_root_config, "page_main")

    assert len(slots) == 10
    assert slots[0].title == "Page1 Button 0"
    assert slots[3].title == "Mic Control"
    assert slots[3].status_source == "mic_mute"

    # Пустые слоты инициализированы дефолтным ButtonSlotDTO
    for i in [1, 2, 4, 5, 6, 7, 8, 9]:
        assert slots[i].slot_index == i
        assert slots[i].title == ""


def test_load_page_slots_by_index_and_fallback(multi_page_root_config: DeckRootConfig):
    """Проверка загрузки по числовому индексу и возврата чистых слотов при неизвестном ID (без fallback на 1-ю)."""
    # По индексу 1 (page_media)
    slots_media = DeckConfigAdapter.load_page_slots(multi_page_root_config, 1)
    assert slots_media[1].title == "Page2 Button 1"

    # Несуществующая страница -> пустые чистые слоты (без fallback на первую страницу)
    empty_slots = DeckConfigAdapter.load_page_slots(multi_page_root_config, "non_existent_page_id")
    assert len(empty_slots) == 10
    assert empty_slots[0].title == ""
    assert not empty_slots[0].hotkey


def test_apply_slots_to_page_modifies_only_target_page(multi_page_root_config: DeckRootConfig):
    """
    apply_slots_to_page изменяет ТОЛЬКО целевую страницу, не затрагивая соседние.
    Исключает утечки данных и разрушение структуры многостраничного DeckRootConfig.
    """
    # Загружаем слоты 2-й страницы (page_media)
    slots_page2 = DeckConfigAdapter.load_page_slots(multi_page_root_config, "page_media")

    # Модифицируем слот 1 и добавляем слот 4 на странице 2
    slots_page2[1].title = "Updated Media Title"
    slots_page2[4] = ButtonSlotDTO(
        slot_index=4,
        title="Volume Down",
        icon="🔉",
        hotkey="Ctrl + Alt + Down",
        color_accent="#ef4444",
    )

    # Применяем изменения
    updated_root = DeckConfigAdapter.apply_slots_to_page(
        multi_page_root_config, "page_media", slots_page2
    )

    # 1. Количество страниц осталось неизменным
    assert len(updated_root.pages) == 3

    # 2. Страница 1 (page_main) осталась полностью нетронутой
    assert len(updated_root.pages[0].buttons) == 2
    assert updated_root.pages[0].buttons[0].title == "Page1 Button 0"
    assert updated_root.pages[0].buttons[1].title == "Mic Control"
    assert updated_root.pages[0].buttons[1].status_source == "mic_mute"

    # 3. Страница 3 (page_dev) осталась нетронутой
    assert len(updated_root.pages[2].buttons) == 1
    assert updated_root.pages[2].buttons[0].title == "Terminal"

    # 4. Страница 2 (page_media) обновилась
    p2_buttons = {b.slot_index: b for b in updated_root.pages[1].buttons}
    assert len(p2_buttons) == 2
    assert p2_buttons[1].title == "Updated Media Title"
    assert p2_buttons[4].title == "Volume Down"
    assert p2_buttons[4].color_accent == "#ef4444"


def test_apply_slots_to_page_clears_deleted_buttons(multi_page_root_config: DeckRootConfig):
    """
    Если пользователь удалил кнопку корзиной 🗑️, очищенный слот исключается из массива кнопок.
    """
    slots_page1 = DeckConfigAdapter.load_page_slots(multi_page_root_config, "page_main")

    # Имитируем очистку слота 0 через корзину (как в Window._on_inspector_slot_cleared)
    slots_page1[0] = ButtonSlotDTO(
        slot_index=0,
        title="",
        icon="",
        category="",
        action_type="",
        hotkey="",
    )

    updated_root = DeckConfigAdapter.apply_slots_to_page(
        multi_page_root_config, "page_main", slots_page1
    )

    # На странице 1 осталась только кнопка слота 3, слот 0 удален
    assert len(updated_root.pages[0].buttons) == 1
    assert updated_root.pages[0].buttons[0].slot_index == 3


# ==============================================================================
# 3. Тесты атомарного сохранения, создания .tmp/.bak и устойчивости к сбоям I/O
# ==============================================================================


def test_save_deck_config_atomic_success(multi_page_root_config: DeckRootConfig):
    """Успешное сохранение: создает целевой файл, а повторное сохранение создает .bak."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_path = os.path.join(tmp_dir, "sub_dir", "deck_config.json")

        # 1. Первое сохранение (создает директорию и файл)
        success1 = DeckConfigAdapter.save_deck_config_atomic(multi_page_root_config, cfg_path)
        assert success1 is True
        assert os.path.isfile(cfg_path)
        assert not os.path.exists(f"{cfg_path}.tmp")

        # Проверяем, что файл валидно читается и парсится
        loaded = DeckConfigAdapter.load_deck_config(cfg_path)
        assert len(loaded.pages) == 3
        assert loaded.pages[0].buttons[1].title == "Mic Control"

        # 2. Второе сохранение (должен появиться .bak файл)
        multi_page_root_config.active_profile = "page_dev"
        success2 = DeckConfigAdapter.save_deck_config_atomic(multi_page_root_config, cfg_path)
        assert success2 is True
        assert os.path.isfile(f"{cfg_path}.bak")

        # Проверяем бэкап: в нем старый active_profile == "page_main"
        with open(f"{cfg_path}.bak", "r", encoding="utf-8") as f:
            bak_data = json.load(f)
        assert bak_data["active_profile"] == "page_main"

        # В основном файле новый active_profile == "page_dev"
        with open(cfg_path, "r", encoding="utf-8") as f:
            new_data = json.load(f)
        assert new_data["active_profile"] == "page_dev"


def test_save_deck_config_atomic_io_error_resilience(multi_page_root_config: DeckRootConfig):
    """
    При сбое I/O в момент записи во временный файл:
    - метод возвращает False;
    - временный файл .tmp очищается;
    - исходный боевой файл не повреждается (не становится 0 байт).
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_path = os.path.join(tmp_dir, "deck_config.json")

        # Первичное успешное сохранение
        assert DeckConfigAdapter.save_deck_config_atomic(multi_page_root_config, cfg_path) is True
        original_size = os.path.getsize(cfg_path)
        assert original_size > 0

        # Имитируем сбой I/O при записи во временный файл
        with patch("builtins.open", side_effect=IOError("Simulated disk write failure")):
            success = DeckConfigAdapter.save_deck_config_atomic(multi_page_root_config, cfg_path)
            assert success is False

        # Проверяем сохранность исходного файла
        assert os.path.isfile(cfg_path)
        assert os.path.getsize(cfg_path) == original_size
        assert not os.path.exists(f"{cfg_path}.tmp")


def test_save_deck_config_atomic_replace_failure_cleans_tmp(multi_page_root_config: DeckRootConfig):
    """
    При сбое os.replace():
    - временный файл .tmp безопасно удаляется;
    - метод возвращает False;
    - боевой файл остается интактным.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_path = os.path.join(tmp_dir, "deck_config.json")
        assert DeckConfigAdapter.save_deck_config_atomic(multi_page_root_config, cfg_path) is True

        with patch("os.replace", side_effect=OSError("Access denied during atomic swap")):
            success = DeckConfigAdapter.save_deck_config_atomic(multi_page_root_config, cfg_path)
            assert success is False

        # Временный файл не остался мусором
        assert not os.path.exists(f"{cfg_path}.tmp")
        # Боевой файл целый
        loaded = DeckConfigAdapter.load_deck_config(cfg_path)
        assert len(loaded.pages) == 3


def test_save_deck_config_atomic_handles_validation_error():
    """
    При передаче некорректных данных (невалидный Pydantic объект):
    - метод возвращает False;
    - диск не трогается, никаких файлов не создается.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_path = os.path.join(tmp_dir, "corrupted_config.json")

        invalid_data = {"pages": "invalid_not_a_list_structure"}  # Невалидная структура для DeckRootConfig

        success = DeckConfigAdapter.save_deck_config_atomic(invalid_data, cfg_path)
        assert success is False
        assert not os.path.exists(cfg_path)
        assert not os.path.exists(f"{cfg_path}.tmp")
