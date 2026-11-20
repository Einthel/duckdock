"""
Тестирование изоляции сенсорных жестов, свайпов и пагинации DuckDeck (Спринт 6, Шаги 3.2 и 3.3).

Проверяет:
  1. Изоляция жестов и бесконфликтность с TouchCursorFilter:
     - Сброс состояния кнопки DeckButtonWidget при горизонтальном сдвиге |dx| >= 20 px.
     - Малый тремор (|dx| < 20 px): обычный тап штатно срабатывает (triggered.emit).
     - Подавление mouseReleaseEvent при распознанном свайпе.
     - 2-пальцевые тач-события свободно пропускаются к TouchCursorFilter без перехвата кнопкой.
     - Двухпальцевый вертикальный свайп переключает вкладки, не вызывая действий кнопок дека.
     - Сетка кнопок DeckGrid проксирует свайпы (swipe_left, swipe_right) и сбрасывает плитки.
  2. Пагинация и кинетическая анимация:
     - Свайп влево (dx < -60 px) -> переход на следующую страницу (page_idx + 1).
     - Свайп вправо (dx > +60 px) -> переход на предыдущую страницу (page_idx - 1).
     - Свайп по сетке кнопок DeckGrid переключает страницы.
     - Граничные условия пагинации (крайняя левая и крайняя правая страницы).
     - Синхронизация точек в DotPagingWidget (выбор точки и кинетическая анимация QVariantAnimation).
     - Эмиссия и реакция на сигнал шины событий core.event_bus.bus.deck_page_changed.
"""
import time
from unittest.mock import MagicMock
import pytest

from PySide6.QtCore import Qt, QPointF, QEvent, QVariantAnimation
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QTouchEvent, QEventPoint, QMouseEvent

from core.event_bus import bus
from core.touch_filter import TouchCursorFilter
from modules.deck.models import DeckActionConfig, DeckButtonConfig, DeckPageConfig
from modules.deck.view import DeckView
from modules.deck.widgets.deck_button import DeckButtonWidget
from modules.deck.widgets.deck_grid import DeckGrid
from modules.deck.widgets.interactive_panel import DotPagingWidget, DeckInteractivePanel
from modules.deck.widgets.swipe_detector import DeckSwipeDetector


def create_touch_event(etype, points_coords):
    """Вспомогательная функция для генерации синтетического QTouchEvent."""
    pts = []
    state = (
        QEventPoint.State.Pressed
        if etype == QEvent.Type.TouchBegin
        else (
            QEventPoint.State.Released
            if etype in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel)
            else QEventPoint.State.Updated
        )
    )
    for idx, (x, y) in enumerate(points_coords):
        pt = QEventPoint(idx, state, QPointF(x, y), QPointF(x, y))
        pts.append(pt)
    return QTouchEvent(etype, None, Qt.KeyboardModifier.NoModifier, pts)


@pytest.fixture
def test_button_config():
    return DeckButtonConfig(
        id="btn_test_swipe",
        title="Swipe Test Button",
        icon="⚡",
        color_accent="#38bdf8",
        action=DeckActionConfig(action_type="hotkey", params={"keys": ["ctrl", "t"]}),
    )


# =============================================================================
# 1. Тестирование сброса состояния DeckButtonWidget при |dx| >= 20 px
# =============================================================================

