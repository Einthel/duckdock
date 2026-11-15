"""
Модульные тесты интерфейса сенсорной макро-панели DuckDeck.
Проверяют:
  - Соблюдение инварианта Qt.NoFocus на 100% интерактивных элементов.
  - Точную геометрию под экран 944x600 (тайлы 174x168 px для 3x5 и 143x123 px для 4x6).
  - Тактильный отклик и состояния [state="..."] (вдавливание +2 px, шейк _content_offset).
  - Централизованную реактивность Live Dynamic Tiles через EventBus (аудио, микрофон, диммер).
  - Навигацию между страницами и безопасную перезагрузку конфига.
  - Гарантированную отписку от EventBus и отсутствие утечек памяти.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from core.deck.action_dispatcher import DeckActionDispatcher
from core.deck.models import (
    DeckActionConfig,
    DeckButtonConfig,
    DeckConfigLoader,
    DeckPageConfig,
    DeckRootConfig,
)
from core.event_bus import bus
from ui.modules.deck_view import DeckButtonWidget, DeckGrid, DeckView, HeaderBar


@pytest.fixture(scope="session")
def qapp():
    """Гарантирует существование экземпляра QApplication для тестов UI."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_button_config():
    """Тестовая конфигурация кнопки."""
    return DeckButtonConfig(
        id="btn_test_audio",
        title="Тест Аудио",
        icon="🎧",
        color_accent="#06b6d4",
        status_source="audio_device",
        action=DeckActionConfig(
            action_type="audio_device",
            params={"mode": "toggle", "devices": ["Наушники", "Динамики"]},
        ),
    )


# -------------------------------------------------------------
# 1. Проверка инвариантов фокуса (Qt.NoFocus)
# -------------------------------------------------------------
def test_deck_view_no_focus_invariant(qapp):
    """Инвариант Stealth Focus: все элементы DeckView обязаны иметь Qt.NoFocus."""
    view = DeckView(config_path="config/deck_config.json")
    try:
        assert view.focusPolicy() == Qt.NoFocus
        assert view.header_bar.focusPolicy() == Qt.NoFocus
        assert view.header_bar.btn_reload.focusPolicy() == Qt.NoFocus
        assert view.grid.focusPolicy() == Qt.NoFocus

        # Проверка всех кнопок-пилюль в шапке
        for pill_btn in view.header_bar._pill_buttons.values():
            assert pill_btn.focusPolicy() == Qt.NoFocus

        # Проверка всех тайлов сетки и их дочерних меток
        buttons = view.grid.get_buttons()
        assert len(buttons) > 0
        for btn_id, btn in buttons.items():
            assert btn.focusPolicy() == Qt.NoFocus
            assert btn.lbl_icon.focusPolicy() == Qt.NoFocus
            assert btn.lbl_title.focusPolicy() == Qt.NoFocus
            assert btn.lbl_status.focusPolicy() == Qt.NoFocus
    finally:
        view.cleanup()


# -------------------------------------------------------------
# 2. Проверка точной геометрии под экран 944x600
# -------------------------------------------------------------
def test_deck_view_geometry_and_tile_dimensions(qapp):
    """
    Проверка строгой геометрии:
      - DeckView: 944x600 px.
      - HeaderBar: 944x48 px.
      - DeckGrid: 944x552 px (отступы 12 px, промежутки 12 px).
      - Сетка 3x5: тайлы 174x168 px, скругление 14 px.
      - Сетка 4x6: тайлы 143x123 px, скругление 10 px.
    """
    view = DeckView(config_path="config/deck_config.json")
    try:
        assert view.width() == 944
        assert view.height() == 600

        assert view.header_bar.width() == 944
        assert view.header_bar.height() == 48

        assert view.grid.width() == 944
        assert view.grid.height() == 552
        margins = view.grid.grid_layout.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (12, 12, 12, 12)
        assert view.grid.grid_layout.spacing() == 12

        # 3x5 страница по умолчанию
        view.set_active_page("default")
        buttons_3x5 = view.grid.get_buttons()
        for btn_id, btn in buttons_3x5.items():
            assert btn.width() == 174
            assert btn.height() == 168
            assert btn.corner_radius == 14

        # 4x6 страница
        view.set_active_page("grid4x6")
        buttons_4x6 = view.grid.get_buttons()
        for btn_id, btn in buttons_4x6.items():
            assert btn.width() == 143
            assert btn.height() == 123
            assert btn.corner_radius == 10
    finally:
        view.cleanup()


