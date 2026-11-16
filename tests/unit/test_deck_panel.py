"""
Тестирование интерактивной сенсорной панели DeckInteractivePanel (Спринт 6, Этап 3).
Проверка:
  - Шаг 3.1: Кинематический детектор 1-пальцевого горизонтального свайпа:
      * dt <= 600 ms
      * |dx| >= 60 px
      * |dx| > 1.5 * |dy| (угловой фильтр доминирования оси)
  - Изоляция от 2-пальцевого свайпа TouchCursorFilter.
  - Подавление синтетического клика мыши после успешного свайпа.
  - Геометрия 920x216 px и инвариант Stealth Focus (Qt.NoFocus).
  - Компоненты: DotPagingWidget, DeckCenterSection, DeckLeftSection, DeckRightSection.
"""
import time
import pytest
from unittest.mock import MagicMock

from PySide6.QtCore import Qt, QPointF, QEvent
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QTouchEvent, QEventPoint, QMouseEvent

from core.event_bus import bus
from modules.deck.widgets.interactive_panel import (
    DeckSwipeDetector,
    DotPagingWidget,
    DeckCenterSection,
    DeckLeftSection,
    DeckRightSection,
    DeckInteractivePanel,
)


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


# =============================================================================
# 1. Тестирование распознавания свайпа (Шаг 3.1)
# =============================================================================

@pytest.mark.unit
def test_swipe_left_recognition_dt_dx_thresholds(qapp):
    """
    1-пальцевый горизонтальный свайп влево:
    dx = -70 px (|dx| >= 60), dy = 0 (|dx| > 1.5*|dy|), dt <= 600 ms.
    Должен распознаваться как swipe 'left' и поглощать событие.
    """
    detector = DeckSwipeDetector()
    dummy = QWidget()

    detected_directions = []
    detector.swipe_detected.connect(lambda d: detected_directions.append(d))

    left_signals = []
    detector.swipe_left.connect(lambda: left_signals.append(True))

    # TouchBegin: 1 палец в точке (200, 100)
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(200, 100)])
    detector.process_event(dummy, ev_begin)
    assert detector.is_swipe_active is True
    assert detector.swipe_triggered is False

    # TouchUpdate: смещение влево на 70px (X=130, Y=100)
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(130, 100)])
    consumed = detector.process_event(dummy, ev_update)

    assert consumed is True
    assert detector.swipe_triggered is True
    assert detected_directions == ["left"]
    assert len(left_signals) == 1
    assert detector.suppress_mouse_release is True

    # TouchEnd: завершение тача поглощается
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(130, 100)])
    consumed_end = detector.process_event(dummy, ev_end)
    assert consumed_end is True

    # Синтетический MouseButtonRelease должен быть подавлен
    ev_mouse = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(130, 100),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    suppressed = detector.process_event(dummy, ev_mouse)
    assert suppressed is True
    assert detector.suppress_mouse_release is False


@pytest.mark.unit
def test_swipe_right_recognition(qapp):
    """
    1-пальцевый горизонтальный свайп вправо:
    dx = +75 px (|dx| >= 60), dy = 4 (|dx| > 1.5*4), dt <= 600 ms.
    Должен распознаваться как swipe 'right'.
    """
    detector = DeckSwipeDetector()
    dummy = QWidget()

    detected_directions = []
    detector.swipe_detected.connect(lambda d: detected_directions.append(d))

    right_signals = []
    detector.swipe_right.connect(lambda: right_signals.append(True))

    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(100, 100)])
    detector.process_event(dummy, ev_begin)

    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(175, 104)])
    consumed = detector.process_event(dummy, ev_update)

    assert consumed is True
    assert detector.swipe_triggered is True
    assert detected_directions == ["right"]
    assert len(right_signals) == 1


@pytest.mark.unit
def test_swipe_timeout_rejection_dt_over_600ms(qapp):
    """
    Свайп, длящийся дольше 600 мс (dt > 600 ms), должен отклоняться
    как медленное протягивание, а не динамический свайп.
    """
    detector = DeckSwipeDetector()
    dummy = QWidget()

    detected_directions = []
    detector.swipe_detected.connect(lambda d: detected_directions.append(d))

    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(200, 100)])
    detector.process_event(dummy, ev_begin)

    # Искусственно состариваем время начала жеста (>600 мс)
    detector._start_time = time.monotonic() - 0.650

    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(120, 100)])
    consumed = detector.process_event(dummy, ev_update)

    assert consumed is False
    assert detector.swipe_triggered is False
    assert len(detected_directions) == 0
    assert detector.is_swipe_active is False


