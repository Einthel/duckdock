"""
Модульные тесты для реестра шаблонов действий ActionPresetsRegistry (modules/deck/presets.py)
и изолированных исполнителей базовых примитивов (modules/deck/executors.py).
"""
import os
from unittest.mock import MagicMock, patch
import pytest

from modules.deck.action_dispatcher import ActionRunnable, WorkerSignals
from modules.deck.executors import (
    AudioExecutor,
    DeckNavExecutor,
    HotkeyExecutor,
    LaunchExecutor,
    MacroExecutor,
    MediaExecutor,
    SystemExecutor,
    TextExecutor,
)
from modules.deck.models import (
    AudioActionParams,
    DeckActionConfig,
    DeckNavActionParams,
    HotkeyActionParams,
    LaunchActionParams,
    MacroActionParams,
    MediaActionParams,
    SystemActionParams,
    TextActionParams,
)
from modules.deck.presets import ActionPresetsRegistry


def test_action_presets_registry_structure_and_coverage():
    """Проверка наполнения реестра пресетов, категорий и DTO представления."""
    presets = ActionPresetsRegistry.get_all_presets()
    assert len(presets) >= 26

    # 8 базовых категорий
    assert len(ActionPresetsRegistry.CATEGORIES) == 8
    cat_ids = {c["id"] for c in ActionPresetsRegistry.CATEGORIES}
    expected_cats = {
        "audio_comm",
        "media_stream",
        "launchers",
        "system_control",
        "input_macros",
        "navigation",
        "soundboard",
        "multi_action",
    }
    assert cat_ids == expected_cats

    # Проверка получения пресета по ID
    p_dev = ActionPresetsRegistry.get_preset_by_id("output_device_toggle")
    assert p_dev is not None
    assert p_dev.category == "audio_comm"
    assert p_dev.base_action.action_type == "audio"
    assert p_dev.status_source == "audio_device"

    # Проверка фильтрации по категории
    media_presets = ActionPresetsRegistry.get_presets_by_category("media_stream")
    assert len(media_presets) >= 5

    # Проверка DTO категорий
    categories_dto = ActionPresetsRegistry.get_categories_dto()
    assert len(categories_dto) == 8
    for cat_dto in categories_dto:
        assert cat_dto.id in cat_ids
        assert len(cat_dto.items) > 0

    # Проверка поиска по ключевым словам (RU и EN)
    res_en = ActionPresetsRegistry.search_presets("discord")
    assert len(res_en) >= 2
    res_ru = ActionPresetsRegistry.search_presets("дискорд")
    assert len(res_ru) >= 2


def test_hotkey_executor():
    """Тест изолированного HotkeyExecutor (press и toggle)."""
    # Press
    p_press = HotkeyActionParams(keys=["ctrl", "c"], mode="press")
    with patch("modules.deck.executors.send_hotkey", return_value=True) as mock_send:
        ok, msg = HotkeyExecutor.execute(p_press)
        assert ok is True
        mock_send.assert_called_once_with(["ctrl", "c"])

    # Toggle
    cfg = DeckActionConfig(
        action_type="hotkey",
        params={"keys": ["ctrl", "m"], "mode": "toggle", "toggle_keys": ["ctrl", "u"], "current_state": 1},
    )
    p_toggle = cfg.get_typed_params()
    with patch("modules.deck.executors.send_hotkey", return_value=True) as mock_send:
        ok, msg = HotkeyExecutor.execute(p_toggle, action_config=cfg)
        assert ok is True
        mock_send.assert_called_once_with(["ctrl", "m"])
        assert cfg.params["current_state"] == 2

        # Второе нажатие
        mock_send.reset_mock()
        ok, msg = HotkeyExecutor.execute(p_toggle, action_config=cfg)
        assert ok is True
        mock_send.assert_called_once_with(["ctrl", "u"])
        assert cfg.params["current_state"] == 1