# -------------------------------------------------------------
# 3. Проверка тактильных состояний и _content_offset
# -------------------------------------------------------------
def test_deck_button_tactile_states_and_shake(qapp, sample_button_config):
    """
    Проверка тактильного отклика:
      - 'idle': _content_offset = (0, 0)
      - 'pressed': вдавливание _content_offset = (0, 2)
      - 'executing': _content_offset = (0, 0)
      - 'success': _content_offset = (0, 0), возврат в idle по таймеру
      - 'error': шейк содержимого _content_offset без изменения внешней геометрии кнопки.
    """
    btn = DeckButtonWidget(button_config=sample_button_config, rows=3, cols=5)
    try:
        assert btn.state == "idle"
        assert btn.content_offset == (0, 0)
        assert btn.size().width() == 174
        assert btn.size().height() == 168

        # Нажатие: вдавливание на 2 px
        btn.set_state("pressed")
        assert btn.state == "pressed"
        assert btn.content_offset == (0, 2)
        # Внешний размер не должен измениться
        assert btn.size().width() == 174
        assert btn.size().height() == 168

        # Исполнение
        btn.set_state("executing")
        assert btn.state == "executing"
        assert btn.content_offset == (0, 0)

        # Ошибка: шейк содержимого
        btn.set_state("error")
        assert btn.state == "error"
        # Выполняем шаг шейка
        btn._on_shake_tick()
        assert btn.content_offset[0] != 0  # Горизонтальное смещение
        assert btn.size().width() == 174    # Внешняя геометрия нерушима

        # Успех: сброс смещения и таймер
        btn.set_state("success")
        assert btn.state == "success"
        assert btn.content_offset == (0, 0)
        assert btn._reset_timer.isActive()

        # Возврат в idle
        btn._on_reset_timeout()
        assert btn.state == "idle"
        assert btn.content_offset == (0, 0)
    finally:
        btn.cleanup()


# -------------------------------------------------------------
# 4. Проверка мышиных и сенсорных событий кнопки
# -------------------------------------------------------------
def test_deck_button_mouse_events_and_trigger(qapp, sample_button_config):
    """Проверка генерации сигнала triggered при нажатии и отпускании внутри тайла."""
    btn = DeckButtonWidget(button_config=sample_button_config, rows=3, cols=5)
    signal_received = []
    btn.triggered.connect(lambda cfg: signal_received.append(cfg))

    try:
        # Нажатие ЛКМ
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(50, 50),
            QPointF(50, 50),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        btn.mousePressEvent(press_event)
        assert btn.state == "pressed"
        assert len(signal_received) == 0

        # Отпускание ЛКМ внутри кнопки
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(50, 50),
            QPointF(50, 50),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier,
        )
        btn.mouseReleaseEvent(release_event)
        assert btn.state == "executing"
        assert len(signal_received) == 1
        assert signal_received[0].id == "btn_test_audio"

        # Отпускание ЛКМ за пределами кнопки не должно вызывать triggered
        btn.mousePressEvent(press_event)
        assert btn.state == "pressed"
        outside_release = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(500, 500),  # Вне пределов 174x168
            QPointF(500, 500),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier,
        )
        btn.mouseReleaseEvent(outside_release)
        assert btn.state == "idle"
        assert len(signal_received) == 1  # Больше не увеличилось
    finally:
        btn.cleanup()


def test_deck_button_executing_watchdog_timeout(qapp):
    """Тест автоматического сброса подсветки тайла из состояния executing сторожевым таймером."""
    btn = DeckButtonWidget(
        DeckButtonConfig(
            id="btn_watchdog",
            title="Watchdog Test",
            icon="⚡",
            action=DeckActionConfig(action_type="hotkey", params={"keys": ["f1"]}),
        ),
        rows=3,
        cols=5,
    )
    try:
        btn.set_state("executing")
        assert btn.state == "executing"
        assert btn._reset_timer.isActive()

        # Симулируем срабатывание сторожевого таймера
        btn._on_reset_timeout()
        assert btn.state == "idle"
    finally:
        btn.cleanup()


# -------------------------------------------------------------
# 5. Централизованная реактивность Live Dynamic Tiles
# -------------------------------------------------------------
def test_deck_view_live_dynamic_tiles_reactivity(qapp):
    """
    Проверка централизованной реактивности живых тайлов:
      - bus.playback_device_changed меняет иконку (🎧/🔊) и строку устройства.
      - bus.mic_mute_changed меняет иконку (🎙/🔇) и статус 'Включен'/'Выключен'.
      - bus.dimmer_opacity_changed обновляет статус процента затемнения.
    """
    view = DeckView(config_path="config/deck_config.json")
    try:
        view.set_active_page("default")
        audio_btn = view.grid.get_button("btn_toggle_audio_device")
        mic_btn = view.grid.get_button("btn_mute_mic")
        dimmer_btn = view.grid.get_button("btn_toggle_dimmer")

        assert audio_btn is not None
        assert mic_btn is not None
        assert dimmer_btn is not None

        # 1. Смена аудиовыхода на Наушники
        bus.playback_device_changed.emit("Наушники HyperX Cloud", "{guid-1}")
        assert audio_btn.lbl_icon.text() == "🎧"
        assert "Наушники" in audio_btn.lbl_status.text()
        assert not audio_btn.lbl_status.isHidden()

        # 2. Смена аудиовыхода на Динамики
        bus.playback_device_changed.emit("Динамики Realtek Audio", "{guid-2}")
        assert audio_btn.lbl_icon.text() == "🔊"
        assert "Динамики" in audio_btn.lbl_status.text()

        # 3. Отключение микрофона (Mute)
        bus.mic_mute_changed.emit(True)
        assert mic_btn.lbl_icon.text() == "🔇"
        assert mic_btn.lbl_status.text() == "Выключен"

        # 4. Включение микрофона (Unmute)
        bus.mic_mute_changed.emit(False)
        assert mic_btn.lbl_icon.text() == "🎙"
        assert mic_btn.lbl_status.text() == "Включен"

        # 5. Регулировка ночного режима
        bus.dimmer_opacity_changed.emit(0.65)
        assert dimmer_btn.lbl_status.text() == "65%"
    finally:
        view.cleanup()


