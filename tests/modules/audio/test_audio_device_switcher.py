"""
Модульные тесты модуля переключения аудиоустройств Windows (IPolicyConfig)
и интеграции в фасад AudioManager с изоляцией WinAPI / COM через unittest.mock.
"""
from unittest.mock import MagicMock, call, patch

import pytest

from modules.audio.service import AudioManager
from modules.audio.models import AudioDeviceInfo
from modules.audio.platform import device_switcher
from modules.audio.platform.device_switcher import (
    ROLE_COMMUNICATIONS,
    ROLE_CONSOLE,
    ROLE_MULTIMEDIA,
    get_playback_devices,
    switch_default_device,
    toggle_audio_device,
)
from core.event_bus import bus


class DummyDeviceState:
    def __init__(self, val):
        self.value = val


class DummyAudioDevice:
    def __init__(self, dev_id, name, state_val=1):
        self.id = dev_id
        self.FriendlyName = name
        self.state = DummyDeviceState(state_val)

    def GetId(self):
        return self.id


# -------------------------------------------------------------
# 1. Тесты switch_default_device через IPolicyConfig
# -------------------------------------------------------------
@patch("modules.audio.platform.device_switcher.comtypes.CoUninitialize")
@patch("modules.audio.platform.device_switcher.comtypes.CoInitialize")
@patch("modules.audio.platform.device_switcher.comtypes.CoCreateInstance")
def test_switch_default_device_success(mock_co_create, mock_co_init, mock_co_uninit):
    """
    Тест успешного вызова SetDefaultEndpoint для всех трех ролей:
    eConsole (0), eMultimedia (1), eCommunications (2).
    """
    mock_policy = MagicMock()
    mock_policy.SetDefaultEndpoint.return_value = 0
    mock_co_create.return_value = mock_policy

    dev_id = "{0.0.0.00000000}.{test-device-guid}"
    result = switch_default_device(dev_id)

    assert result is True
    assert mock_policy.SetDefaultEndpoint.call_count == 3
    expected_calls = [
        call(dev_id, ROLE_CONSOLE),
        call(dev_id, ROLE_MULTIMEDIA),
        call(dev_id, ROLE_COMMUNICATIONS),
    ]
    mock_policy.SetDefaultEndpoint.assert_has_calls(expected_calls)
    mock_co_init.assert_called_once()
    mock_co_uninit.assert_called_once()


@patch("modules.audio.platform.device_switcher.comtypes.CoCreateInstance")
def test_switch_default_device_failure_handled(mock_co_create):
    """Тест обработки сбоя COM CoCreateInstance без падения программы."""
    mock_co_create.side_effect = Exception("COM Access Denied")

    result = switch_default_device("{0.0.0.00000000}.{err-guid}")
    assert result is False


# -------------------------------------------------------------
# 2. Тесты get_playback_devices
# -------------------------------------------------------------
@patch("modules.audio.platform.device_switcher.get_default_playback_device_id")
@patch("modules.audio.platform.device_switcher.AudioUtilities.GetAllDevices")
def test_get_playback_devices_filtering(mock_get_all, mock_get_default_id):
    """
    Тест фильтрации устройств: возвращаются только активные (state=1)
    устройства воспроизведения (префикс {0.0.0.00000000}.).
    """
    dev1 = DummyAudioDevice("{0.0.0.00000000}.{dev1}", "Наушники Sennheiser", state_val=1)
    dev2 = DummyAudioDevice("{0.0.0.00000000}.{dev2}", "Динамики Realtek", state_val=1)
    dev_unplugged = DummyAudioDevice("{0.0.0.00000000}.{dev3}", "Отключенные динамики", state_val=8)
    dev_mic = DummyAudioDevice("{0.0.1.00000000}.{mic1}", "Микрофон USB", state_val=1)

    mock_get_all.return_value = [dev1, dev2, dev_unplugged, dev_mic]
    mock_get_default_id.return_value = "{0.0.0.00000000}.{dev1}"

    devices = get_playback_devices()

    assert len(devices) == 2
    assert devices[0].name == "Наушники Sennheiser"
    assert devices[0].is_default is True
    assert devices[1].name == "Динамики Realtek"
    assert devices[1].is_default is False


