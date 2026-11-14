"""
Модульное тестирование распознавания тач-жестов и защиты от коллизий (Спринт 6, шаг 6.1).
Комплексное тестирование вертикального двухпальцевого свайпа экранов и защиты от ложных срабатываний:
- Двухпальцевый вертикальный свайп вверх (+1) и вниз (-1) (len(points) == 2, |avg_dy| >= 70px, dt <= 500ms, dy0 * dy1 > 0).
- Отклонение слишком медленных свайпов (> 500ms).
- Отклонение свайпов с недостаточной амплитудой (< 70px).
- Отклонение щипка / противоположного движения (dy0 * dy1 < 0).
- Подавление синтетического клика мыши после двухпальцевого свайпа.
- Отклонение горизонтальных и диагональных жестов (|avg_dy| <= 1.3 * |avg_dx|).
- Касания одним пальцем (включая сайдбар) не переключают вкладки и свободно передаются UI-кнопкам.
"""
import time
import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt, QPointF, QEvent, QObject
from PySide6.QtWidgets import QPushButton, QWidget
from PySide6.QtGui import QTouchEvent, QEventPoint

from core.event_bus import bus
from core.focus_guardian import FocusGuardian
from core.touch_filter import TouchCursorFilter
from core.config import AppConfig
from ui.main_window import MainWindow


def create_touch_event(etype, points_coords):
    """
    Вспомогательная функция для создания синтетического QTouchEvent.
    points_coords: список кортежей (x, y) для каждой точки касания.
    """
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


@pytest.mark.unit
def test_two_finger_swipe_up_switches_next_screen(qapp):
    """Двухпальцевый свайп вверх (avg_dy <= -70px, dt <= 500ms, dy0*dy1 > 0) переключает на следующий экран (+1)."""
    filter_obj = TouchCursorFilter()
    dummy_widget = QWidget()
    filter_obj._current_tab = 0

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    # TouchBegin: 2 пальца в точках Y=400
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(300, 400), (500, 400)])
    filter_obj.eventFilter(dummy_widget, ev_begin)

    # TouchUpdate: смещение вверх на 80px (dy0 = -80, dy1 = -80, avg_dy = -80 <= -70)
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(300, 320), (500, 320)])
    consumed = filter_obj.eventFilter(dummy_widget, ev_update)

    assert consumed is True
    assert tabs_received == [1]
    assert filter_obj._current_tab == 1
    assert filter_obj._suppress_mouse_release is True

    # TouchEnd: завершение жеста
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(300, 320), (500, 320)])
    consumed_end = filter_obj.eventFilter(dummy_widget, ev_end)
    assert consumed_end is True


@pytest.mark.unit
def test_two_finger_swipe_down_switches_prev_screen(qapp):
    """Двухпальцевый свайп вниз (avg_dy >= +70px, dt <= 500ms, dy0*dy1 > 0) переключает на предыдущий экран (-1)."""
    filter_obj = TouchCursorFilter()
    dummy_widget = QWidget()
    filter_obj._current_tab = 2

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    # TouchBegin: 2 пальца в точках Y=200
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(300, 200), (500, 200)])
    filter_obj.eventFilter(dummy_widget, ev_begin)

    # TouchUpdate: смещение вниз на 75px (dy0 = +75, dy1 = +75, avg_dy = +75 >= +70)
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(300, 275), (500, 275)])
    consumed = filter_obj.eventFilter(dummy_widget, ev_update)

    assert consumed is True
    assert tabs_received == [1]
    assert filter_obj._current_tab == 1
    assert filter_obj._suppress_mouse_release is True

    # TouchEnd: завершение жеста
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(300, 275), (500, 275)])
    consumed_end = filter_obj.eventFilter(dummy_widget, ev_end)
    assert consumed_end is True


@pytest.mark.unit
def test_two_finger_swipe_too_slow_no_trigger(qapp):
    """Слишком медленный двухпальцевый свайп (dt > 500ms) не переключает экран."""
    filter_obj = TouchCursorFilter()
    dummy_widget = QWidget()
    filter_obj._current_tab = 0

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    # TouchBegin: 2 пальца
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(300, 400), (500, 400)])
    filter_obj.eventFilter(dummy_widget, ev_begin)

    # Искусственно состариваем время начала жеста (>500 мс)
    filter_obj._two_finger_start_time = time.monotonic() - 0.550

    # TouchUpdate: dy = -80px, но dt=550ms > 500ms
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(300, 320), (500, 320)])
    filter_obj.eventFilter(dummy_widget, ev_update)

    assert len(tabs_received) == 0
    assert filter_obj._two_finger_swipe_triggered is False
    assert filter_obj._suppress_mouse_release is False

    # TouchEnd: отрыв пальцев не должен приводить к ложному срабатыванию
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(300, 320), (500, 320)])
    filter_obj.eventFilter(dummy_widget, ev_end)
    assert len(tabs_received) == 0