def test_launch_executor():
    """Тест изолированного LaunchExecutor (url, file, app)."""
    # URL
    p_url = LaunchActionParams(target="google.com", kind="url")
    with patch("os.startfile") as mock_start:
        ok, msg = LaunchExecutor.execute(p_url)
        assert ok is True
        mock_start.assert_called_once_with("https://google.com")

    # File
    p_file = LaunchActionParams(target="C:\\test\\doc.txt", kind="file")
    with patch("os.path.exists", return_value=True), patch("os.startfile") as mock_start:
        ok, msg = LaunchExecutor.execute(p_file)
        assert ok is True
        mock_start.assert_called_once_with("C:\\test\\doc.txt")

    # App
    p_app = LaunchActionParams(target="notepad.exe", args=["test.txt"], kind="app")
    with patch("subprocess.Popen") as mock_popen:
        ok, msg = LaunchExecutor.execute(p_app)
        assert ok is True
        mock_popen.assert_called_once()


def test_audio_executor():
    """Тест изолированного AudioExecutor (mic, master, device, soundboard)."""
    # Mic
    p_mic = AudioActionParams(target="mic", command="toggle_mute")
    mock_audio_mgr = MagicMock()
    mock_audio_mgr.toggle_mic_mute.return_value = True
    ok, msg = AudioExecutor.execute(p_mic, audio_manager=mock_audio_mgr)
    assert ok is True
    mock_audio_mgr.toggle_mic_mute.assert_called_once()

    # Master mute
    p_master = AudioActionParams(target="master", command="toggle_mute")
    mock_audio_mgr.toggle_master_mute.return_value = False
    ok, msg = AudioExecutor.execute(p_master, audio_manager=mock_audio_mgr)
    assert ok is True
    mock_audio_mgr.toggle_master_mute.assert_called_once()

    # Soundboard
    play_called = []
    p_sb = AudioActionParams(target="soundboard", command="play_sound", file_path="click.wav")
    ok, msg = AudioExecutor.execute(
        p_sb,
        play_sound_emitter=lambda p, v, s: play_called.append((p, v, s)),
    )
    assert ok is True
    assert len(play_called) == 1
    assert play_called[0][0] == "click.wav"


def test_media_executor():
    """Тест изолированного MediaExecutor."""
    p_media = MediaActionParams(command="play_pause")
    with patch("ctypes.windll.user32.keybd_event") as mock_kb:
        ok, msg = MediaExecutor.execute(p_media)
        assert ok is True
        assert mock_kb.call_count == 2


def test_text_executor():
    """Тест изолированного TextExecutor."""
    p_text = TextActionParams(text="Hello DuckDock", send_enter=True)
    with patch("modules.deck.executors.send_hotkey") as mock_hotkey:
        ok, msg = TextExecutor.execute(p_text)
        assert ok is True
        # Ожидаем ctrl+v и enter
        assert mock_hotkey.call_count >= 2


def test_system_executor():
    """Тест изолированного SystemExecutor."""
    # Dimmer
    p_dim = SystemActionParams(command="dimmer")
    received = []
    from core.event_bus import bus
    bus.dimmer_toggle_requested.connect(lambda: received.append(True))
    ok, msg = SystemExecutor.execute(p_dim)
    assert ok is True
    assert len(received) == 1

    # Lock PC
    p_lock = SystemActionParams(command="lock_pc")
    with patch("ctypes.windll.user32.LockWorkStation", return_value=1) as mock_lock:
        ok, msg = SystemExecutor.execute(p_lock)
        assert ok is True
        mock_lock.assert_called_once()


def test_deck_nav_executor():
    """Тест изолированного DeckNavExecutor."""
    p_nav = DeckNavActionParams(target="goto_page", page_id="profile_2")
    received = []
    from core.event_bus import bus
    bus.deck_page_changed.connect(lambda p: received.append(p))
    ok, msg = DeckNavExecutor.execute(p_nav)
    assert ok is True
    assert "profile_2" in received


def test_macro_executor():
    """Тест изолированного MacroExecutor."""
    step1 = DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "c"]})
    step2 = DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "v"]})
    p_macro = MacroActionParams(steps=[step1, step2], delay_ms=10)

    executed = []
    def runner(step):
        executed.append(step)
        return True, "OK"

    ok, msg = MacroExecutor.execute(p_macro, single_action_runner=runner)
    assert ok is True
    assert len(executed) == 2