@pytest.mark.unit
def test_deck_button_reset_state_on_mouse_drag_20px(qapp, test_button_config):
    """
    При смещении курсора/пальца по горизонтали |dx| >= 20 px состояние кнопки
    должно сбрасываться в 'idle', _is_pressed = False, _swipe_consumed = True.
    """
    btn = DeckButtonWidget(button_config=test_button_config, rows=2, cols=5)
    triggered_calls = []
    btn.triggered.connect(lambda cfg: triggered_calls.append(cfg))

    try:
        # 1. Нажатие в точке (50, 50)
        press_ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(50, 50),
            QPointF(50, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mousePressEvent(press_ev)
        assert btn.is_pressed is True
        assert btn.state == "pressed"
        assert btn.swipe_consumed is False

        # 2. Небольшое смещение на 10 px (|dx| = 10 < 20 px) -> остается pressed
        move_small_ev = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(60, 52),
            QPointF(60, 52),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mouseMoveEvent(move_small_ev)
        assert btn.is_pressed is True
        assert btn.state == "pressed"

        # 3. Смещение на 22 px (|dx| = 22 >= 20 px) -> сброс в idle
        move_large_ev = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(72, 52),
            QPointF(72, 52),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mouseMoveEvent(move_large_ev)
        assert btn.is_pressed is False
        assert btn.state == "idle"
        assert btn.swipe_consumed is True

        # 4. Отпускание кнопки -> клик должен быть подавлен
        release_ev = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(72, 52),
            QPointF(72, 52),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mouseReleaseEvent(release_ev)
        assert len(triggered_calls) == 0
        assert btn.state == "idle"
    finally:
        btn.cleanup()


@pytest.mark.unit
def test_deck_button_reset_state_on_touch_update_20px(qapp, test_button_config):
    """
    Сенсорное событие QTouchEvent с |dx| >= 20 px также должно сбрасывать кнопку.
    """
    btn = DeckButtonWidget(button_config=test_button_config, rows=2, cols=5)
    triggered_calls = []
    btn.triggered.connect(lambda cfg: triggered_calls.append(cfg))

    try:
        # Нажатие 1 пальцем
        ev_press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(40, 40),
            QPointF(40, 40),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mousePressEvent(ev_press)
        assert btn.is_pressed is True

        # TouchBegin в точке (40, 40)
        ev_touch_begin = create_touch_event(QEvent.Type.TouchBegin, [(40, 40)])
        btn.event(ev_touch_begin)

        # TouchUpdate со сдвигом влево на 25 px (X=15, dx=-25, |dx| >= 20)
        ev_touch_update = create_touch_event(QEvent.Type.TouchUpdate, [(15, 40)])
        btn.event(ev_touch_update)

        assert btn.is_pressed is False
        assert btn.state == "idle"
        assert btn.swipe_consumed is True

        # Отпускание кнопки не вызывает triggered
        ev_release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(15, 40),
            QPointF(15, 40),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mouseReleaseEvent(ev_release)
        assert len(triggered_calls) == 0
    finally:
        btn.cleanup()


@pytest.mark.unit
def test_deck_button_tap_with_small_tremor_triggers_normally(qapp, test_button_config):
    """
    Обычный тап с легким дрожанием пальца (|dx| < 20 px) не должен сбрасывать кнопку
    и должен штатно генерировать сигнал triggered.
    """
    btn = DeckButtonWidget(button_config=test_button_config, rows=2, cols=5)
    triggered_calls = []
    btn.triggered.connect(lambda cfg: triggered_calls.append(cfg))

    try:
        # Нажатие
        press_ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(50, 50),
            QPointF(50, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mousePressEvent(press_ev)
        assert btn.state == "pressed"

        # Микросдвиг пальца на 8 px (|dx| = 8 < 20 px)
        move_ev = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(58, 54),
            QPointF(58, 54),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mouseMoveEvent(move_ev)
        assert btn.state == "pressed"
        assert btn.is_pressed is True

        # Отпускание внутри тайла
        release_ev = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(58, 54),
            QPointF(58, 54),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mouseReleaseEvent(release_ev)

        assert len(triggered_calls) == 1
        assert triggered_calls[0].id == "btn_test_swipe"
        assert btn.state == "executing"
    finally:
        btn.cleanup()


# =============================================================================
# 2. Бесконфликтность с core.touch_filter.TouchCursorFilter (2 пальца = вкладки)
# =============================================================================

@pytest.mark.unit
def test_two_finger_touch_on_deck_button_resets_button_and_passes_event(qapp, test_button_config):
    """
    При обнаружении 2 пальцев (len(points) > 1):
    1. Кнопка сбрасывается в idle и не захватывает клик.
    2. Событие возвращает False (не поглощается), давая TouchCursorFilter обработать жест.
    """
    btn = DeckButtonWidget(button_config=test_button_config, rows=2, cols=5)
    try:
        # Первоначальное касание 1 пальцем
        press_ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(50, 50),
            QPointF(50, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        btn.mousePressEvent(press_ev)
        assert btn.state == "pressed"
        assert btn.is_pressed is True

        # Опускается 2-й палец (len(points) == 2)
        ev_two_finger = create_touch_event(
            QEvent.Type.TouchUpdate,
            [(50, 50), (120, 50)],
        )
        consumed = btn.event(ev_two_finger)

        # Событие НЕ должно поглощаться кнопкой
        assert consumed is False
        # Кнопка сброшена в idle
        assert btn.state == "idle"
        assert btn.is_pressed is False
        assert btn.swipe_consumed is True
    finally:
        btn.cleanup()


@pytest.mark.unit
def test_two_finger_swipe_over_deck_button_switches_tab_without_button_trigger(qapp, test_button_config):
    """
    Интеграционный тест: двухпальцевый вертикальный свайп через TouchCursorFilter
    над кнопкой DeckButtonWidget должен:
    1. Переключить вкладку приложения через bus.tab_changed.
    2. Не вызывать срабатывания кнопки DeckButtonWidget.
    3. Подавить синтетический MouseButtonRelease.
    """
    filter_obj = TouchCursorFilter()
    btn = DeckButtonWidget(button_config=test_button_config, rows=2, cols=5)

    triggered_calls = []
    btn.triggered.connect(lambda cfg: triggered_calls.append(cfg))

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    filter_obj._current_tab = 2  # Deck Tab

    try:
        # 1. 2 пальца опускаются на кнопку
        ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(50, 100), (100, 100)])
        filter_obj.eventFilter(btn, ev_begin)
        btn.event(ev_begin)
        assert btn.state == "idle"

        # 2. Вертикальное смещение вверх на 80 px (dy = -80 px)
        ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(50, 20), (100, 20)])
        consumed_filter = filter_obj.eventFilter(btn, ev_update)
        btn.event(ev_update)

        assert consumed_filter is True
        assert tabs_received == [3]  # Переключение на вкладку Audio (2 + 1 = 3)
        assert filter_obj._suppress_mouse_release is True

        # 3. TouchEnd
        ev_end = create_touch_event(QEvent.Type.TouchEnd, [(50, 20), (100, 20)])
        filter_obj.eventFilter(btn, ev_end)
        btn.event(ev_end)

        # 4. Синтетический MouseButtonRelease
        ev_mouse = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(50, 20),
            QPointF(50, 20),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        suppressed_by_filter = filter_obj.eventFilter(btn, ev_mouse)
        assert suppressed_by_filter is True

        # Кнопка ни разу не вызывалась
        assert len(triggered_calls) == 0
        assert btn.state == "idle"
    finally:
        btn.cleanup()


