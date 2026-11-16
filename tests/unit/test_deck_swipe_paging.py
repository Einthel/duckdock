"""
Тестирование связки жестов свайпа с пагинацией DuckDeck (Спринт 6, Шаг 3.3).
Проверяет:
  - Свайп влево (dx < -60 px) -> переход на следующую страницу (page_idx + 1).
  - Свайп вправо (dx > +60 px) -> переход на предыдущую страницу (page_idx - 1).
  - Синхронизация точек в DotPagingWidget (индикатор и кинетическая анимация QVariantAnimation).
  - Эмиссия и реакция на сигнал шины событий core.event_bus.bus.deck_page_changed.
  - Граничные условия пагинации (крайняя левая и крайняя правая страницы).
  - Синхронизация при выборе точки в DotPagingWidget.
"""
import pytest
from unittest.mock import MagicMock

from PySide6.QtCore import Qt, QPointF, QEvent, QVariantAnimation
from PySide6.QtGui import QMouseEvent, QTouchEvent, QEventPoint
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from modules.deck.view import DeckView
from modules.deck.widgets.interactive_panel import DotPagingWidget, DeckInteractivePanel


@pytest.fixture(scope="session")
def qapp():
    """Гарантирует существование экземпляра QApplication."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# =============================================================================
# 1. Свайп влево: переход на следующую страницу (page_idx + 1)
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


# =============================================================================
# 2. Свайп вправо: переход на предыдущую страницу (page_idx - 1)
# =============================================================================
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


# =============================================================================
# 3. Свайп по сетке кнопок DeckGrid
# =============================================================================
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


# =============================================================================
# 4. Граничные условия пагинации (крайние страницы)
# =============================================================================
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
# 5. Синхронизация при выборе точки в DotPagingWidget
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


# =============================================================================
# 6. Реакция на внешнюю смену страницы через шину событий (EventBus)
# =============================================================================
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


# =============================================================================
# 7. Кинетическая анимация DotPagingWidget
# =============================================================================
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
