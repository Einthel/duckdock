"""
Тестирование графического интерфейса сенсорного аудиомикшера (modules.audio.view).
"""
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QPointingDevice
from PySide6.QtWidgets import QApplication, QFileIconProvider

from core.config import AppConfig
from core.event_bus import bus
from core.i18n import I18nManager, tp
from modules.audio.models import AudioSessionInfo
from modules.audio.view import AudioMixerView, SessionCardWidget, TouchSlider
from ui.main_window import MainWindow


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
    with patch("core.window_manager.WindowManager.find_window_by_process_name", return_value=None):
        win = MainWindow(config)

    # Проверяем, что на индексе 3 находится AudioMixerView
    audio_tab = win.workspace.widget(3)
    assert isinstance(audio_tab, AudioMixerView)
    assert hasattr(win, "page_audio")
    assert win.page_audio is audio_tab

    win.close()


@pytest.mark.unit
def test_audio_sessions_pluralization():
    """Валидация плюральных форм числа аудиосессий (RU и EN)."""
    mgr = I18nManager()
    try:
        # RU
        mgr.set_language("ru", emit_signal=False)
        assert tp("audio.sessions.count", count=1) == "1 активный процесс"
        assert tp("audio.sessions.count", count=2) == "2 активных процесса"
        assert tp("audio.sessions.count", count=4) == "4 активных процесса"
        assert tp("audio.sessions.count", count=5) == "5 активных процессов"
        assert tp("audio.sessions.count", count=11) == "11 активных процессов"
        assert tp("audio.sessions.count", count=21) == "21 активный процесс"
        assert tp("audio.sessions.count", count=24) == "24 активных процесса"

        # EN
        mgr.set_language("en", emit_signal=False)
        assert tp("audio.sessions.count", count=1) == "1 active process"
        assert tp("audio.sessions.count", count=2) == "2 active processes"
        assert tp("audio.sessions.count", count=5) == "5 active processes"
        assert tp("audio.sessions.count", count=21) == "21 active processes"
    finally:
        mgr.set_language("ru", emit_signal=False)


@pytest.mark.unit
def test_session_card_retranslate_ui(qapp):
    """Проверка локализации карточки системных звуков (pid=0)."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)

    session = AudioSessionInfo(
        pid=0,
        name="System",
        process_name="System",
        volume=0.8,
        is_muted=False,
    )
    icon_provider = QFileIconProvider()
    card = SessionCardWidget(session, icon_provider)

    try:
        assert card.lbl_sub.text() == "Системные звуки"

        # Переключение на английский
        mgr.set_language("en")
        card.retranslate_ui()
        assert card.lbl_sub.text() == "System Sounds"

        # Переключение обратно на русский
        mgr.set_language("ru")
        card.retranslate_ui()
        assert card.lbl_sub.text() == "Системные звуки"
    finally:
        mgr.set_language("ru", emit_signal=False)


@pytest.mark.unit
def test_audio_view_retranslate_ui(qapp):
    """Проверка динамического обновления текстов AudioMixerView без сброса слайдера."""
    mgr = I18nManager()
    mgr.set_language("ru", emit_signal=False)

    with patch("modules.audio.view.AudioManager") as MockManager:
        mock_instance = MockManager.return_value
        mock_instance.get_master_volume.return_value = 0.75
        mock_instance.is_master_muted.return_value = False
        mock_instance.get_master_device_name.return_value = "Наушники Realtek"
        mock_instance.get_sessions.return_value = [
            AudioSessionInfo(pid=0, name="System", process_name="System", volume=0.5, is_muted=False),
            AudioSessionInfo(pid=1234, name="Game", process_name="game.exe", volume=0.8, is_muted=False),
        ]

        view = AudioMixerView()
        try:
            assert view.lbl_title.text() == "WINDOWS CORE AUDIO MIXER"
            assert "ОБЩАЯ ГРОМКОСТЬ" in view.lbl_m_title.text()
            assert "ПРИЛОЖЕНИЯ И ПРОЦЕССЫ" in view.lbl_apps.text()
            assert "ЗВУК" in view.btn_master_mute.text()
            assert view.master_slider.value() == 75

            # Горячая смена языка на английский
            mgr.set_language("en")
            # TouchModuleView автоматически вызывает retranslate_ui()
            assert view.lbl_title.text() == "WINDOWS CORE AUDIO MIXER"
            assert "MASTER VOLUME" in view.lbl_m_title.text()
            assert "APPLICATIONS & PROCESSES" in view.lbl_apps.text()
            assert "AUDIO" in view.btn_master_mute.text()
            assert view.master_slider.value() == 75

            # Переключение обратно на русский
            mgr.set_language("ru")
            assert "ОБЩАЯ ГРОМКОСТЬ" in view.lbl_m_title.text()
            assert "ПРИЛОЖЕНИЯ И ПРОЦЕССЫ" in view.lbl_apps.text()
            assert "ЗВУК" in view.btn_master_mute.text()
            assert view.master_slider.value() == 75
        finally:
            mgr.set_language("ru", emit_signal=False)
            view.cleanup()
            view.deleteLater()