# =============================================================================
# 3. Интеграция свайпа в DeckGrid и подавление кликов
# =============================================================================

@pytest.mark.unit
def test_deck_grid_swipe_left_triggers_page_signal_and_suppresses_buttons(qapp):
    """
    Свайп влево по сетке DeckGrid:
    - Распознается детектором свайпа (DeckGrid.swipe_left).
    - Сбрасывает плитку кнопки при смещении |dx| >= 20 px.
    - Подавляет синтетический клик мыши после свайпа.
    """
    grid = DeckGrid()
    page_cfg = DeckPageConfig(
        id="page_test",
        name="Test Page",
        title="Test Page",
        grid_rows=2,
        grid_cols=5,
        buttons=[
            DeckButtonConfig(
                id=f"btn_{i}",
                title=f"Btn {i}",
                icon="🔷",
                action=DeckActionConfig(action_type="hotkey", params={"keys": ["a"]}),
            )
            for i in range(10)
        ],
    )
    grid.load_page(page_cfg)

    swipe_left_calls = []
    grid.swipe_left.connect(lambda: swipe_left_calls.append(True))

    button_triggered_calls = []
    grid.button_triggered.connect(lambda cfg: button_triggered_calls.append(cfg))

    btn0 = grid.get_button("btn_0")
    assert btn0 is not None

    try:
        # 1. Начало жеста на первой кнопке
        ev_press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(50, 50),
            QPointF(50, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        grid.swipe_detector.process_event(btn0, ev_press)
        btn0.mousePressEvent(ev_press)
        assert btn0.state == "pressed"

        # 2. Смещение влево на 75 px (|dx| = 75 >= 60, |dx| > 1.5*|dy|, dt <= 600 ms)
        ev_move = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(-25, 50),
            QPointF(-25, 50),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        consumed_move = grid.swipe_detector.process_event(btn0, ev_move)
        assert consumed_move is True
        assert len(swipe_left_calls) == 1
        assert grid.swipe_detector.suppress_mouse_release is True

        # Кнопка сброшена в idle
        assert btn0.state == "idle"
        assert btn0.is_pressed is False

        # 3. Отпускание мыши / пальца -> поглощается детектором
        ev_release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(-25, 50),
            QPointF(-25, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        consumed_release = grid.swipe_detector.process_event(btn0, ev_release)
        assert consumed_release is True

        # Сигнал срабатывания кнопки не был отправлен
        assert len(button_triggered_calls) == 0
        assert btn0.state == "idle"
    finally:
        grid.cleanup()


@pytest.mark.unit
def test_deck_grid_swipe_right_triggers_swipe_right_signal(qapp):
    """
    Свайп вправо по сетке DeckGrid:
    - Распознается детектором свайпа (DeckGrid.swipe_right).
    - Сбрасывает состояние кнопки и подавляет клик.
    """
    grid = DeckGrid()
    page_cfg = DeckPageConfig(
        id="page_test2",
        name="Test Page 2",
        title="Test Page 2",
        grid_rows=2,
        grid_cols=5,
        buttons=[
            DeckButtonConfig(
                id=f"btn_{i}",
                title=f"Btn {i}",
                icon="🔷",
                action=DeckActionConfig(action_type="hotkey", params={"keys": ["a"]}),
            )
            for i in range(10)
        ],
    )
    grid.load_page(page_cfg)

    swipe_right_calls = []
    grid.swipe_right.connect(lambda: swipe_right_calls.append(True))

    btn1 = grid.get_button("btn_1")
    assert btn1 is not None

    try:
        # Нажатие на кнопку
        ev_press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(50, 50),
            QPointF(50, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        grid.swipe_detector.process_event(btn1, ev_press)
        btn1.mousePressEvent(ev_press)
        assert btn1.state == "pressed"

        # Смещение вправо на 80 px (dx = +80, dy = 0)
        ev_move = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(130, 50),
            QPointF(130, 50),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        consumed_move = grid.swipe_detector.process_event(btn1, ev_move)
        assert consumed_move is True
        assert len(swipe_right_calls) == 1
        assert btn1.state == "idle"

        # Отпускание поглощается
        ev_release = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(130, 50),
            QPointF(130, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        consumed_release = grid.swipe_detector.process_event(btn1, ev_release)
        assert consumed_release is True
    finally:
        grid.cleanup()


# =============================================================================
# 4. Пагинация DeckView при свайпах влево/вправо и по сетке
# =============================================================================

@pytest.mark.unit
def test_deck_view_swipe_left_switches_to_next_page(qapp):
    """
    Свайп влево на интерактивной панели переключает DeckView на следующую страницу,
    обновляет активную точку DotPagingWidget и эмитирует bus.deck_page_changed.
    """
    view = DeckView(config_path="config/deck_config.json")
    emitted_pages = []
    bus.deck_page_changed.connect(lambda p: emitted_pages.append(p))

    try:
        assert view.active_page_id == "default"
        assert view.get_current_page_index() == 0
        assert view.interactive_panel.get_current_page() == 0

        # Эмулируем свайп влево на интерактивной панели
        view.interactive_panel.swipe_left.emit()

        # Страница должна переключиться на 'grid4x6' (индекс 1)
        assert view.active_page_id == "grid4x6"
        assert view.get_current_page_index() == 1
        assert view.interactive_panel.get_current_page() == 1
        assert "grid4x6" in emitted_pages
    finally:
        view.cleanup()


@pytest.mark.unit
def test_deck_view_swipe_right_switches_to_prev_page(qapp):
    """
    Свайп вправо возвращает DeckView на предыдущую страницу,
    синхронизирует точку DotPagingWidget и эмитирует bus.deck_page_changed.
    """
    view = DeckView(config_path="config/deck_config.json")
    emitted_pages = []
    bus.deck_page_changed.connect(lambda p: emitted_pages.append(p))

    try:
        # Устанавливаем страницу 1 ('grid4x6')
        view.set_active_page("grid4x6")
        assert view.active_page_id == "grid4x6"
        assert view.interactive_panel.get_current_page() == 1

        emitted_pages.clear()

        # Эмулируем свайп вправо на панели
        view.interactive_panel.swipe_right.emit()

        # Должен произойти возврат на 'default' (индекс 0)
        assert view.active_page_id == "default"
        assert view.get_current_page_index() == 0
        assert view.interactive_panel.get_current_page() == 0
        assert "default" in emitted_pages
    finally:
        view.cleanup()


@pytest.mark.unit
def test_deck_view_swipe_from_grid_triggers_paging(qapp):
    """
    Свайп по области кнопок DeckGrid (swipe_left / swipe_right)
    также корректно переключает страницы макро-панели.
    """
    view = DeckView(config_path="config/deck_config.json")
    try:
        assert view.active_page_id == "default"

        # Свайп влево по сетке
        view.grid.swipe_left.emit()
        assert view.active_page_id == "grid4x6"
        assert view.interactive_panel.get_current_page() == 1

        # Свайп вправо по сетке
        view.grid.swipe_right.emit()
        assert view.active_page_id == "default"
        assert view.interactive_panel.get_current_page() == 0
    finally:
        view.cleanup()


@pytest.mark.unit
def test_deck_view_swipe_boundary_conditions(qapp):
    """
    На первой странице свайп вправо не должен вызывать ошибок или смещения.
    На последней странице свайп влево не должен выходить за пределы списка.
    """
    view = DeckView(config_path="config/deck_config.json")
    try:
        # 1. Мы на первой странице (индекс 0). Свайп вправо -> остаемся на индексе 0
        assert view.get_current_page_index() == 0
        view.interactive_panel.swipe_right.emit()
        assert view.active_page_id == "default"
        assert view.get_current_page_index() == 0
        assert view.interactive_panel.get_current_page() == 0

        # 2. Переходим на последнюю страницу (индекс 1)
        view.interactive_panel.swipe_left.emit()
        assert view.active_page_id == "grid4x6"
        assert view.get_current_page_index() == 1

        # 3. Свайп влево на последней странице -> остаемся на ней
        view.interactive_panel.swipe_left.emit()
        assert view.active_page_id == "grid4x6"
        assert view.get_current_page_index() == 1
    finally:
        view.cleanup()


# =============================================================================
# 5. Синхронизация DotPagingWidget и кинетическая анимация
# =============================================================================

@pytest.mark.unit
def test_deck_view_dot_paging_click_synchronization(qapp):
    """
    Нажатие на точку в DotPagingWidget (сигнал page_selected)
    переключает страницу в DeckView.
    """
    view = DeckView(config_path="config/deck_config.json")
    try:
        assert view.active_page_id == "default"

        # Клик по точке 1
        dots = view.interactive_panel.center_section.dots
        dots.page_selected.emit(1)

        assert view.active_page_id == "grid4x6"
        assert view.interactive_panel.get_current_page() == 1
    finally:
        view.cleanup()


@pytest.mark.unit
def test_deck_view_external_deck_page_changed_eventbus_sync(qapp):
    """
    Внешний сигнал bus.deck_page_changed обновляет активную страницу в DeckView
    и индикатор в DotPagingWidget, не вызывая зацикливания.
    """
    view = DeckView(config_path="config/deck_config.json")
    try:
        assert view.active_page_id == "default"

        # Внешний эмит по ID
        bus.deck_page_changed.emit("grid4x6")
        assert view.active_page_id == "grid4x6"
        assert view.interactive_panel.get_current_page() == 1

        # Внешний эмит по fallback-индексу 'page_0'
        bus.deck_page_changed.emit("page_0")
        assert view.active_page_id == "default"
        assert view.interactive_panel.get_current_page() == 0
    finally:
        view.cleanup()


@pytest.mark.unit
def test_dot_paging_widget_kinetic_animation(qapp):
    """
    Проверка механизма кинетической анимации точек:
    - Запуск QVariantAnimation при animated=True.
    - Корректная остановка анимации при cleanup().
    """
    dots = DotPagingWidget(page_count=3, current_page=0)
    try:
        assert dots.current_page() == 0
        assert dots._anim_pos == 0.0

        # Переключение с анимацией
        dots.set_current_page(2, animated=True)
        assert dots.current_page() == 2
        # Анимация должна быть запущена
        assert dots._anim.state() == QVariantAnimation.State.Running

        # Принудительная остановка / завершение
        dots._anim.stop()
        dots._anim_pos = 2.0
        dots.update()
        assert dots._anim_pos == 2.0
    finally:
        dots.cleanup()
        assert dots._anim.state() != QVariantAnimation.State.Running
