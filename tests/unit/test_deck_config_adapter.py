"""
Модульные тесты адаптера конфигурации DuckDeck (DeckConfigAdapter) согласно шагу 5.1.
Проверяет:
  - test_adapter_load_valid_config
  - test_adapter_dto_to_config_merge_preserves_extra_fields
  - test_adapter_save_atomic_write_and_backup
  - test_adapter_corrupted_json_recovery
"""
import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest

from modules.deck.editor.adapter import DeckConfigAdapter
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.models import (
    DeckActionConfig,
    DeckButtonConfig,
    DeckConfigLoader,
    DeckPageConfig,
    DeckRootConfig,
)


def test_adapter_load_valid_config(tmp_path: Path):
    """Тест загрузки валидной конфигурации и построения словаря DTO активной страницы."""
    config_file = tmp_path / "deck_test_config.json"
    root_cfg = DeckConfigLoader.get_default_config()
    DeckConfigAdapter.save_deck_config_atomic(root_cfg, str(config_file))

    loaded_root = DeckConfigAdapter.load_deck_config(str(config_file))
    assert len(loaded_root.pages) > 0

    slots_dto = DeckConfigAdapter.load_page_slots(loaded_root, "default")
    assert isinstance(slots_dto, dict)
    assert len(slots_dto) == 10
    for idx in range(10):
        assert idx in slots_dto
        assert slots_dto[idx].slot_index == idx


def test_adapter_dto_to_config_merge_preserves_extra_fields():
    """Редактирование полей в DTO сохраняет немодифицированные поля Pydantic (status_source, sound_override, etc)."""
    orig_button = DeckButtonConfig(
        id="btn_sample",
        slot_index=2,
        name="Original Name",
        title="Original Title",
        category="system",
        icon="🎧",
        icon_path="resources/deck/icons/headphone.png",
        icon_size=48,
        color_accent="#ef4444",
        background_color="#161b26",
        status_source="audio_device",
        sound_override="resources/deck/sounds/click.wav",
        action=DeckActionConfig(
            action_type="audio_device",
            params={"mode": "toggle", "devices": ["Наушники", "Динамики"]},
        ),
        toggle_action=DeckActionConfig(
            action_type="system",
            params={"command": "toggle_mic_mute"},
        ),
    )

    dto = DeckConfigAdapter.slot_to_dto(orig_button)
    assert dto.title == "Original Title"
    assert dto.icon == "🎧"

    # Пользователь изменил заголовок и акцент в инспекторе
    dto.title = "New Headphones"
    dto.icon = "🎵"
    dto.color_accent = "#38bdf8"

    # Обратное слияние в DeckButtonConfig
    merged = DeckConfigAdapter.dto_to_slot(dto, original_config=orig_button)

    assert merged.title == "New Headphones"
    assert merged.icon == "🎵"
    assert merged.color_accent == "#38bdf8"
    # Сохраненные поля
    assert merged.status_source == "audio_device"
    assert merged.sound_override == "resources/deck/sounds/click.wav"
    assert merged.toggle_action is not None
    assert merged.toggle_action.action_type == "system"


def test_adapter_save_atomic_write_and_backup(tmp_path: Path):
    """Проверка атомарной записи (.tmp -> replace) и создания резервной копии (.bak)."""
    config_file = tmp_path / "deck_atomic.json"
    root_cfg = DeckConfigLoader.get_default_config()

    # Первое сохранение
    ok = DeckConfigAdapter.save_deck_config_atomic(root_cfg, str(config_file))
    assert ok is True
    assert config_file.exists()

    # Второе сохранение (должен появиться .bak)
    root_cfg.pages[0].name = "Updated Page Name"
    ok2 = DeckConfigAdapter.save_deck_config_atomic(root_cfg, str(config_file))
    assert ok2 is True

    bak_file = tmp_path / "deck_atomic.json.bak"
    assert bak_file.exists()

    tmp_file = tmp_path / "deck_atomic.json.tmp"
    assert not tmp_file.exists(), "Временный файл .tmp обязан быть очищен"


def test_adapter_corrupted_json_recovery(tmp_path: Path):
    """Симуляция поврежденного файла JSON — адаптер восстанавливает данные из .bak или дефолтной схемы."""
    config_file = tmp_path / "deck_corrupted.json"
    bak_file = tmp_path / "deck_corrupted.json.bak"

    # Создаем валидный .bak
    valid_root = DeckConfigLoader.get_default_config()
    with open(bak_file, "w", encoding="utf-8") as f:
        json.dump(valid_root.model_dump(), f)

    # Записываем мусор в основной файл
    with open(config_file, "w", encoding="utf-8") as f:
        f.write("{ INVALID JSON DATA --- CORRUPTED !!!")

    recovered = DeckConfigAdapter.load_deck_config(str(config_file))
    assert isinstance(recovered, DeckRootConfig)
    assert len(recovered.pages) > 0
