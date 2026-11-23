"""
Модульные тесты для подсистемы DuckDeck (модели, хоткеи, запуск процессов,
HTTP-запросы, скриншоты и диспетчер I/O с изоляцией WinAPI).
"""
import json
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from modules.deck.action_dispatcher import ActionRunnable, DeckActionDispatcher, WorkerSignals
from modules.deck.actions.hotkey_sender import (
    EXTENDED_KEYS,
    KEYEVENTF_EXTENDEDKEY,
    KEYEVENTF_KEYUP,
    KEYEVENTF_SCANCODE,
    VK_MAPPING,
    resolve_vk,
    send_hotkey,
)
from modules.deck.actions.http_client import execute_http_request
from modules.deck.actions.process_launcher import CREATE_NO_WINDOW, DETACHED_PROCESS, launch_process
from modules.deck.actions.screen_capture import capture_screen, copy_pixmap_to_clipboard, get_primary_screen
from modules.deck.models import (
    ActionCategory,
    AudioDeviceParams,
    DeckActionConfig,
    DeckButtonConfig,
    DeckConfigLoader,
    DeckPageConfig,
    DeckRootConfig,
    HotkeyParams,
    HttpRequestParams,
    LaunchParams,
    NavigationParams,
    ScreenshotParams,
    SoundSettings,
    SystemParams,
)
from core.focus_guardian import FocusGuardian


# -------------------------------------------------------------
# 1. Тесты Pydantic v2 моделей и схем параметров
# -------------------------------------------------------------
def test_deck_action_typed_params_factory():
    """Проверка фабрики типизированных параметров DeckActionConfig.get_typed_params()."""
    # Hotkey
    act_hk = DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "f9"]})
    typed_hk = act_hk.get_typed_params()
    assert isinstance(typed_hk, HotkeyParams)
    assert typed_hk.keys == ["ctrl", "f9"]

    # Audio Device
    act_audio = DeckActionConfig(
        action_type="audio_device",
        params={"mode": "cycle", "devices": ["Headphones", "Speakers"]},
    )
    typed_audio = act_audio.get_typed_params()
    assert isinstance(typed_audio, AudioDeviceParams)
    assert typed_audio.mode == "cycle"
    assert typed_audio.devices == ["Headphones", "Speakers"]

    # Launch
    act_launch = DeckActionConfig(
        action_type="launch",
        params={"path": "notepad.exe", "args": ["file.txt"], "detached": True},
    )
    typed_launch = act_launch.get_typed_params()
    assert isinstance(typed_launch, LaunchParams)
    assert typed_launch.path == "notepad.exe"
    assert typed_launch.args == ["file.txt"]
    assert typed_launch.detached is True

    # Http Request
    act_http = DeckActionConfig(
        action_type="http_request",
        params={"url": "http://127.0.0.1:8000/api", "method": "GET", "timeout_sec": 2.0},
    )
    typed_http = act_http.get_typed_params()
    assert isinstance(typed_http, HttpRequestParams)
    assert typed_http.url == "http://127.0.0.1:8000/api"
    assert typed_http.timeout_sec == 2.0

    # Screenshot
    act_shot = DeckActionConfig(
        action_type="screenshot",
        params={"target": "primary_screen", "clipboard": True},
    )
    typed_shot = act_shot.get_typed_params()
    assert isinstance(typed_shot, ScreenshotParams)
    assert typed_shot.target == "primary_screen"
    assert typed_shot.clipboard is True

    # System
    act_sys = DeckActionConfig(
        action_type="system",
        params={"command": "toggle_mic_mute"},
    )
    typed_sys = act_sys.get_typed_params()
    assert isinstance(typed_sys, SystemParams)
    assert typed_sys.command == "toggle_mic_mute"

    # Navigation
    act_nav = DeckActionConfig(
        action_type="navigation",
        params={"target_page_id": "gaming_page"},
    )
    typed_nav = act_nav.get_typed_params()
    assert isinstance(typed_nav, NavigationParams)
    assert typed_nav.target_page_id == "gaming_page"


def test_deck_root_config_serialization():
    """Тест сериализации и десериализации дерева конфигурации DeckRootConfig."""
    btn = DeckButtonConfig(
        id="btn_1",
        title="Тест",
        icon="🚀",
        action=DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"}),
    )
    page = DeckPageConfig(
        id="main_page",
        name="Главная",
        grid_rows=3,
        grid_cols=5,
        buttons=[btn],
    )
    root = DeckRootConfig(active_profile="main_page", pages=[page])

    json_str = root.model_dump_json()
    data = json.loads(json_str)
    assert data["active_profile"] == "main_page"
    assert len(data["pages"]) == 1
    assert data["pages"][0]["buttons"][0]["id"] == "btn_1"

    restored = DeckRootConfig.model_validate_json(json_str)
    assert restored.active_profile == "main_page"
    assert restored.pages[0].buttons[0].title == "Тест"