@pytest.mark.unit
def test_swipe_insufficient_dx_rejection_under_60px(qapp):
    """
    Смещение меньше 60 px (|dx| < 60) не должно триггерить свайп
    (защита от дрожания пальца при обычном тапе).
    """
    detector = DeckSwipeDetector()
    dummy = QWidget()

    detected_directions = []
    detector.swipe_detected.connect(lambda d: detected_directions.append(d))

    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(200, 100)])
    detector.process_event(dummy, ev_begin)

    # Смещение всего 45 px (|dx| = 45 < 60)
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(155, 100)])
    detector.process_event(dummy, ev_update)

    assert detector.swipe_triggered is False
    assert len(detected_directions) == 0

    # TouchEnd также не должен триггерить свайп
    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(155, 100)])
    consumed_end = detector.process_event(dummy, ev_end)
    assert consumed_end is False
    assert len(detected_directions) == 0


@pytest.mark.unit
def test_swipe_axis_dominance_rejection_diagonal(qapp):
    """
    Угловой фильтр: если |dx| <= 1.5 * |dy|, жест отклоняется
    как диагональный или вертикальный.
    Пример: dx = 70, dy = 50 -> 70 <= 1.5 * 50 = 75 (отклонение).
    """
    detector = DeckSwipeDetector()
    dummy = QWidget()

    detected_directions = []
    detector.swipe_detected.connect(lambda d: detected_directions.append(d))

    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(200, 100)])
    detector.process_event(dummy, ev_begin)

    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(130, 150)])
    consumed = detector.process_event(dummy, ev_update)

    assert consumed is False
    assert detector.swipe_triggered is False
    assert len(detected_directions) == 0


@pytest.mark.unit
def test_swipe_axis_dominance_accepted_narrow_angle(qapp):
    """
    Угловой фильтр: если |dx| > 1.5 * |dy|, жест принимается.
    Пример: dx = 80, dy = 30 -> 80 > 1.5 * 30 = 45 (принятие).
    """
    detector = DeckSwipeDetector()
    dummy = QWidget()

    detected_directions = []
    detector.swipe_detected.connect(lambda d: detected_directions.append(d))

    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(200, 100)])
    detector.process_event(dummy, ev_begin)

    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(120, 130)])
    consumed = detector.process_event(dummy, ev_update)

    assert consumed is True
    assert detector.swipe_triggered is True
    assert detected_directions == ["left"]


@pytest.mark.unit
def test_two_finger_touch_isolated_and_not_intercepted(qapp):
    """
    2-пальцевые касания НЕ должны перехватываться детектором DuckDeck,
    чтобы гарантировать свободную работу глобального TouchCursorFilter.
    """
    detector = DeckSwipeDetector()
    dummy = QWidget()

    detected_directions = []
    detector.swipe_detected.connect(lambda d: detected_directions.append(d))

    # TouchBegin: 2 пальца
    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(200, 100), (300, 100)])
    consumed = detector.process_event(dummy, ev_begin)

    assert consumed is False
    assert detector.is_swipe_active is False
    assert len(detected_directions) == 0

    # TouchUpdate: 2 пальца
    ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(200, 180), (300, 180)])
    consumed_update = detector.process_event(dummy, ev_update)

    assert consumed_update is False
    assert detector.is_swipe_active is False
    assert len(detected_directions) == 0


@pytest.mark.unit
def test_flick_swipe_recognized_at_touch_end(qapp):
    """
    Быстрый жест без промежуточных TouchUpdate (резкий отрыв пальца):
    TouchBegin -> TouchEnd с dx = -70 px, dt <= 600 ms.
    Должен успешно распознаться на событии TouchEnd.
    """
    detector = DeckSwipeDetector()
    dummy = QWidget()

    detected_directions = []
    detector.swipe_detected.connect(lambda d: detected_directions.append(d))

    ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(200, 100)])
    detector.process_event(dummy, ev_begin)

    ev_end = create_touch_event(QEvent.Type.TouchEnd, [(130, 100)])
    consumed = detector.process_event(dummy, ev_end)

    assert consumed is True
    assert detected_directions == ["left"]
    assert detector.suppress_mouse_release is True


# =============================================================================
# 2. Тестирование центральной секции и интеграции свайпа
# =============================================================================