@pytest.mark.unit
def test_two_finger_swipe_insufficient_dy_no_trigger(qapp):
    """Двухпальцевый свайп с недостаточным смещением (|avg_dy| < 70px) не переключает экран."""
    filter_obj = TouchCursorFilter()
    dummy_widget = QWidget()
    filter_obj._current_tab = 0

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    # TouchBegin: 2 пальца
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(300, 400), (500, 400)])
    filter_obj.eventFilter(dummy_widget, ev_begin)

    # TouchUpdate: dy = -50px < 70px
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(300, 350), (500, 350)])
    filter_obj.eventFilter(dummy_widget, ev_update)

    assert len(tabs_received) == 0
    assert filter_obj._two_finger_swipe_triggered is False
    assert filter_obj._suppress_mouse_release is False

    # TouchEnd: dy = -50px < 70px
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(300, 350), (500, 350)])
    filter_obj.eventFilter(dummy_widget, ev_end)
    assert len(tabs_received) == 0


@pytest.mark.unit
def test_two_finger_pinch_opposing_motion_no_trigger(qapp):
    """Щипок / противоположное движение пальцев по вертикали (dy0 * dy1 < 0) блокируется и не переключает экран."""
    filter_obj = TouchCursorFilter()
    dummy_widget = QWidget()
    filter_obj._current_tab = 0

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    # TouchBegin: 2 пальца в точках Y=200, Y=400
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(300, 200), (500, 400)])
    filter_obj.eventFilter(dummy_widget, ev_begin)

    # TouchUpdate: противоположное движение (палец 0 смещается вниз на +80, палец 1 вверх на -80: dy0*dy1 < 0)
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(300, 280), (500, 320)])
    filter_obj.eventFilter(dummy_widget, ev_update)

    assert len(tabs_received) == 0
    assert filter_obj._two_finger_swipe_triggered is False
    assert filter_obj._suppress_mouse_release is False

    # TouchEnd: завершение щипка
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(300, 280), (500, 320)])
    filter_obj.eventFilter(dummy_widget, ev_end)
    assert len(tabs_received) == 0


@pytest.mark.unit
def test_two_finger_swipe_suppresses_synthetic_mouse_click(qapp):
    """Успешный двухпальцевый свайп (>=70px) подавляет последующий MouseButtonRelease, исключая ложный клик."""
    filter_obj = TouchCursorFilter()
    btn = QPushButton("Test Button")
    clicks = []
    btn.clicked.connect(lambda: clicks.append(True))
    filter_obj._current_tab = 0

    # TouchBegin: 2 пальца
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(300, 400), (500, 400)])
    filter_obj.eventFilter(btn, ev_begin)

    # TouchUpdate: свайп вверх на 80px (успешный жест)
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(300, 320), (500, 320)])
    consumed_update = filter_obj.eventFilter(btn, ev_update)
    assert consumed_update is True
    assert filter_obj._suppress_mouse_release is True

    # TouchEnd: отрыв пальцев
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(300, 320), (500, 320)])
    consumed_end = filter_obj.eventFilter(btn, ev_end)
    assert consumed_end is True

    # Синтетический MouseButtonRelease от Windows/Qt после свайпа
    ev_release = QEvent(QEvent.Type.MouseButtonRelease)
    consumed_release = filter_obj.eventFilter(btn, ev_release)
    assert consumed_release is True  # Подавлен, кнопка под пальцем НЕ нажимается!
    assert filter_obj._suppress_mouse_release is False  # Одноразовый флаг сброшен

    # Последующий нормальный клик мыши НЕ должен подавляться
    ev_release_next = QEvent(QEvent.Type.MouseButtonRelease)
    consumed_next = filter_obj.eventFilter(btn, ev_release_next)
    assert consumed_next is False