def test_deck_config_loader():
    """Тест безопасного загрузчика DuckDeck с fallback на дефолтный профиль."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = os.path.join(tmp_dir, "deck_test.json")

        # 1. Несуществующий файл -> создание дефолтной конфигурации
        loaded = DeckConfigLoader.load_from_file(config_path)
        assert isinstance(loaded, DeckRootConfig)
        assert loaded.active_profile == "default"
        assert len(loaded.pages) > 0
        assert os.path.isfile(config_path)

        # 2. Чтение валидного сохраненного файла
        loaded.active_profile = "custom_profile"
        DeckConfigLoader.save_to_file(loaded, config_path)
        reloaded = DeckConfigLoader.load_from_file(config_path)
        assert reloaded.active_profile == "custom_profile"

        # 3. Поврежденный файл -> fallback без исключений
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON DATA")

        fallback = DeckConfigLoader.load_from_file(config_path)
        assert isinstance(fallback, DeckRootConfig)
        assert fallback.active_profile == "default"


# -------------------------------------------------------------
# 2. Тесты модуля hotkey_sender.py
# -------------------------------------------------------------
def test_resolve_vk():
    """Тест сопоставления строковых клавиш в виртуальные коды VK."""
    assert resolve_vk("ctrl") == 0x11
    assert resolve_vk("Ctrl") == 0x11
    assert resolve_vk("alt") == 0x12
    assert resolve_vk("shift") == 0x10
    assert resolve_vk("win") == 0x5B
    assert resolve_vk("f9") == 0x78
    assert resolve_vk("f13") == 0x7C
    assert resolve_vk("enter") == 0x0D
    assert resolve_vk("esc") == 0x1B
    assert resolve_vk("up") == 0x26
    assert resolve_vk("volup") == 0xAF
    assert resolve_vk("a") == 0x41
    assert resolve_vk("9") == 0x39
    assert resolve_vk("nonexistent_key_xyz") is None


@patch("core.deck.actions.hotkey_sender._send_key_event")
@patch("core.deck.actions.hotkey_sender.time.sleep")
def test_send_hotkey_lifo_and_scancodes(mock_sleep, mock_send_key):
    """
    Тест отправки хоткея: прямой порядок нажатия, LIFO отпускание
    и гарантированная очистка модификаторов.
    """
    # ctrl (0x11) + shift (0x10) + d (0x44)
    res = send_hotkey(["ctrl", "shift", "d"], restore_focus=False)
    assert res is True

    calls = mock_send_key.call_args_list
    assert len(calls) >= 6

    # Первые 3 вызова — Down в прямом порядке
    assert calls[0][0][1] == 0x11 and calls[0][1].get("is_up") is False
    assert calls[1][0][1] == 0x10 and calls[1][1].get("is_up") is False
    assert calls[2][0][1] == 0x44 and calls[2][1].get("is_up") is False

    # Следующие 3 вызова — Up в обратном LIFO порядке
    assert calls[3][0][1] == 0x44 and calls[3][1].get("is_up") is True
    assert calls[4][0][1] == 0x10 and calls[4][1].get("is_up") is True
    assert calls[5][0][1] == 0x11 and calls[5][1].get("is_up") is True


def test_send_key_event_internals():
    """Тест вызова WinAPI MapVirtualKeyW и SendInput внутри _send_key_event."""
    from modules.deck.actions.hotkey_sender import _send_key_event
    user32_mock = MagicMock()
    user32_mock.MapVirtualKeyW.return_value = 72

    # UP стрелка — расширенная клавиша
    _send_key_event(user32_mock, 0x26, is_up=True)
    user32_mock.MapVirtualKeyW.assert_called_once_with(0x26, 0)
    user32_mock.SendInput.assert_called_once()
    assert user32_mock.SendInput.call_args[0][0] == 1


@patch("modules.deck.actions.hotkey_sender.win32gui")
@patch("modules.deck.actions.hotkey_sender.FocusGuardian")
@patch("core.deck.actions.hotkey_sender.time.sleep")
@patch("core.deck.actions.hotkey_sender._send_key_event")
def test_send_hotkey_focus_restoration(mock_send_key, mock_sleep, mock_fg_cls, mock_gui):
    """Тест проверки и возврата фокуса в основное окно перед отправкой SendInput."""
    fg_mock = MagicMock()
    fg_mock.last_primary_hwnd = 12345
    fg_mock.is_subscreen_window.return_value = True
    mock_fg_cls.get_instance.return_value = fg_mock

    mock_gui.GetForegroundWindow.return_value = 99999  # текущее окно — DuckDock на 2-м экране

    send_hotkey(["enter"], restore_focus=True, focus_delay_sec=0.02)

    # Должен быть вызван restore_focus_to_primary
    fg_mock.restore_focus_to_primary.assert_called_once_with(delay=False)


# -------------------------------------------------------------
# 3. Тесты process_launcher.py
# -------------------------------------------------------------
@patch("subprocess.Popen")
def test_launch_process_executable(mock_popen):
    """Тест запуска бинарного процесса с флагами detachment и переменными окружения."""
    with patch.dict(os.environ, {"MY_TEST_APP": "test_app.exe"}):
        success, msg = launch_process("%MY_TEST_APP%", args=["--arg1", "val"], detached=True)
        assert success is True
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd == ["test_app.exe", "--arg1", "val"]
        kwargs = mock_popen.call_args[1]
        assert kwargs["creationflags"] == (CREATE_NO_WINDOW | DETACHED_PROCESS)


@patch("os.startfile")
def test_launch_process_url_protocol(mock_startfile):
    """Тест открытия URL и протоколов через os.startfile."""
    success, msg = launch_process("discord://channels/123/456")
    assert success is True
    mock_startfile.assert_called_once_with("discord://channels/123/456")


def test_launch_process_empty_path():
    """Тест обработки пустого пути запуска."""
    success, msg = launch_process("   ")
    assert success is False


# -------------------------------------------------------------
# 4. Тесты http_client.py
# -------------------------------------------------------------
@patch("urllib.request.urlopen")
def test_execute_http_request_success(mock_urlopen):
    """Тест успешного HTTP POST запроса с JSON телом."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"status": "ok"}'
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    success, status, text = execute_http_request(
        url="http://127.0.0.1:6742/api/profiles/load",
        method="POST",
        json_body={"profile": "RedAlert"},
        timeout_sec=1.5,
    )

    assert success is True
    assert status == 200
    assert text == '{"status": "ok"}'
    mock_urlopen.assert_called_once()
    req = mock_urlopen.call_args[0][0]
    assert req.method == "POST"
    assert req.headers["Content-type"] == "application/json"


