"""
Тесты для модуля core.audio_manager (Windows Core Audio API & PyCaw Facade).
"""
import pytest
from unittest.mock import MagicMock, patch
from core.audio_manager import AudioManager, AudioSessionInfo, APP_FRIENDLY_NAMES


@pytest.mark.unit
def test_audio_session_info_validation():
    """Проверка валидации Pydantic модели AudioSessionInfo."""
    info = AudioSessionInfo(
        pid=1234,
        name="Discord",
        process_name="discord.exe",
        exe_path=r"C:\Users\test\AppData\Local\Discord\app.exe",
        volume=0.75,
        is_muted=False,
        is_active=True,
    )
    assert info.pid == 1234
    assert info.name == "Discord"
    assert info.volume == 0.75
    assert not info.is_muted
    assert info.is_active

    # Тест дефолтных значений
    default_info = AudioSessionInfo()
    assert default_info.pid is None
    assert default_info.name == "Unknown"
    assert default_info.volume == 1.0
    assert not default_info.is_muted


@pytest.mark.unit
def test_audio_manager_master_volume():
    """Тест чтения и записи Master Volume с проверкой ограничения диапазона (0.0 - 1.0)."""
    mgr = AudioManager()

    mock_ep = MagicMock()
    mock_ep.GetMasterVolumeLevelScalar.return_value = 0.65
    mock_ep.GetMute.return_value = 0

    with patch.object(mgr, "_get_endpoint_volume", return_value=mock_ep):
        # 1. Чтение громкости
        vol = mgr.get_master_volume()
        assert vol == 0.65

        # 2. Установка громкости (в пределах 0.0 - 1.0)
        mgr.set_master_volume(0.8)
        mock_ep.SetMasterVolumeLevelScalar.assert_called_with(0.8, None)

        # 3. Клампинг выше 1.0
        mgr.set_master_volume(1.5)
        mock_ep.SetMasterVolumeLevelScalar.assert_called_with(1.0, None)

        # 4. Клампинг ниже 0.0
        mgr.set_master_volume(-0.3)
        mock_ep.SetMasterVolumeLevelScalar.assert_called_with(0.0, None)


@pytest.mark.unit
def test_audio_manager_master_mute():
    """Тест чтения, установки и переключения Master Mute."""
    mgr = AudioManager()

    mock_ep = MagicMock()
    mock_ep.GetMute.return_value = 0

    with patch.object(mgr, "_get_endpoint_volume", return_value=mock_ep):
        # Проверка начального состояния
        assert not mgr.is_master_muted()

        # Установка Mute = True
        mgr.set_master_mute(True)
        mock_ep.SetMute.assert_called_with(1, None)

        # Toggle Mute (было False -> станет True)
        mock_ep.GetMute.return_value = 0
        new_state = mgr.toggle_master_mute()
        assert new_state is True
        mock_ep.SetMute.assert_called_with(1, None)

        # Toggle Mute (было True -> станет False)
        mock_ep.GetMute.return_value = 1
        new_state = mgr.toggle_master_mute()
        assert new_state is False
        mock_ep.SetMute.assert_called_with(0, None)


@pytest.mark.unit
def test_audio_manager_format_app_name():
    """Тест форматирования понятных имен приложений."""
    mgr = AudioManager()

    assert mgr._format_app_name("chrome.exe", 100) == "Google Chrome"
    assert mgr._format_app_name("discord.exe", 200) == "Discord"
    assert mgr._format_app_name("browser.exe", 300) == "Yandex Browser"
    assert mgr._format_app_name("custom_game.exe", 400) == "custom_game"
    assert mgr._format_app_name("", 0) == "Системные звуки"
    assert mgr._format_app_name("System", None) == "Системные звуки"


@pytest.mark.unit
def test_audio_manager_get_sessions_mocked():
    """Тест сканирования сессий, группировки по PID и фильтрации expired."""
    mgr = AudioManager()

    # Сессия 1: Discord (PID 100, Active)
    s1 = MagicMock()
    s1.State = 1
    s1.Process = MagicMock()
    s1.Process.pid = 100
    s1.Process.name.return_value = "discord.exe"
    s1.SimpleAudioVolume.GetMasterVolume.return_value = 0.8
    s1.SimpleAudioVolume.GetMute.return_value = 0

    # Сессия 2: Вторая сессия того же Discord (PID 100)
    s2 = MagicMock()
    s2.State = 1
    s2.Process = MagicMock()
    s2.Process.pid = 100
    s2.Process.name.return_value = "discord.exe"
    s2.SimpleAudioVolume.GetMasterVolume.return_value = 0.9
    s2.SimpleAudioVolume.GetMute.return_value = 0

    # Сессия 3: Устаревшая сессия (State = 2, Expired)
    s3 = MagicMock()
    s3.State = 2
    s3.Process = MagicMock()
    s3.Process.pid = 200

    # Сессия 4: Системные звуки (Process = None)
    s4 = MagicMock()
    s4.State = 0
    s4.Process = None
    s4.SimpleAudioVolume.GetMasterVolume.return_value = 0.5
    s4.SimpleAudioVolume.GetMute.return_value = 1

    with patch("core.audio_manager.AudioUtilities.GetAllSessions", return_value=[s1, s2, s3, s4]), \
         patch.object(mgr, "_resolve_process_exe", return_value=r"C:\Apps\discord.exe"):

        sessions = mgr.get_sessions()

        # Должно быть 2 сессии (Discord с максимальной громкостью 0.9 и Системные звуки)
        assert len(sessions) == 2

        discord_sess = next((s for s in sessions if s.pid == 100), None)
        assert discord_sess is not None
        assert discord_sess.name == "Discord"
        assert discord_sess.volume == 0.9
        assert not discord_sess.is_muted
        assert discord_sess.is_active

        sys_sess = next((s for s in sessions if s.pid == 0), None)
        assert sys_sess is not None
        assert sys_sess.name == "Системные звуки"
        assert sys_sess.volume == 0.5
        assert sys_sess.is_muted


@pytest.mark.unit
def test_audio_manager_set_session_volume_and_mute():
    """Тест установки уровня громкости и отключения звука конкретного PID."""
    mgr = AudioManager()

    s1 = MagicMock()
    s1.Process = MagicMock()
    s1.Process.pid = 500
    s1.SimpleAudioVolume = MagicMock()
    s1.SimpleAudioVolume.GetMute.return_value = 0

    s2 = MagicMock()
    s2.Process = MagicMock()
    s2.Process.pid = 600
    s2.SimpleAudioVolume = MagicMock()

    with patch("core.audio_manager.AudioUtilities.GetAllSessions", return_value=[s1, s2]):
        # Установка громкости PID 500
        mgr.set_session_volume(500, 0.45)
        s1.SimpleAudioVolume.SetMasterVolume.assert_called_with(0.45, None)
        s2.SimpleAudioVolume.SetMasterVolume.assert_not_called()

        # Переключение Mute для PID 500
        new_mute = mgr.toggle_session_mute(500)
        assert new_mute is True
        s1.SimpleAudioVolume.SetMute.assert_called_with(1, None)