@pytest.mark.unit
def test_two_finger_swipe_horizontal_diagonal_rejection(qapp):
    """Свайп с доминирующим или сопоставимым горизонтальным смещением (|avg_dy| <= 1.3 * |avg_dx|) блокируется."""
    filter_obj = TouchCursorFilter()
    dummy_widget = QWidget()
    filter_obj._current_tab = 0

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    # TouchBegin: 2 пальца
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(300, 200), (500, 200)])
    filter_obj.eventFilter(dummy_widget, ev_begin)

    # TouchUpdate: dy = -80, dx = +70 (|avg_dy|=80 <= 1.3*70 = 91)
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(370, 120), (570, 120)])
    filter_obj.eventFilter(dummy_widget, ev_update)

    assert len(tabs_received) == 0


@pytest.mark.unit
def test_two_finger_swipe_cyclic_switching(qapp):
    """Двухпальцевый свайп циклически меняет экраны: 0 -> 4 при свайпе вниз, 4 -> 0 при свайпе вверх."""
    filter_obj = TouchCursorFilter()
    dummy_widget = QWidget()
    filter_obj._current_tab = 0

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    # 1. Свайп вниз с 0-й вкладки -> переключение на 4-ю (0 - 1 = 4 по модулю 5)
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(300, 200), (500, 200)])
    filter_obj.eventFilter(dummy_widget, ev_begin)
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(300, 280), (500, 280)])
    filter_obj.eventFilter(dummy_widget, ev_update)
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(300, 280), (500, 280)])
    filter_obj.eventFilter(dummy_widget, ev_end)

    assert filter_obj._current_tab == 4
    assert tabs_received[-1] == 4

    # 2. Свайп вверх с 4-й вкладки -> переключение на 0-ю ((4 + 1) % 5 = 0)
    ev_begin2 = create_touch_event(QEvent.Type.TouchBegin, [(300, 400), (500, 400)])
    filter_obj.eventFilter(dummy_widget, ev_begin2)
    ev_update2 = create_touch_event(QEvent.Type.TouchUpdate, [(300, 320), (500, 320)])
    filter_obj.eventFilter(dummy_widget, ev_update2)
    ev_end2 = create_touch_event(QEvent.Type.TouchEnd, [(300, 320), (500, 320)])
    filter_obj.eventFilter(dummy_widget, ev_end2)

    assert filter_obj._current_tab == 0
    assert tabs_received[-1] == 0


@pytest.mark.unit
def test_single_touch_on_sidebar_passes_to_button_without_tab_switch(qapp):
    """Касание одним пальцем (включая сайдбар) не переключает вкладки и передается кнопке."""
    filter_obj = TouchCursorFilter()
    btn = QPushButton("Test")
    clicks = []
    btn.clicked.connect(lambda: clicks.append(True))

    tabs_received = []
    bus.tab_changed.connect(lambda idx: tabs_received.append(idx))

    # TouchBegin: 1 палец на сайдбаре (x=40, y=100)
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(40, 100)])
    consumed_begin = filter_obj.eventFilter(btn, ev_begin)
    assert consumed_begin is False  # Не поглощается фильтром

    # TouchUpdate: движение пальца на 50px вниз
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(40, 150)])
    consumed_update = filter_obj.eventFilter(btn, ev_update)
    assert consumed_update is False  # Не поглощается

    # TouchEnd: отрыв пальца
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(40, 150)])
    consumed_end = filter_obj.eventFilter(btn, ev_end)
    assert consumed_end is False  # Не поглощается
    assert len(tabs_received) == 0  # Свайп НЕ сработал, вкладки не переключались

    # Синтетический MouseButtonRelease после тапа
    ev_release = QEvent(QEvent.Type.MouseButtonRelease)
    consumed_release = filter_obj.eventFilter(btn, ev_release)
    assert consumed_release is False  # Клик мыши НЕ подавляется!


@pytest.mark.unit
def test_main_window_switch_tab_by_offset_cyclic(qapp):
    """Метод MainWindow.switch_tab_by_offset корректно циклически переключает вкладки (+1 / -1)."""
    win = MainWindow(AppConfig())
    total = win.workspace.count()
    assert total == 5

    # 0 -> +1 = 1
    win.switch_tab_by_offset(1)
    assert win.workspace.currentIndex() == 1

    # 1 -> -1 = 0
    win.switch_tab_by_offset(-1)
    assert win.workspace.currentIndex() == 0

    # 0 -> -1 = 4 (циклический переход на последнюю вкладку)
    win.switch_tab_by_offset(-1)
    assert win.workspace.currentIndex() == 4

    # 4 -> +1 = 0 (циклический переход на первую вкладку)
    win.switch_tab_by_offset(1)
    assert win.workspace.currentIndex() == 0

    win.close()