@patch("urllib.request.urlopen")
def test_execute_http_request_timeout(mock_urlopen):
    """Тест корректного перехвата таймаута сети без падения."""
    mock_urlopen.side_effect = TimeoutError("Connection timed out")

    success, status, text = execute_http_request("http://192.168.1.200/api")
    assert success is False
    assert status == 0
    assert "Сетевая ошибка" in text


# -------------------------------------------------------------
# 5. Тесты screen_capture.py
# -------------------------------------------------------------
@patch("core.deck.actions.screen_capture.copy_pixmap_to_clipboard")
@patch("core.deck.actions.screen_capture.get_primary_screen")
def test_capture_screen_primary(mock_get_screen, mock_copy, qapp):
    """Тест захвата первичного экрана и отправки в буфер обмена."""
    mock_screen = MagicMock()
    fake_pixmap = QPixmap(100, 100)
    mock_screen.grabWindow.return_value = fake_pixmap
    mock_get_screen.return_value = mock_screen

    success, msg = capture_screen(target="primary_screen", clipboard=True)
    assert success is True
    mock_screen.grabWindow.assert_called_once_with(0)
    mock_copy.assert_called_once_with(fake_pixmap)


def test_clipboard_helper_cross_thread_dispatch(qapp):
    """Тест безопасной передачи QPixmap в буфер обмена из фонового потока на GUI-поток."""
    import threading
    from PySide6.QtCore import QThread
    from modules.deck.actions.screen_capture import ClipboardHelper, copy_pixmap_to_clipboard

    slot_thread = []

    def mock_on_copy(pixmap):
        slot_thread.append(QThread.currentThread())

    helper = ClipboardHelper.get_instance()
    helper._on_copy_pixmap = mock_on_copy

    # Вызов из фонового потока
    fake_pixmap = QPixmap(32, 32)
    worker = threading.Thread(target=lambda: copy_pixmap_to_clipboard(fake_pixmap))
    worker.start()
    worker.join()

    # Обработка очереди событий GUI потока
    qapp.processEvents()

    assert len(slot_thread) == 1
    assert slot_thread[0] == qapp.thread(), "Слот _on_copy_pixmap обязан выполняться в главном потоке GUI"


# -------------------------------------------------------------
# 6. Тесты action_dispatcher.py (антидребезг и потокобезопасность)
# -------------------------------------------------------------
def test_action_dispatcher_debounce(qapp):
    """Тест аппаратного/программного антидребезга (cooldown 250 мс)."""
    pool = QThreadPool()
    dispatcher = DeckActionDispatcher(debounce_ms=250, thread_pool=pool)

    act = DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "c"]})

    # Первое нажатие принимается
    res1 = dispatcher.dispatch("btn_copy", act)
    assert res1 is True

    # Мгновенное второе нажатие отклоняется из-за антидребезга
    res2 = dispatcher.dispatch("btn_copy", act)
    assert res2 is False

    # Другая кнопка принимается независимо
    res3 = dispatcher.dispatch("btn_paste", act)
    assert res3 is True


def test_action_runnable_routing_system_dimmer(qapp):
    """Тест маршрутизации действия system toggle_dimmer через ActionRunnable."""
    from core.event_bus import bus

    signals = WorkerSignals()
    results = []
    signals.finished.connect(lambda b_id, ok, msg: results.append((b_id, ok, msg)))

    dimmer_signals = []
    bus.dimmer_toggle_requested.connect(lambda: dimmer_signals.append(True))

    act = DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"})

    runnable = ActionRunnable("btn_dim", act, signals)
    runnable.run()

    assert len(dimmer_signals) == 1
    assert len(results) == 1
    assert results[0][0] == "btn_dim"
    assert results[0][1] is True


