"""
Модульные тесты расширенных действий DuckDeck v0.6.0 (Extended Actions).
Проверяет валидацию Pydantic v2 моделей и безопасное исполнение в ActionRunnable:
  - website, open_path, open_app, close_window
  - text_macro, multimedia, volume_control, hotkey_switch
"""
import ctypes
from unittest.mock import MagicMock, patch
import pytest

from modules.deck.action_dispatcher import ActionRunnable, WorkerSignals
from modules.deck.models import (
    CloseWindowParams,
    DeckActionConfig,
    HotkeySwitchParams,
    HotkeySwitchState,
    MultimediaParams,
    OpenAppParams,
    OpenPathParams,
    TextMacroParams,
    VolumeControlParams,
    WebsiteParams,
)


def test_extended_actions_pydantic_validation() -> None:
    """Проверка строгой валидации Pydantic v2 моделей для новых типов действий."""
    # 1. WebsiteParams
    w = WebsiteParams(url="https://github.com")
    assert w.url == "https://github.com"

    # 2. HotkeySwitchParams
    hs = HotkeySwitchParams(
        state_1=HotkeySwitchState(title="Mute", keys=["ctrl", "m"]),
        state_2=HotkeySwitchState(title="Unmute", keys=["ctrl", "u"]),
        current_state=1,
    )
    assert hs.state_1.title == "Mute"
    assert hs.state_2.keys == ["ctrl", "u"]
    assert hs.current_state == 1

    # 3. OpenPathParams
    op = OpenPathParams(path="C:\\Docs\\Report.pdf")
    assert op.path == "C:\\Docs\\Report.pdf"

    # 4. OpenAppParams
    oa = OpenAppParams(executable="calc.exe", args=["/test"], working_dir="C:\\")
    assert oa.executable == "calc.exe"
    assert oa.args == ["/test"]
    assert oa.working_dir == "C:\\"

    # 5. CloseWindowParams
    cw = CloseWindowParams(target="active_window")
    assert cw.target == "active_window"

    # 6. TextMacroParams
    tm = TextMacroParams(text="Hello World", send_enter=True)
    assert tm.text == "Hello World"
    assert tm.send_enter is True

    # 7. MultimediaParams
    mm = MultimediaParams(command="play_pause")
    assert mm.command == "play_pause"

    # 8. VolumeControlParams
    vc = VolumeControlParams(target="focus_app", command="volume_up", step_percent=10)
    assert vc.target == "focus_app"
    assert vc.command == "volume_up"
    assert vc.step_percent == 10


def test_deck_action_config_typed_params_factory() -> None:
    """Проверка фабричного метода get_typed_params() для всех расширенных действий."""
    cfg_web = DeckActionConfig(action_type="website", params={"url": "https://example.com"})
    assert isinstance(cfg_web.get_typed_params(), WebsiteParams)

    cfg_switch = DeckActionConfig(
        action_type="hotkey_switch",
        params={
            "state_1": {"title": "S1", "keys": ["f1"]},
            "state_2": {"title": "S2", "keys": ["f2"]},
            "current_state": 1,
        },
    )
    assert isinstance(cfg_switch.get_typed_params(), HotkeySwitchParams)

    cfg_path = DeckActionConfig(action_type="open_path", params={"path": "C:\\Folder"})
    assert isinstance(cfg_path.get_typed_params(), OpenPathParams)

    cfg_app = DeckActionConfig(action_type="open_app", params={"executable": "app.exe"})
    assert isinstance(cfg_app.get_typed_params(), OpenAppParams)

    cfg_close = DeckActionConfig(action_type="close_window", params={"target": "active_window"})
    assert isinstance(cfg_close.get_typed_params(), CloseWindowParams)

    cfg_macro = DeckActionConfig(action_type="text_macro", params={"text": "test", "send_enter": False})
    assert isinstance(cfg_macro.get_typed_params(), TextMacroParams)

    cfg_media = DeckActionConfig(action_type="multimedia", params={"command": "next_track"})
    assert isinstance(cfg_media.get_typed_params(), MultimediaParams)

    cfg_vol = DeckActionConfig(action_type="volume_control", params={"target": "master", "command": "toggle_mute"})
    assert isinstance(cfg_vol.get_typed_params(), VolumeControlParams)