# -------------------------------------------------------------
# 6. Навигация между страницами и HeaderBar
# -------------------------------------------------------------
def test_deck_view_page_navigation(qapp):
    """Проверка переключения страниц через HeaderBar и навигационные кнопки."""
    view = DeckView(config_path="config/deck_config.json")
    try:
        assert view.active_page_id == "default"
        assert "btn_toggle_audio_device" in view.grid.get_buttons()

        # Переключение на страницу 4x6 через сигнал шапки
        view.header_bar.page_selected.emit("grid4x6")
        assert view.active_page_id == "grid4x6"
        assert "btn_stream_back" in view.grid.get_buttons()

        # Возврат на основную страницу через навигационную кнопку "btn_stream_back"
        back_btn = view.grid.get_button("btn_stream_back")
        assert back_btn is not None
        view._on_button_triggered(back_btn.button_config)
        assert view.active_page_id == "default"
    finally:
        view.cleanup()


# -------------------------------------------------------------
# 7. Интеграция с диспетчером действий и индикация состояний
# -------------------------------------------------------------
def test_deck_view_action_dispatch_and_feedback(qapp):
    """
    Проверка прохождения действий через диспетчер:
      - Начало действия переводит кнопку в 'executing'.
      - Завершение переводит в 'success' (при True) или 'error' (при False).
    """
    mock_dispatcher = MagicMock(spec=DeckActionDispatcher)
    mock_dispatcher.dispatch.return_value = True

    from PySide6.QtCore import Signal, QObject
    class DummyDispatcher(QObject):
        action_started = Signal(str)
        action_finished = Signal(str, bool, str)
        def dispatch(self, btn_id, act):
            return True

    dummy_disp = DummyDispatcher()
    view = DeckView(config_path="config/deck_config.json", dispatcher=dummy_disp)
    try:
        btn = view.grid.get_button("btn_screenshot_primary")
        assert btn is not None

        # Имитируем нажатие
        view._on_button_triggered(btn.button_config)

        # Диспетчер рапортует старт
        dummy_disp.action_started.emit("btn_screenshot_primary")
        assert btn.state == "executing"

        # Диспетчер рапортует успешный финиш
        dummy_disp.action_finished.emit("btn_screenshot_primary", True, "Скриншот скопирован")
        assert btn.state == "success"
        assert "Скриншот скопирован" in view.header_bar.lbl_status.text()

        # Диспетчер рапортует ошибку
        dummy_disp.action_finished.emit("btn_screenshot_primary", False, "Сбой захвата экрана")
        assert btn.state == "error"
        assert "Сбой захвата экрана" in view.header_bar.lbl_status.text()
    finally:
        view.cleanup()


# -------------------------------------------------------------
# 8. Перезагрузка конфигурации и устойчивость к ошибкам
# -------------------------------------------------------------
def test_deck_view_reload_config_and_fallback(qapp):
    """Проверка горячей перезагрузки конфигурации и fallback при поврежденном файле."""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json", encoding="utf-8") as tf:
        json.dump({
            "active_profile": "custom",
            "pages": [{
                "id": "custom",
                "name": "Пользовательский",
                "grid_rows": 3,
                "grid_cols": 5,
                "buttons": [{
                    "id": "btn_c1",
                    "title": "Кнопка 1",
                    "icon": "⚡",
                    "color_accent": "#f59e0b",
                    "action": {"action_type": "hotkey", "params": {"keys": ["f5"]}}
                }]
            }]
        }, tf)
        tmp_path = tf.name

    try:
        view = DeckView(config_path=tmp_path)
        assert view.active_page_id == "custom"
        assert "btn_c1" in view.grid.get_buttons()

        # Повреждаем файл конфигурации
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON DATA")

        # Перезагружаем — должен сработать fallback на дефолт без краша
        view.reload_config()
        assert view.root_config is not None
        assert len(view.grid.get_buttons()) > 0
    finally:
        view.cleanup()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# -------------------------------------------------------------
# 9. Гарантированная отписка от EventBus и отсутствие утечек
# -------------------------------------------------------------
def test_deck_view_cleanup_eventbus_unsubscription(qapp):
    """
    Проверка отсутствия утечек подписчиков EventBus после вызова cleanup():
    эмиссия сигналов после очистки не должна вызывать исключений или обновления несуществующих тайлов.
    """
    view = DeckView(config_path="config/deck_config.json")
    audio_btn = view.grid.get_button("btn_toggle_audio_device")
    assert audio_btn is not None

    view.cleanup()

    # Эмитируем сигнал в шину после отписки
    bus.playback_device_changed.emit("Новое Устройство", "{id}")
    # Проверяем, что флаг подключения сброшен
    assert not view._eventbus_connected