def test_action_dispatcher_gc_protection_and_cleanup(qapp):
    """Тест сохранения сильной ссылки на задачи в пуле потоков во время сборки мусора (GC)."""
    import gc
    dispatcher = DeckActionDispatcher(debounce_ms=50)

    received_finished = []
    dispatcher.action_finished.connect(lambda bid, ok, msg: received_finished.append((bid, ok, msg)))

    act = DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"})
    accepted = dispatcher.dispatch("btn_test_gc", act)
    assert accepted is True

    # Проверяем, что задача зарегистрирована в _active_tasks
    assert "btn_test_gc" in dispatcher._active_tasks

    # Провоцируем принудительную сборку мусора Python
    gc.collect()

    # Ждем завершения в пуле потоков
    dispatcher.thread_pool.waitForDone(2000)
    qapp.processEvents()

    assert len(received_finished) == 1
    assert received_finished[0][0] == "btn_test_gc"
    assert received_finished[0][1] is True
    # После завершения ссылка удалена из словаря активных задач
    assert "btn_test_gc" not in dispatcher._active_tasks


# -------------------------------------------------------------
# 5. Тесты расширенных моделей DuckDeck v0.4.0 (Step 1.2)
# -------------------------------------------------------------
def test_deck_button_config_extended_fields_and_validation():
    """Тест валидации slot_index (0..9), category, icon_size (16..128) и icon_path."""
    act = DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"})

    # Валидная конфигурация с новыми полями
    btn = DeckButtonConfig(
        id="btn_valid",
        slot_index=5,
        name="Ночной режим",
        title="Ночной режим",
        category="system",
        icon="🌙",
        icon_path="resources/deck/icons/system/dimmer.png",
        icon_size=48,
        action=act,
    )
    assert btn.slot_index == 5
    assert btn.category == "system"
    assert btn.name == "Ночной режим"
    assert btn.icon_size == 48
    assert btn.icon_path == "resources/deck/icons/system/dimmer.png"

    # Проверка дефолтных значений
    btn_defaults = DeckButtonConfig(id="btn_def", title="Дефолт", action=act)
    assert btn_defaults.slot_index == 0
    assert btn_defaults.category == "system"
    assert btn_defaults.icon_size == 48
    assert btn_defaults.icon == "⚡"

    # Невалидный slot_index (< 0 или > 9)
    with pytest.raises(ValidationError):
        DeckButtonConfig(id="btn_err_neg", slot_index=-1, title="Ошибка", action=act)

    with pytest.raises(ValidationError):
        DeckButtonConfig(id="btn_err_high", slot_index=10, title="Ошибка", action=act)

    # Невалидная категория
    with pytest.raises(ValidationError):
        DeckButtonConfig(id="btn_err_cat", category="invalid_cat", title="Ошибка", action=act)

    # Невалидный icon_size (< 16 или > 128)
    with pytest.raises(ValidationError):
        DeckButtonConfig(id="btn_err_size_low", icon_size=10, title="Ошибка", action=act)

    with pytest.raises(ValidationError):
        DeckButtonConfig(id="btn_err_size_high", icon_size=200, title="Ошибка", action=act)


def test_sound_settings_model_and_root_config():
    """Тест модели SoundSettings и интеграции в DeckRootConfig."""
    snd = SoundSettings()
    assert snd.enabled is True
    assert snd.volume == 0.8
    assert "button_click.wav" in snd.default_tap_sound
    assert "button_sw_page.wav" in snd.page_switch_sound
    assert "button_offline.wav" in snd.error_sound

    # Валидация громкости (0.0..1.0)
    with pytest.raises(ValidationError):
        SoundSettings(volume=-0.1)

    with pytest.raises(ValidationError):
        SoundSettings(volume=1.5)

    # DeckRootConfig по умолчанию включает SoundSettings и simulation_mode
    root = DeckRootConfig()
    assert isinstance(root.sound_settings, SoundSettings)
    assert root.simulation_mode is False


def test_deck_config_json_ten_buttons_per_page():
    """Проверка актуализированного config/deck_config.json: базовая валидация структуры страниц и кнопок."""
    cfg = DeckConfigLoader.load_from_file("config/deck_config.json")
    assert isinstance(cfg, DeckRootConfig)
    assert isinstance(cfg.sound_settings, SoundSettings)
    assert cfg.sound_settings.enabled is True
    assert len(cfg.pages) >= 1

    for page in cfg.pages:
        assert page.grid_rows == 2
        assert page.grid_cols == 5
        assert len(page.buttons) <= 10
        # Проверяем уникальность slot_index
        slots = [b.slot_index for b in page.buttons]
        assert len(slots) == len(set(slots))
        for btn in page.buttons:
            assert btn.category in ActionCategory.__args__
            assert btn.icon_size == 48