def test_action_runnable_website_execution() -> None:
    """Тестирование безопасного открытия URL сайта в ActionRunnable."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    action_cfg = DeckActionConfig(action_type="website", params={"url": "github.com"})
    runnable = ActionRunnable("btn_web", action_cfg, signals)

    with patch("os.startfile") as mock_startfile:
        runnable.run()
        mock_startfile.assert_called_once_with("https://github.com")

    assert len(results) == 1
    assert results[0][1] is True


def test_action_runnable_open_path_execution() -> None:
    """Тестирование открытия пути или файла через os.startfile."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    action_cfg = DeckActionConfig(action_type="open_path", params={"path": "C:\\fake\\file.txt"})
    runnable = ActionRunnable("btn_path", action_cfg, signals)

    with patch("os.path.exists", return_value=True), patch("os.startfile") as mock_startfile:
        runnable.run()
        mock_startfile.assert_called_once_with("C:\\fake\\file.txt")

    assert len(results) == 1
    assert results[0][1] is True


def test_action_runnable_open_app_execution() -> None:
    """Тестирование запуска приложения через subprocess.Popen."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    action_cfg = DeckActionConfig(
        action_type="open_app",
        params={"executable": "notepad.exe", "args": ["file.txt"]},
    )
    runnable = ActionRunnable("btn_app", action_cfg, signals)

    with patch("subprocess.Popen") as mock_popen:
        runnable.run()
        mock_popen.assert_called_once_with(["notepad.exe", "file.txt"], cwd=None, shell=False)

    assert len(results) == 1
    assert results[0][1] is True


def test_action_runnable_close_window_execution() -> None:
    """Тестирование отправки WM_CLOSE активному окну."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    action_cfg = DeckActionConfig(action_type="close_window", params={"target": "active_window"})
    runnable = ActionRunnable("btn_close", action_cfg, signals)

    with patch("ctypes.windll.user32.GetForegroundWindow", return_value=12345), \
         patch("ctypes.windll.user32.PostMessageW") as mock_post:
        runnable.run()
        mock_post.assert_called_once_with(12345, 0x0010, 0, 0)

    assert len(results) == 1
    assert results[0][1] is True


def test_action_runnable_text_macro_execution() -> None:
    """Тестирование вставки текстового макроса."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    action_cfg = DeckActionConfig(action_type="text_macro", params={"text": "Привет", "send_enter": True})
    runnable = ActionRunnable("btn_macro", action_cfg, signals)

    with patch("modules.deck.action_dispatcher.send_hotkey") as mock_hotkey, \
         patch("win32clipboard.OpenClipboard"), \
         patch("win32clipboard.EmptyClipboard"), \
         patch("win32clipboard.SetClipboardText"), \
         patch("win32clipboard.CloseClipboard"):
        runnable.run()
        # Должен быть вызван send_hotkey(["ctrl", "v"]) и send_hotkey(["enter"])
        assert mock_hotkey.call_count == 2
        mock_hotkey.assert_any_call(["ctrl", "v"])
        mock_hotkey.assert_any_call(["enter"])

    assert len(results) == 1
    assert results[0][1] is True


def test_action_runnable_multimedia_keys_execution() -> None:
    """Тестирование симуляции мультимедийных клавиш keybd_event."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    action_cfg = DeckActionConfig(action_type="multimedia", params={"command": "play_pause"})
    runnable = ActionRunnable("btn_media", action_cfg, signals)

    with patch("ctypes.windll.user32.keybd_event") as mock_keybd:
        runnable.run()
        # Должно быть нажатие (0xCD, 0, 0, 0) и отпускание (0xCD, 0, 2, 0)
        assert mock_keybd.call_count == 2
        mock_keybd.assert_any_call(0xCD, 0, 0, 0)
        mock_keybd.assert_any_call(0xCD, 0, 2, 0)

    assert len(results) == 1
    assert results[0][1] is True


