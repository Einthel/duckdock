"""
Тестирование графического интерфейса сенсорного аудиомикшера (ui.modules.audio_view).
"""
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QPointingDevice
from PySide6.QtWidgets import QApplication

from core.audio_manager import AudioSessionInfo
from ui.modules.audio_view import TouchSlider, SessionCardWidget, AudioMixerView
from ui.main_window import MainWindow
from core.config import AppConfig


@pytest.mark.unit
def test_touch_slider_stealth_focus_and_jump(qapp):
    """
    Проверка инвариантов TouchSlider:
    1. Qt.NoFocus для предотвращения перехвата фокуса у полноэкранных игр.
    2. Мгновенный прыжок значения (Jump-to-touch) при клике в любую точку трека.
    """
    slider = TouchSlider(Qt.Horizontal)
    slider.resize(200, 40)
    slider.setRange(0, 100)
    slider.setValue(10)

    # 1. Проверка политики фокуса
    assert slider.focusPolicy() == Qt.NoFocus

    # 2. Эмуляция тача в середину слайдера (x = 100 при width = 200 -> ~50%)
    dev = QPointingDevice.primaryPointingDevice()
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(100, 20),
        QPointF(100, 20),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        dev,
    )
    slider.mousePressEvent(ev)
    assert 45 <= slider.value() <= 55


@pytest.mark.unit
def test_session_card_widget(qapp):
    """Проверка создания и обновления карточки сессии приложения."""
    session = AudioSessionInfo(
        pid=999,
        name="Telegram",
        process_name="telegram.exe",
        volume=0.6,
        is_muted=False,
    )
    mock_icon_provider = MagicMock()
    mock_icon_provider.icon.return_value = MagicMock(isNull=lambda: True)

    card = SessionCardWidget(session, mock_icon_provider)

    assert card.pid == 999
    assert card.lbl_name.text() == "Telegram"
    assert card.slider.value() == 60
    assert card.lbl_vol.text() == "60%"
    assert card.btn_mute.text() == "🔊"
    assert card.btn_mute.focusPolicy() == Qt.NoFocus
    assert card.slider.focusPolicy() == Qt.NoFocus

    # Обновление состояния (например, mute включен, громкость 80%)
    session_updated = AudioSessionInfo(
        pid=999,
        name="Telegram",
        process_name="telegram.exe",
        volume=0.8,
        is_muted=True,
    )
    card.update_state(session_updated)
    assert card.slider.value() == 80
    assert card.lbl_vol.text() == "80%"
    assert card.btn_mute.text() == "🔇"
    assert card.btn_mute.property("muted") == "true"


@pytest.mark.unit
def test_audio_mixer_view_integration(qapp):
    """Тест работы AudioMixerView: мастер-громкость, сессии и таймер."""
    mock_sessions = [
        AudioSessionInfo(pid=101, name="Game", process_name="game.exe", volume=0.5, is_muted=False),
        AudioSessionInfo(pid=102, name="Discord", process_name="discord.exe", volume=0.7, is_muted=True),
    ]

    with patch("core.audio_manager.AudioManager.get_master_volume", return_value=0.75), \
         patch("core.audio_manager.AudioManager.is_master_muted", return_value=False), \
         patch("core.audio_manager.AudioManager.get_sessions", return_value=mock_sessions), \
         patch("core.audio_manager.AudioManager.set_master_volume") as mock_set_master_vol, \
         patch("core.audio_manager.AudioManager.toggle_master_mute", return_value=True) as mock_toggle_mute:

        view = AudioMixerView()
        assert view is not None
        assert view.poll_timer.isActive()

        # Проверка мастер-громкости
        assert view.master_slider.value() == 75
        assert view.lbl_master_vol.text() == "75%"
        assert view.btn_master_mute.text() == "🔊 ЗВУК"

        # Проверка списка сессий
        assert len(view._session_cards) == 2
        assert 101 in view._session_cards
        assert 102 in view._session_cards

        # Проверка изменения мастер-громкости слайдером
        view.master_slider.setValue(90)
        mock_set_master_vol.assert_called_with(0.9)

        # Проверка нажатия Mute
        view.btn_master_mute.click()
        mock_toggle_mute.assert_called_once()
        assert view.btn_master_mute.text() == "🔇 MUTE"

        view.poll_timer.stop()


@pytest.mark.unit
def test_main_window_has_audio_mixer_tab(qapp):
    """Проверка, что вкладка 3 главного окна содержит AudioMixerView."""
    config = AppConfig()
    win = MainWindow(config)

    # Проверяем, что на индексе 3 находится AudioMixerView
    audio_tab = win.workspace.widget(3)
    assert isinstance(audio_tab, AudioMixerView)
    assert hasattr(win, "page_audio")
    assert win.page_audio is audio_tab

    win.close()