def test_deck_event_bus_signals():
    """Проверка регистрации и работы сигналов DuckDeck в core.event_bus."""
    from core.event_bus import bus

    notifications = []
    page_changes = []

    def on_notification(msg: str):
        notifications.append(msg)

    def on_page_changed(page_id: str):
        page_changes.append(page_id)

    bus.deck_notification.connect(on_notification)
    bus.deck_page_changed.connect(on_page_changed)

    try:
        bus.deck_notification.emit("Скриншот сохранен")
        bus.deck_page_changed.emit("media_controls")

        assert notifications == ["Скриншот сохранен"]
        assert page_changes == ["media_controls"]
    finally:
        bus.deck_notification.disconnect(on_notification)
        bus.deck_page_changed.disconnect(on_page_changed)


# -------------------------------------------------------------
# 10. Тесты simulation_mode (Stubs Mode) в ActionDispatcher (Шаг 4.1)
# -------------------------------------------------------------
def test_deck_action_dispatcher_simulation_mode_signals_and_no_background_tasks(qapp):
    """
    Тест режима simulation_mode в DeckActionDispatcher (Шаг 4.1):
    - При simulation_mode=True не запускаются фоновые задачи в QThreadPool (_active_tasks пуст).
    - Эмитятся сигналы action_started и action_finished с success=True.
    - В bus.deck_notification транслируется сообщение '[Stub Action] {title} (ID: {button_id})'.
    - Сохраняется защита от дребезга (debounce).
    """
    from core.event_bus import bus

    dispatcher = DeckActionDispatcher(simulation_mode=True, debounce_ms=200)
    assert dispatcher.simulation_mode is True

    started_events = []
    finished_events = []
    notifications = []

    dispatcher.action_started.connect(started_events.append)
    dispatcher.action_finished.connect(lambda b_id, ok, msg: finished_events.append((b_id, ok, msg)))

    def on_notif(msg: str):
        notifications.append(msg)

    bus.deck_notification.connect(on_notif)

    try:
        act = DeckActionConfig(action_type="system", params={"command": "toggle_mic_mute"})

        # Первый тап - принимается
        accepted = dispatcher.dispatch("btn_mute_mic", act, button_title="Микрофон")
        assert accepted is True

        # Проверка: фоновые задачи НЕ запущены
        assert len(dispatcher._active_tasks) == 0

        # Проверка сигналов
        assert started_events == ["btn_mute_mic"]
        assert len(finished_events) == 1
        assert finished_events[0] == ("btn_mute_mic", True, "[Stub Action] Микрофон (ID: btn_mute_mic)")
        assert notifications == ["[Stub Action] Микрофон (ID: btn_mute_mic)"]

        # Второй тап немедленно - отклоняется антидребезгом
        accepted_debounce = dispatcher.dispatch("btn_mute_mic", act, button_title="Микрофон")
        assert accepted_debounce is False
        assert len(finished_events) == 1

        # Отключение simulation_mode переводит диспетчер в боевой режим
        dispatcher.simulation_mode = False
        assert dispatcher.simulation_mode is False

    finally:
        bus.deck_notification.disconnect(on_notif)


def test_deck_action_dispatcher_simulation_mode_button_object_and_fallback_title(qapp):
    """
    Тест поддержки объекта DeckButtonConfig и автоматического fallback заголовка.
    """
    from core.event_bus import bus

    dispatcher = DeckActionDispatcher(simulation_mode=True, debounce_ms=10)
    notifications = []

    def on_notif(msg: str):
        notifications.append(msg)

    bus.deck_notification.connect(on_notif)

    try:
        act = DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "v"]})

        # 1. Вызов без указания button_title - fallback на button_id
        dispatcher.dispatch("btn_raw_id", act)
        assert notifications[-1] == "[Stub Action] btn_raw_id (ID: btn_raw_id)"

        # 2. Вызов с передачей объекта DeckButtonConfig
        btn_obj = DeckButtonConfig(
            id="btn_headphones",
            title="Наушники",
            slot_index=2,
            action=act,
        )
        dispatcher.dispatch(btn_obj, act)
        assert notifications[-1] == "[Stub Action] Наушники (ID: btn_headphones)"

    finally:
        bus.deck_notification.disconnect(on_notif)


def test_deck_view_simulation_mode_integration(qapp, sample_two_page_deck_config_path):
    """
    Интеграционный тест DeckView со сквозным тактильным циклом в simulation_mode:
    - Конфигурация DeckRootConfig с simulation_mode=True передается в диспетчер.
    - При нажатии на кнопку сетки вызывается dispatch с button_title.
    - Кнопка проходит тактильный цикл (executing -> success).
    - Сообщение транслируется в тикер и статус.
    """
    from core.event_bus import bus
    from modules.deck.view import DeckView

    notifs = []
    def on_notif(msg: str):
        notifs.append(msg)
    bus.deck_notification.connect(on_notif)

    try:
        view = DeckView(config_path=sample_two_page_deck_config_path)
        # Активируем режим симуляции
        view.dispatcher.simulation_mode = True

        btn_target = view.grid.get_button("btn_toggle_audio_device")
        assert btn_target is not None

        # Эмулируем срабатывание кнопки
        view._on_button_triggered(btn_target.button_config)

        # Проверяем переход в состояние success и отправку уведомления
        assert btn_target._state == "success"
        assert len(notifs) >= 1
        assert "[Stub Action] Аудиовыход (ID: btn_toggle_audio_device)" in notifs[-1]
        assert "[Stub Action]" in view.status_message

    finally:
        bus.deck_notification.disconnect(on_notif)
        view.cleanup()
        view.close()