def test_action_runnable_volume_control_execution() -> None:
    """Тестирование управления громкостью через AudioManager."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    mock_audio = MagicMock()
    mock_audio.toggle_mic_mute.return_value = True

    action_cfg = DeckActionConfig(action_type="volume_control", params={"target": "microphone", "command": "toggle_mute"})
    runnable = ActionRunnable("btn_vol", action_cfg, signals, audio_manager=mock_audio)

    runnable.run()
    mock_audio.toggle_mic_mute.assert_called_once()
    assert len(results) == 1
    assert results[0][1] is True


def test_action_runnable_hotkey_switch_toggle() -> None:
    """Тестирование переключения состояний в hotkey_switch."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    action_cfg = DeckActionConfig(
        action_type="hotkey_switch",
        params={
            "state_1": {"title": "State A", "keys": ["ctrl", "1"]},
            "state_2": {"title": "State B", "keys": ["ctrl", "2"]},
            "current_state": 1,
        },
    )

    with patch("modules.deck.action_dispatcher.send_hotkey", return_value=True) as mock_send:
        # Первое нажатие: активен State 1 (keys: ctrl+1), переход в State 2
        runnable1 = ActionRunnable("btn_sw", action_cfg, signals)
        runnable1.run()
        mock_send.assert_called_with(["ctrl", "1"])
        assert action_cfg.params["current_state"] == 2

        # Второе нажатие: активен State 2 (keys: ctrl+2), переход в State 1
        runnable2 = ActionRunnable("btn_sw", action_cfg, signals)
        runnable2.run()
        mock_send.assert_called_with(["ctrl", "2"])
        assert action_cfg.params["current_state"] == 1

    assert len(results) == 2
    assert results[0][1] is True
    assert results[1][1] is True


# ==============================================================================
# Step 5.3 Tests & Aliases
# ==============================================================================

test_action_hotkey_switch_toggle = test_action_runnable_hotkey_switch_toggle
test_action_multimedia_keys = test_action_runnable_multimedia_keys_execution
test_action_volume_controller = test_action_runnable_volume_control_execution


def test_action_app_open_safe_execution() -> None:
    """Безопасный запуск приложения: проверка пути, мокированный subprocess.Popen, обработка FileNotFoundError."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    cfg = DeckActionConfig(action_type="open_app", params={"executable": "cmd.exe", "args": ["/c", "dir"]})
    r = ActionRunnable("btn_app1", cfg, signals)
    with patch("subprocess.Popen") as mock_pop:
        r.run()
        mock_pop.assert_called_once_with(["cmd.exe", "/c", "dir"], cwd=None, shell=False)
    assert results[-1][1] is True

    cfg_err = DeckActionConfig(action_type="open_app", params={"executable": "nonexistent_app_123.exe"})
    r_err = ActionRunnable("btn_app2", cfg_err, signals)
    with patch("subprocess.Popen", side_effect=FileNotFoundError("Not found")):
        r_err.run()
    assert results[-1][1] is False


def test_action_app_close_graceful() -> None:
    """Отправка WM_CLOSE окну с безопасной обработкой случая, когда окно отсутствует."""
    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    cfg = DeckActionConfig(action_type="close_window", params={"target": "active_window"})
    r = ActionRunnable("btn_c1", cfg, signals)
    with patch("ctypes.windll.user32.GetForegroundWindow", return_value=999), \
         patch("ctypes.windll.user32.PostMessageW") as mock_post:
        r.run()
        mock_post.assert_called_once_with(999, 0x0010, 0, 0)
    assert results[-1][1] is True

    r2 = ActionRunnable("btn_c2", cfg, signals)
    with patch("ctypes.windll.user32.GetForegroundWindow", return_value=0):
        r2.run()
    assert results[-1][1] is False


def test_actions_pydantic_validation_safety() -> None:
    """Проверка валидации параметров Pydantic v2: обработка невалидных параметров без краша."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WebsiteParams.model_validate({"url": 12345})

    with pytest.raises(ValidationError):
        HotkeySwitchParams.model_validate({"current_state": 5})

    with pytest.raises(ValidationError):
        MultimediaParams.model_validate({"command": "invalid_command"})

    with pytest.raises(ValidationError):
        VolumeControlParams.model_validate({"target": "unknown_target", "command": "set_level"})

