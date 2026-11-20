"""
Интеграционные тесты для подсистемы DuckDeck и переключения аудиоустройств в DuckDock:
1. Инициализация MainWindow с DeckView на вкладке 2.
2. Проверка сайдбара (кнопка btn_deck, иконка, подсказка, переключение вкладок).
3. Синхронизация AudioMixerView при смене аудиоустройства через EventBus.
4. Маршрутизация системных действий колоды (диммер, микрофон, аудиовыход, блокировка).
5. Корректность очистки ресурсов (cleanup) при закрытии окна.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QApplication

from core.config import AppConfig, load_config
from core.event_bus import bus
from modules.audio.models import AudioDeviceInfo, AudioSessionInfo
from modules.audio.view import AudioMixerView
from modules.deck.action_dispatcher import ActionRunnable, DeckActionDispatcher, WorkerSignals
from modules.deck.models import DeckActionConfig
from modules.deck.view import DeckView
from ui.main_window import MainWindow


@pytest.mark.integration
def test_main_window_deck_view_tab_initialization(qapp):
    """
    Проверка интеграции DeckView в MainWindow:
    - На вкладке с индексом 2 расположен экземпляр DeckView.
    - В сайдбаре присутствует кнопка btn_deck с иконкой '🎛' и нужной подсказкой.
    - Переключение на вкладку 2 активирует страницу колоды и подсветку кнопки.
    - При закрытии окна вызывается cleanup() страницы колоды.
    """
    config = AppConfig()
    with patch("core.window_manager.WindowManager.find_window_by_process_name", return_value=None):
        win = MainWindow(config)

    try:
        # 1. Проверка наличия и типа страницы колоды
        assert hasattr(win, "page_deck")
        assert isinstance(win.page_deck, DeckView)
        assert win.workspace.widget(2) is win.page_deck
        assert win.workspace.count() >= 5

        # 2. Проверка кнопки сайдбара
        assert hasattr(win.sidebar, "btn_deck")
        assert win.sidebar.btn_deck.text() == "🎛"
        assert win.sidebar.btn_deck.toolTip() == "DuckDeck (Макро-панель и управление)"
        assert win.sidebar.btn_deck.focusPolicy() == Qt.NoFocus

        # 3. Переключение вкладок через EventBus
        bus.tab_changed.emit(2)
        assert win.workspace.currentIndex() == 2
        assert win.sidebar.btn_deck.property("active") == "true"

        # Переключение на другую вкладку
        bus.tab_changed.emit(0)
        assert win.workspace.currentIndex() == 0
        assert win.sidebar.btn_deck.property("active") == "false"

        # 4. Проверка вызова cleanup при закрытии
        with patch.object(win.page_deck, "cleanup", wraps=win.page_deck.cleanup) as mock_deck_cleanup, \
             patch.object(win.page_audio, "cleanup", wraps=win.page_audio.cleanup) as mock_audio_cleanup:
            win.close()
            assert mock_deck_cleanup.called, "cleanup() для DeckView должен быть вызван при закрытии окна"
            assert mock_audio_cleanup.called, "cleanup() для AudioMixerView должен быть вызван при закрытии окна"

    finally:
        win.close()


@pytest.mark.integration
def test_audio_view_device_switch_button_and_eventbus_sync(qapp):
    """
    Проверка сенсорной кнопки переключения аудиоустройства в AudioMixerView:
    - Кнопка btn_switch_device присутствует в header_layout шапки.
    - Эмиссия сигнала bus.playback_device_changed обновляет подпись кнопки, заголовок и сессии.
    - Клик по кнопке вызывает audio_manager.toggle_playback_device.
    """
    mock_audio_mgr = MagicMock()
    mock_audio_mgr.get_master_device_name.return_value = "Динамики Realtek"
    mock_audio_mgr.get_master_volume.return_value = 0.8
    mock_audio_mgr.is_master_muted.return_value = False
    mock_audio_mgr.get_sessions.return_value = []

    with patch("modules.audio.view.AudioManager", return_value=mock_audio_mgr):
        view = AudioMixerView()
        try:
            # 1. Проверка наличия кнопки и ее базовых свойств
            assert hasattr(view, "btn_switch_device")
            assert view.btn_switch_device.height() == 40
            assert view.btn_switch_device.minimumWidth() >= 140
            assert view.btn_switch_device.focusPolicy() == Qt.NoFocus
            assert "🔊 Динамики Realtek" in view.btn_switch_device.text()

            # 2. Эмуляция переключения на наушники через EventBus
            with patch.object(view, "_refresh_master") as mock_ref_master, \
                 patch.object(view, "_refresh_sessions") as mock_ref_sess:
                bus.playback_device_changed.emit("Наушники HyperX Cloud", "{guid-headphones}")
                assert view.lbl_device.text() == "Наушники HyperX Cloud"
                assert "🎧 Наушники HyperX Cloud" in view.btn_switch_device.text()
                mock_ref_master.assert_called_once()
                mock_ref_sess.assert_called_once_with(force_rebuild=True)

            # 3. Эмуляция переключения обратно на колонки
            bus.playback_device_changed.emit("Динамики USB Audio", "{guid-speakers}")
            assert view.lbl_device.text() == "Динамики USB Audio"
            assert "🔊 Динамики USB Audio" in view.btn_switch_device.text()

            # 4. Проверка клика по кнопке btn_switch_device
            view.btn_switch_device.click()
            mock_audio_mgr.toggle_playback_device.assert_called_with(["Наушники", "Динамики"])

        finally:
            view.cleanup()
            view.close()


@pytest.mark.integration
def test_deck_system_actions_routing_integration(qapp):
    """
    Проверка маршрутизации системных действий DuckDeck через диспетчер:
    - toggle_dimmer -> bus.dimmer_toggle_requested
    - toggle_mic_mute -> AudioManager.toggle_mic_mute
    - toggle_playback_device (system) -> AudioManager.toggle_playback_device
    - lock_workstation -> ctypes.windll.user32.LockWorkStation
    - audio_device (audio_device) -> AudioManager.toggle_playback_device
    """
    mock_audio_mgr = MagicMock()
    mock_audio_mgr.toggle_mic_mute.return_value = True
    fake_dev = AudioDeviceInfo(id="{guid}", name="Наушники Test", is_default=True, state=1)
    mock_audio_mgr.toggle_playback_device.return_value = fake_dev

    # 1. toggle_dimmer
    dimmer_emitted = []
    bus.dimmer_toggle_requested.connect(lambda: dimmer_emitted.append(True))
    signals1 = WorkerSignals()
    results1 = []
    signals1.finished.connect(lambda b_id, ok, msg: results1.append((b_id, ok, msg)))

    act_dimmer = DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"})
    runnable1 = ActionRunnable("btn_dim", act_dimmer, signals1, audio_manager=mock_audio_mgr)
    runnable1.run()

    assert len(dimmer_emitted) == 1
    assert len(results1) == 1
    assert results1[0][1] is True

    # 2. toggle_mic_mute
    signals2 = WorkerSignals()
    results2 = []
    signals2.finished.connect(lambda b_id, ok, msg: results2.append((b_id, ok, msg)))

    act_mic = DeckActionConfig(action_type="system", params={"command": "toggle_mic_mute"})
    runnable2 = ActionRunnable("btn_mic", act_mic, signals2, audio_manager=mock_audio_mgr)
    runnable2.run()

    mock_audio_mgr.toggle_mic_mute.assert_called_once()
    assert len(results2) == 1
    assert results2[0][1] is True

    # 3. toggle_playback_device (command in system)
    signals3 = WorkerSignals()
    results3 = []
    signals3.finished.connect(lambda b_id, ok, msg: results3.append((b_id, ok, msg)))

    act_audio_sys = DeckActionConfig(action_type="system", params={"command": "toggle_playback_device"})
    runnable3 = ActionRunnable("btn_audio_sys", act_audio_sys, signals3, audio_manager=mock_audio_mgr)
    runnable3.run()

    mock_audio_mgr.toggle_playback_device.assert_called()
    assert len(results3) == 1
    assert results3[0][1] is True

    # 4. lock_workstation
    with patch("ctypes.windll.user32.LockWorkStation", return_value=1) as mock_lock:
        signals4 = WorkerSignals()
        results4 = []
        signals4.finished.connect(lambda b_id, ok, msg: results4.append((b_id, ok, msg)))

        act_lock = DeckActionConfig(action_type="system", params={"command": "lock_workstation"})
        runnable4 = ActionRunnable("btn_lock", act_lock, signals4, audio_manager=mock_audio_mgr)
        runnable4.run()

        mock_lock.assert_called_once()
        assert len(results4) == 1
        assert results4[0][1] is True

    # 5. audio_device action type
    signals5 = WorkerSignals()
    results5 = []
    signals5.finished.connect(lambda b_id, ok, msg: results5.append((b_id, ok, msg)))

    act_audio = DeckActionConfig(
        action_type="audio_device",
        params={"mode": "toggle", "devices": ["Наушники", "Динамики"]}
    )
    runnable5 = ActionRunnable("btn_audio", act_audio, signals5, audio_manager=mock_audio_mgr)
    runnable5.run()

    mock_audio_mgr.toggle_playback_device.assert_called_with(["Наушники", "Динамики"])
    assert len(results5) == 1
    assert results5[0][1] is True


@pytest.mark.integration
def test_config_json_tracked_apps_happ_removed():
    """
    Проверка, что сторонний процесс happ удален из tracked_apps в config.json,
    исключая паразитные попытки тайлинга на вкладке 2.
    """
    config_file = Path("config.json")
    assert config_file.exists(), "config.json должен существовать в корне проекта"

    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    tracked = data.get("tracked_apps", [])
    tracked_names = [app.get("name") for app in tracked]
    tracked_procs = [app.get("process_name") for app in tracked]

    assert "happ" not in tracked_names, "happ не должен присутствовать в tracked_apps"
    assert "happ.exe" not in tracked_procs, "happ.exe не должен присутствовать в tracked_apps"

    cfg = load_config(config_file)
    for app in cfg.tracked_apps:
        assert app.name != "happ"
        assert app.process_name != "happ.exe"


@pytest.mark.integration
def test_duckdock_spec_configuration():
    """
    Проверка спецификации сборки DuckDock.spec:
    - В datas включены ресурсы DuckDeck: 'resources/deck' и 'config/deck_config.json'.
    - В hiddenimports включен модуль 'PySide6.QtMultimedia'.
    """
    spec_path = Path("DuckDock.spec")
    assert spec_path.exists(), "DuckDock.spec должен существовать в корне проекта"

    content = spec_path.read_text(encoding="utf-8")
    assert "resources/deck" in content, "DuckDock.spec должен содержать resources/deck в datas"
    assert "config/deck_config.json" in content, "DuckDock.spec должен содержать config/deck_config.json в datas"
    assert "PySide6.QtMultimedia" in content, "DuckDock.spec должен содержать PySide6.QtMultimedia в hiddenimports"