# =============================================================================
# 8. Тесты реактивности симуляции, звукового отклика и DoD верификация (Шаг 4.3)
# =============================================================================

def test_deck_simulation_mode_and_audio_feedback_integration(qapp, sample_two_page_deck_config_path):
    """
    Проверка сквозного взаимодействия DeckView в simulation_mode с аудио-движком:
    - При клике на плитку: вызов sound_engine.play_tap(sound_override=...).
    - При смене страницы: вызов sound_engine.play_page_switch().
    - При ошибке действия: вызов sound_engine.play_error().
    - Тактильный цикл кнопки (executing -> success или executing -> error).
    """
    from core.event_bus import bus
    from modules.deck.sound_engine import DeckSoundEngine
    from modules.deck.view import DeckView

    mock_sound_engine = MagicMock(spec=DeckSoundEngine)
    notifs = []

    def on_notif(msg: str):
        notifs.append(msg)

    bus.deck_notification.connect(on_notif)

    try:
        view = DeckView(
            config_path=sample_two_page_deck_config_path,
            sound_engine=mock_sound_engine,
        )
        view.dispatcher.simulation_mode = True

        btn_target = view.grid.get_button("btn_toggle_audio_device")
        assert btn_target is not None

        # 1. Клик по плитке в режиме симуляции
        view._on_button_triggered(btn_target.button_config)

        # Проверка аудио-отклика клика
        mock_sound_engine.play_tap.assert_called_once_with(
            sound_override=btn_target.button_config.sound_override
        )

        # Проверка тактильного статуса кнопки и уведомления
        assert btn_target._state == "success"
        assert len(notifs) >= 1
        assert "[Stub Action] Аудиовыход" in notifs[-1]

        # 2. Аудио-отклик при завершении действия с ошибкой
        mock_sound_engine.reset_mock()
        view._on_action_finished("btn_toggle_audio_device", False, "Имитация ошибки")
        mock_sound_engine.play_error.assert_called_once()
        assert btn_target._state == "error"
        assert view.status_message == "Имитация ошибки"

        # 3. Аудио-отклик при смене страницы (свайп / пагинация)
        mock_sound_engine.reset_mock()
        view.next_page()
        mock_sound_engine.play_page_switch.assert_called_once()

    finally:
        bus.deck_notification.disconnect(on_notif)
        view.cleanup()
        view.close()


def test_deck_action_dispatcher_multi_button_debounce_isolation_in_simulation(qapp):
    """
    Проверка независимости антидребезга и изоляции задач в simulation_mode:
    - Тап по кнопке 1 блокирует повторный тап по кнопке 1 на время debounce (250 мс).
    - Тап по кнопке 2 принимается независимо без ложных блокировок.
    - В simulation_mode пул потоков QThreadPool не нагружается (_active_tasks == 0).
    """
    dispatcher = DeckActionDispatcher(simulation_mode=True, debounce_ms=250)
    started = []
    finished = []

    dispatcher.action_started.connect(started.append)
    dispatcher.action_finished.connect(lambda b_id, ok, msg: finished.append((b_id, ok, msg)))

    act1 = DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"})
    act2 = DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "c"]})

    # Тап 1: Кнопка A
    assert dispatcher.dispatch("btn_a", act1, button_title="Диммер") is True
    assert started == ["btn_a"]
    assert len(finished) == 1
    assert len(dispatcher._active_tasks) == 0

    # Повторный тап Кнопки A сразу — блокируется антидребезгом
    assert dispatcher.dispatch("btn_a", act1, button_title="Диммер") is False
    assert len(finished) == 1

    # Тап Кнопки B сразу — принимается успешно (антидребезг изолирован по ID кнопки)
    assert dispatcher.dispatch("btn_b", act2, button_title="Копировать") is True
    assert started == ["btn_a", "btn_b"]
    assert len(finished) == 2
    assert finished[-1][0] == "btn_b"
    assert len(dispatcher._active_tasks) == 0


def test_action_runnable_combat_handlers_integrity(qapp):
    """
    Архитектурная проверка сохранения боевых обработчиков (DoD Invariant):
    - Все боевые функции модулей modules/deck/actions/ импортируются и работоспособны.
    - При выключенном simulation_mode диспетчер запускает боевую задачу через QThreadPool.
    """
    from modules.deck.actions.hotkey_sender import send_hotkey
    from modules.deck.actions.process_launcher import launch_process
    from modules.deck.actions.http_client import execute_http_request
    from modules.deck.actions.screen_capture import capture_screen

    # Проверка доступности боевых функций модулей
    assert callable(send_hotkey)
    assert callable(launch_process)
    assert callable(execute_http_request)
    assert callable(capture_screen)

    dispatcher = DeckActionDispatcher(simulation_mode=False, debounce_ms=50)
    act = DeckActionConfig(action_type="system", params={"command": "toggle_dimmer"})

    with patch.object(dispatcher.thread_pool, "start") as mock_pool_start:
        accepted = dispatcher.dispatch("btn_live", act, button_title="Диммер")
        assert accepted is True
        # В боевом режиме задача отправляется в QThreadPool
        mock_pool_start.assert_called_once()
        assert len(dispatcher._active_tasks) == 1