@pytest.mark.unit
def test_deck_center_section_swipe_and_clock(qapp):
    """
    Проверка работы DeckCenterSection:
    - Габариты: 360x216 px.
    - Часы и дата инициализированы.
    - Проксирование сигналов свайпа из зоны.
    """
    sec = DeckCenterSection()
    try:
        assert sec.width() == 360
        assert sec.height() == 216
        assert sec.focusPolicy() == Qt.NoFocus
        assert sec.lbl_clock.focusPolicy() == Qt.NoFocus
        assert sec.lbl_date.focusPolicy() == Qt.NoFocus

        # Часы содержат формат HH:mm (длина 5 символов)
        assert len(sec.lbl_clock.text()) == 5
        assert ":" in sec.lbl_clock.text()

        # Проверка свайпа через секцию
        received_swipes = []
        sec.swipe_detected.connect(lambda d: received_swipes.append(d))

        ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(200, 100)])
        sec.swipe_detector.process_event(sec, ev_begin)

        ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(120, 100)])
        sec.swipe_detector.process_event(sec, ev_update)

        assert received_swipes == ["left"]
    finally:
        sec.cleanup()


@pytest.mark.unit
def test_dot_paging_widget_navigation(qapp):
    """
    Проверка виджета точечной пагинации DotPagingWidget:
    - Переключение активной точки.
    - Эмиссия сигнала page_selected и шины bus.deck_page_changed.
    """
    dots = DotPagingWidget(page_count=3, current_page=0)
    assert dots.focusPolicy() == Qt.NoFocus
    assert dots.current_page() == 0

    page_selected_events = []
    dots.page_selected.connect(lambda idx: page_selected_events.append(idx))

    bus_events = []
    bus.deck_page_changed.connect(lambda name: bus_events.append(name))

    # Смена на страницу 2 программно
    dots.set_current_page(2)
    assert dots.current_page() == 2

    # Симуляция клика мышью по точке 1
    # total_width = 3 * 14 + 2 * 8 = 58 px.
    # Центр виджета при ширине dots.width():
    total_dots_width = 3 * 14 + 2 * 8
    start_x = (dots.width() - total_dots_width) // 2
    dot_1_x = start_x + 1 * (14 + 8) + 7  # Центр 1-й точки

    ev_click = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(dot_1_x, 12),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    dots.mouseReleaseEvent(ev_click)

    assert dots.current_page() == 1
    assert page_selected_events == [1]
    assert "page_1" in bus_events


# =============================================================================
# 3. Комплексное тестирование DeckInteractivePanel
# =============================================================================

@pytest.mark.unit
def test_deck_interactive_panel_full_layout_and_cleanup(qapp):
    """
    Проверка всей составной панели DeckInteractivePanel:
    - Общий размер: 920x216 px.
    - 3 секции: 280 + 360 + 280 = 920 px.
    - Qt.NoFocus на всех элементах.
    - Проксирование свайпа из center_section.
    - Безопасная очистка в cleanup().
    """
    panel = DeckInteractivePanel()
    try:
        assert panel.width() == 920
        assert panel.height() == 216
        assert panel.objectName() == "DeckInteractivePanel"
        assert panel.focusPolicy() == Qt.NoFocus

        assert panel.left_section.width() == 280
        assert panel.center_section.width() == 360
        assert panel.right_section.width() == 280

        # Проверка кнопок левой секции (NoFocus)
        assert panel.left_section.btn_prev.focusPolicy() == Qt.NoFocus
        assert panel.left_section.btn_play.focusPolicy() == Qt.NoFocus
        assert panel.left_section.btn_next.focusPolicy() == Qt.NoFocus

        # Проверка правой секции (NoFocus)
        assert panel.right_section.btn_settings.focusPolicy() == Qt.NoFocus

        # Проксирование свайпа
        panel_swipes = []
        panel.swipe_detected.connect(lambda d: panel_swipes.append(d))

        ev_begin = create_touch_event(QEvent.Type.TouchBegin, [(100, 100)])
        panel.center_section.swipe_detector.process_event(panel.center_section, ev_begin)

        ev_update = create_touch_event(QEvent.Type.TouchUpdate, [(180, 100)])
        panel.center_section.swipe_detector.process_event(panel.center_section, ev_update)

        assert panel_swipes == ["right"]

        # Проверка шины событий: NotificationTicker
        bus.deck_notification.emit("Тестовое уведомление")
        assert panel.right_section.lbl_ticker.text() == "Тестовое уведомление"

    finally:
        panel.cleanup()