# -------------------------------------------------------------
# 3. Тесты циклического переключения toggle_audio_device
# -------------------------------------------------------------
@patch("modules.audio.platform.device_switcher.switch_default_device")
@patch("modules.audio.platform.device_switcher.get_playback_devices")
def test_toggle_audio_device_cycles_between_targets(mock_get_devices, mock_switch):
    """Тест циклического переключения между списком ключевых слов target."""
    dev_head = AudioDeviceInfo(id="{0.0.0.00000000}.{head}", name="Headset G435", is_default=True)
    dev_spk = AudioDeviceInfo(id="{0.0.0.00000000}.{spk}", name="Динамики Creative", is_default=False)
    dev_other = AudioDeviceInfo(id="{0.0.0.00000000}.{other}", name="AMD HDMI", is_default=False)

    mock_get_devices.return_value = [dev_head, dev_spk, dev_other]
    mock_switch.return_value = True

    # 1. Текущий - Наушники -> переключается на Динамики
    next_dev = toggle_audio_device(targets=["Headset", "Динамики"])
    assert next_dev is not None
    assert next_dev.id == dev_spk.id
    mock_switch.assert_called_with(dev_spk.id)

    # 2. Если теперь текущий - Динамики -> переключается обратно на Наушники
    dev_head.is_default = False
    dev_spk.is_default = True
    next_dev_2 = toggle_audio_device(targets=["Headset", "Динамики"])
    assert next_dev_2 is not None
    assert next_dev_2.id == dev_head.id
    mock_switch.assert_called_with(dev_head.id)


# -------------------------------------------------------------
# 4. Тесты интеграции в AudioManager и EventBus
# -------------------------------------------------------------
def test_audio_manager_playback_device_switching():
    """Тест вызова смены устройства через AudioManager и эмиссии сигналов EventBus."""
    mgr = AudioManager()

    with patch("modules.audio.platform.device_switcher.switch_default_device", return_value=True) as mock_switch:
        with patch.object(mgr, "get_master_device_name", return_value="Наушники Sennheiser"):
            with patch.object(mgr, "get_master_volume", return_value=0.75):
                with patch.object(mgr, "is_master_muted", return_value=False):
                    signals_received = []
                    bus.playback_device_changed.connect(lambda name, d_id: signals_received.append((name, d_id)))

                    target_id = "{0.0.0.00000000}.{test_headphones}"
                    success = mgr.set_default_playback_device(target_id)

                    assert success is True
                    mock_switch.assert_called_once_with(target_id)
                    assert len(signals_received) == 1
                    assert signals_received[0] == ("Наушники Sennheiser", target_id)


def test_audio_manager_mic_mute_control():
    """Тест методов управления микрофоном (is_mic_muted, set_mic_mute, toggle_mic_mute)."""
    mgr = AudioManager()

    mock_mic_volume = MagicMock()
    mock_mic_volume.GetMute.return_value = 0

    with patch.object(mgr, "_get_mic_endpoint_volume", return_value=mock_mic_volume):
        mic_signals = []
        bus.mic_mute_changed.connect(lambda muted: mic_signals.append(muted))

        # 1. Проверка текущего mute (False)
        assert mgr.is_mic_muted() is False

        # 2. Установка mute True
        mgr.set_mic_mute(True)
        mock_mic_volume.SetMute.assert_called_with(1, None)
        assert mic_signals[-1] is True

        # 3. Переключение toggle_mic_mute (False -> True)
        mock_mic_volume.GetMute.return_value = 0
        new_state = mgr.toggle_mic_mute()
        assert new_state is True
        mock_mic_volume.SetMute.assert_called_with(1, None)