# =============================================================================
# 9. TDD тесты Этапа 1: Модели 8 базовых примитивов, нормализатор и пресеты
# =============================================================================
from modules.deck.models import (
    ActionPresetDefinition,
    AudioActionParams,
    DeckActionNormalizer,
    DeckNavActionParams,
    HotkeyActionParams,
    LaunchActionParams,
    MacroActionParams,
    MediaActionParams,
    SystemActionParams,
    TextActionParams,
)
from pydantic import ValidationError


@pytest.mark.parametrize(
    "legacy_type,legacy_params,expected_type,expected_target,expected_cmd",
    [
        ("website", {"url": "https://github.com"}, "launch", "https://github.com", None),
        ("open_website", {"url": "http://duckdock.local"}, "launch", "http://duckdock.local", None),
        ("open_app", {"executable": "wt.exe", "args": ["-p", "PowerShell"]}, "launch", "wt.exe", None),
        ("open_path", {"path": "C:\\Games"}, "launch", "C:\\Games", None),
        ("launch", {"path": "calc.exe"}, "launch", "calc.exe", None),
        ("http_request", {"url": "http://127.0.0.1:8000/api", "method": "POST"}, "launch", "http://127.0.0.1:8000/api", None),
        ("hotkey", {"keys": ["ctrl", "c"]}, "hotkey", None, None),
        ("hotkey_switch", {"state_1": {"keys": ["f1"]}, "state_2": {"keys": ["f2"]}}, "hotkey", None, None),
        ("volume_control", {"target": "master", "command": "volume_up", "step_percent": 10}, "audio", "master", "step"),
        ("volume_control", {"target": "microphone", "command": "toggle_mute"}, "audio", "mic", "toggle_mute"),
        ("audio_device", {"mode": "toggle", "devices": ["Наушники", "Динамики"]}, "audio", "device", "toggle_device"),
        ("play_audio", {"file_path": "click.wav"}, "audio", "soundboard", "play_sound"),
        ("stop_audio", {}, "audio", "soundboard", "stop_sound"),
        ("multimedia", {"command": "next_track"}, "media", None, "next_track"),
        ("text_macro", {"text": "Hello World", "send_enter": True}, "text", None, None),
        ("screenshot", {"target": "primary_screen"}, "system", None, "screenshot"),
        ("close_window", {"target": "active_window"}, "system", None, "close_window"),
        ("brightness", {}, "system", None, "dimmer"),
        ("sleep_display", {}, "system", None, "sleep_display"),
        ("system", {"command": "toggle_dimmer"}, "system", None, "dimmer"),
        ("system", {"command": "lock_workstation"}, "system", None, "lock_pc"),
        ("navigation", {"target_page_id": "page_gaming"}, "deck_nav", "page_gaming", "goto_page"),
        ("create_folder", {"page_id": "tools_folder"}, "deck_nav", "tools_folder", "folder_open"),
        ("switch_profile", {"page_id": "profile_dev"}, "deck_nav", "profile_dev", "goto_page"),
        ("prev_page", {}, "deck_nav", None, "prev_page"),
        ("next_page", {}, "deck_nav", None, "next_page"),
        ("goto_page", {"page_id": "p2"}, "deck_nav", "p2", "goto_page"),
        ("page_indicator", {"page_id": "p1"}, "deck_nav", "p1", "goto_page"),
        ("multi_action", {"steps": []}, "macro", None, None),
        ("multi_action_switch", {"steps": []}, "macro", None, None),
    ],
)
def test_deck_action_normalizer_legacy_migration(
    legacy_type, legacy_params, expected_type, expected_target, expected_cmd
):
    """
    Шаг 1.4: Проверка прозрачной миграции всех 26+ устаревших типов конфигураций
    в 8 канонических базовых примитивов DuckDeck.
    """
    config = DeckActionConfig(action_type=legacy_type, params=legacy_params)
    assert config.action_type == expected_type

    typed = config.get_typed_params()
    if expected_type == "launch":
        assert isinstance(typed, LaunchActionParams)
        if expected_target:
            assert typed.target == expected_target
    elif expected_type == "audio":
        assert isinstance(typed, AudioActionParams)
        if expected_target:
            assert typed.target == expected_target
        if expected_cmd:
            assert typed.command == expected_cmd
    elif expected_type == "hotkey":
        assert isinstance(typed, HotkeyActionParams)
    elif expected_type == "media":
        assert isinstance(typed, MediaActionParams)
        if expected_cmd:
            assert typed.command == expected_cmd
    elif expected_type == "text":
        assert isinstance(typed, TextActionParams)
    elif expected_type == "system":
        assert isinstance(typed, SystemActionParams)
        if expected_cmd:
            assert typed.command == expected_cmd
    elif expected_type == "deck_nav":
        assert isinstance(typed, DeckNavActionParams)
        if expected_target:
            assert typed.page_id == expected_target
        if expected_cmd:
            assert typed.target == expected_cmd
    elif expected_type == "macro":
        assert isinstance(typed, MacroActionParams)


def test_eight_core_primitives_strict_validation():
    """
    Шаг 1.4: Проверка строгой валидации параметров для каждого из 8 примитивов
    с валидными и невалидными значениями (Pydantic ValidationError).
    """
    # 1. HotkeyActionParams
    hk = HotkeyActionParams(keys=["ctrl", "shift", "d"], mode="toggle", toggle_keys=["ctrl", "alt", "d"])
    assert hk.mode == "toggle"
    with pytest.raises(ValidationError):
        HotkeyActionParams(mode="invalid_mode")  # type: ignore

    # 2. LaunchActionParams
    la = LaunchActionParams(target="notepad.exe", args=["test.txt"], working_dir="C:\\", kind="app")
    assert la.target == "notepad.exe"
    assert la.path == "notepad.exe"
    with pytest.raises(ValidationError):
        LaunchActionParams(kind="invalid_kind")  # type: ignore

    # 3. AudioActionParams
    aud = AudioActionParams(target="mic", command="toggle_mute", step_percent=10)
    assert aud.target == "mic"
    assert aud.command == "toggle_mute"
    with pytest.raises(ValidationError):
        AudioActionParams(target="invalid_target")  # type: ignore
    with pytest.raises(ValidationError):
        AudioActionParams(command="invalid_cmd")  # type: ignore

    # 4. MediaActionParams
    med = MediaActionParams(command="next_track")
    assert med.command == "next_track"
    with pytest.raises(ValidationError):
        MediaActionParams(command="invalid_media")  # type: ignore

    # 5. TextActionParams
    txt = TextActionParams(text="git status", send_enter=True)
    assert txt.text == "git status"
    assert txt.send_enter is True

    # 6. SystemActionParams
    sys_p = SystemActionParams(command="dimmer", screenshot_target="primary")
    assert sys_p.command == "dimmer"
    assert sys_p.screenshot_target == "primary"
    with pytest.raises(ValidationError):
        SystemActionParams(command="non_existent_sys_cmd")  # type: ignore

    # 7. DeckNavActionParams
    nav = DeckNavActionParams(target="folder_open", page_id="folder_sub")
    assert nav.target == "folder_open"
    assert nav.page_id == "folder_sub"
    assert nav.target_page_id == "folder_sub"
    with pytest.raises(ValidationError):
        DeckNavActionParams(target="invalid_nav_target")  # type: ignore

    # 8. MacroActionParams
    mac = MacroActionParams(steps=[DeckActionConfig(action_type="hotkey", params={"keys": ["enter"]})], delay_ms=100)
    assert len(mac.steps) == 1
    assert mac.delay_ms == 100


def test_action_preset_definition_model():
    """
    Шаг 1.4: Проверка декларативной схемы ActionPresetDefinition.
    """
    preset = ActionPresetDefinition(
        id="discord_mute",
        category="audio_comm",
        title_key="deck.presets.discord_mute.title",
        desc_key="deck.presets.discord_mute.desc",
        icon="🎤",
        color_accent="#818cf8",
        status_source="mic_mute",
        base_action=DeckActionConfig(
            action_type="hotkey",
            params={"keys": ["ctrl", "shift", "m"]},
        ),
        keywords=["discord", "mute", "микрофон", "дискорд"],
    )
    assert preset.id == "discord_mute"
    assert preset.category == "audio_comm"
    assert preset.base_action.action_type == "hotkey"
    assert len(preset.keywords) == 4

    # Сериализация и десериализация пресета
    dumped = preset.model_dump_json()
    reloaded = ActionPresetDefinition.model_validate_json(dumped)
    assert reloaded.id == preset.id
    assert reloaded.base_action.action_type == "hotkey"


def test_deck_action_serialization_and_roundtrip():
    """
    Шаг 1.4: Проверка JSON roundtrip сериализации/десериализации для всех 8 примитивов.
    """
    primitives = [
        DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "alt", "del"], "mode": "press"}),
        DeckActionConfig(action_type="launch", params={"target": "wt.exe", "kind": "app"}),
        DeckActionConfig(action_type="audio", params={"target": "device", "command": "toggle_device"}),
        DeckActionConfig(action_type="media", params={"command": "play_pause"}),
        DeckActionConfig(action_type="text", params={"text": "echo 1", "send_enter": True}),
        DeckActionConfig(action_type="system", params={"command": "dimmer"}),
        DeckActionConfig(action_type="deck_nav", params={"target": "next_page"}),
        DeckActionConfig(action_type="macro", params={"steps": [], "delay_ms": 25}),
    ]

    for original in primitives:
        json_data = original.model_dump_json()
        restored = DeckActionConfig.model_validate_json(json_data)
        assert restored.action_type == original.action_type
        assert restored.params == original.params





