"""
Модульные тесты Drag-and-Drop на холсте конфигуратора DuckDeck (Sprint 6.6).
Проверяют:
  - DragEnterEvent / DragLeaveEvent с переключением подсветки drag_hover.
  - DropEvent для действия из библиотеки (application/x-duckdeck-action).
  - DropEvent для обмена слотами (application/x-duckdeck-slot, swap).
  - DropEvent для копирования слота при зажатом Ctrl (copy).
  - Проброс сигналов DND через DeckCanvasWidget.
"""
import json
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from modules.deck.editor.dto import ActionItemDTO
from modules.deck.editor.widgets.grid_cell import EditorGridCell
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.editor.widgets.action_item import ActionItemWidget


def test_grid_cell_drag_enter_and_leave(qapp: QApplication) -> None:
    """Ячейка подсвечивается (drag_hover='true') при входе DND и сбрасывает при выходе."""
    cell = EditorGridCell(slot_index=0)

    # Неподдерживаемый MIME
    mime_invalid = QMimeData()
    mime_invalid.setText("plain text")
    evt_invalid = QDragEnterEvent(QPoint(10, 10), Qt.CopyAction, mime_invalid, Qt.LeftButton, Qt.NoModifier)
    cell.dragEnterEvent(evt_invalid)
    assert cell.property("drag_hover") in (None, "false")

    # Поддерживаемый MIME действия
    mime_action = QMimeData()
    mime_action.setData("application/x-duckdeck-action", b"{}")
    evt_action = QDragEnterEvent(QPoint(10, 10), Qt.CopyAction, mime_action, Qt.LeftButton, Qt.NoModifier)
    cell.dragEnterEvent(evt_action)
    assert cell.property("drag_hover") == "true"

    # DragLeaveEvent
    evt_leave = QDragLeaveEvent()
    cell.dragLeaveEvent(evt_leave)
    assert cell.property("drag_hover") == "false"


def test_grid_cell_drop_action_from_library(qapp: QApplication) -> None:
    """При сбросе действия из библиотеки ячейка эмиттирует action_dropped с распарсенным JSON payload."""
    cell = EditorGridCell(slot_index=2)
    emitted = []
    cell.action_dropped.connect(lambda slot, data: emitted.append((slot, data)))

    action_payload = {
        "id": "website",
        "title": "Open Web",
        "icon": "🌐",
        "category": "deck.categories.web",
    }
    mime = QMimeData()
    mime.setData("application/x-duckdeck-action", json.dumps(action_payload).encode("utf-8"))

    evt = QDropEvent(
        QPointF(10.0, 10.0),
        Qt.CopyAction,
        mime,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    cell.dropEvent(evt)

    assert len(emitted) == 1
    slot_idx, data = emitted[0]
    assert slot_idx == 2
    assert data["id"] == "website"
    assert data["title"] == "Open Web"
    assert cell.property("drag_hover") == "false"


def test_grid_cell_drop_slot_swap(qapp: QApplication) -> None:
    """При обычном сбросе слота (без Ctrl) ячейка эмиттирует slot_dropped с is_copy=False."""
    cell = EditorGridCell(slot_index=4)
    emitted = []
    cell.slot_dropped.connect(lambda src, dst, is_copy: emitted.append((src, dst, is_copy)))

    mime = QMimeData()
    mime.setData("application/x-duckdeck-slot", b"1")

    evt = QDropEvent(
        QPointF(10.0, 10.0),
        Qt.MoveAction,
        mime,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    cell.dropEvent(evt)

    assert emitted == [(1, 4, False)]
    assert cell.property("drag_hover") == "false"


def test_grid_cell_drop_slot_copy_with_ctrl(qapp: QApplication) -> None:
    """При сбросе слота с зажатым Ctrl ячейка эмиттирует slot_dropped с is_copy=True."""
    cell = EditorGridCell(slot_index=7)
    emitted = []
    cell.slot_dropped.connect(lambda src, dst, is_copy: emitted.append((src, dst, is_copy)))

    mime = QMimeData()
    mime.setData("application/x-duckdeck-slot", b"3")

    evt = QDropEvent(
        QPointF(10.0, 10.0),
        Qt.CopyAction,
        mime,
        Qt.LeftButton,
        Qt.ControlModifier,
    )
    cell.dropEvent(evt)

    assert emitted == [(3, 7, True)]
    assert cell.property("drag_hover") == "false"


def test_canvas_dnd_signal_forwarding(qapp: QApplication) -> None:
    """DeckCanvasWidget корректно агрегирует и пробрасывает сигналы action_dropped и slot_dropped со всех ячеек."""
    canvas = DeckCanvasWidget()

    actions_forwarded = []
    slots_forwarded = []
    canvas.action_dropped.connect(lambda s, d: actions_forwarded.append((s, d)))
    canvas.slot_dropped.connect(lambda s, d, c: slots_forwarded.append((s, d, c)))

    target_cell = canvas.get_cell(5)
    assert target_cell is not None

    # Эмитируем сигнал от ячейки 5
    target_cell.action_dropped.emit(5, {"id": "test_act"})
    assert actions_forwarded == [(5, {"id": "test_act"})]

    target_cell.slot_dropped.emit(0, 5, True)
    assert slots_forwarded == [(0, 5, True)]


def test_grid_cell_drop_action_malformed_payload_rejected(qapp: QApplication) -> None:
    """Некорректный action payload (не dict, пустой id или битый json) отклоняется без эмиссии сигнала."""
    cell = EditorGridCell(slot_index=1)
    emitted = []
    cell.action_dropped.connect(lambda slot, data: emitted.append((slot, data)))

    # 1. Примитив вместо dict (строка)
    mime_str = QMimeData()
    mime_str.setData("application/x-duckdeck-action", json.dumps("not a dict").encode("utf-8"))
    evt1 = QDropEvent(QPointF(10.0, 10.0), Qt.CopyAction, mime_str, Qt.LeftButton, Qt.NoModifier)
    cell.dropEvent(evt1)
    assert len(emitted) == 0
    assert evt1.isAccepted() is False

    # 2. Словарь без ключа 'id'
    mime_no_id = QMimeData()
    mime_no_id.setData("application/x-duckdeck-action", json.dumps({"title": "No ID"}).encode("utf-8"))
    evt2 = QDropEvent(QPointF(10.0, 10.0), Qt.CopyAction, mime_no_id, Qt.LeftButton, Qt.NoModifier)
    cell.dropEvent(evt2)
    assert len(emitted) == 0
    assert evt2.isAccepted() is False

    # 3. Битый JSON
    mime_bad_json = QMimeData()
    mime_bad_json.setData("application/x-duckdeck-action", b"invalid json{{{")
    evt3 = QDropEvent(QPointF(10.0, 10.0), Qt.CopyAction, mime_bad_json, Qt.LeftButton, Qt.NoModifier)
    cell.dropEvent(evt3)
    assert len(emitted) == 0
    assert evt3.isAccepted() is False


def test_grid_cell_drop_slot_self_drop_ignored(qapp: QApplication) -> None:
    """Сброс слота на самого себя (src == dst) отклоняется и не вызывает перестановок."""
    cell = EditorGridCell(slot_index=3)
    emitted = []
    cell.slot_dropped.connect(lambda src, dst, is_copy: emitted.append((src, dst, is_copy)))

    mime = QMimeData()
    mime.setData("application/x-duckdeck-slot", b"3")
    evt = QDropEvent(QPointF(10.0, 10.0), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    cell.dropEvent(evt)

    assert len(emitted) == 0
    assert evt.isAccepted() is False


def test_grid_cell_drop_slot_invalid_range_ignored(qapp: QApplication) -> None:
    """Сброс некорректного индекса слота (< 0 или >= 10) отклоняется."""
    cell = EditorGridCell(slot_index=2)
    emitted = []
    cell.slot_dropped.connect(lambda src, dst, is_copy: emitted.append((src, dst, is_copy)))

    # Отрицательный слот
    mime_neg = QMimeData()
    mime_neg.setData("application/x-duckdeck-slot", b"-1")
    evt1 = QDropEvent(QPointF(10.0, 10.0), Qt.MoveAction, mime_neg, Qt.LeftButton, Qt.NoModifier)
    cell.dropEvent(evt1)
    assert len(emitted) == 0
    assert evt1.isAccepted() is False

    # Слот вне диапазона сетки (например 99)
    mime_oob = QMimeData()
    mime_oob.setData("application/x-duckdeck-slot", b"99")
    evt2 = QDropEvent(QPointF(10.0, 10.0), Qt.MoveAction, mime_oob, Qt.LeftButton, Qt.NoModifier)
    cell.dropEvent(evt2)
    assert len(emitted) == 0
    assert evt2.isAccepted() is False

    # Нечисловые данные
    mime_nan = QMimeData()
    mime_nan.setData("application/x-duckdeck-slot", b"invalid_slot")
    evt3 = QDropEvent(QPointF(10.0, 10.0), Qt.MoveAction, mime_nan, Qt.LeftButton, Qt.NoModifier)
    cell.dropEvent(evt3)
    assert len(emitted) == 0
    assert evt3.isAccepted() is False


def test_action_item_widget_drag_payload_has_category_id(qapp: QApplication) -> None:
    """
    Проверяет, что при инициализации DND в ActionItemWidget:
    - свойство category_id возвращается корректно из ActionItemDTO;
    - mouseMoveEvent не падает с AttributeError: 'ActionItemDTO' object has no attribute 'category_id'.
    """
    from unittest.mock import patch
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QEvent

    item_dto = ActionItemDTO(
        id="nav_next_page",
        title_key="deck.editor.presets.nav_next_page.title",
        category_key="deck.editor.categories.navigation",
        icon="▶",
    )
    assert item_dto.category_id == "navigation"

    widget = ActionItemWidget(item_dto=item_dto)
    widget._drag_start_pos = QPoint(10, 10)

    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(50.0, 50.0),
        QPointF(50.0, 50.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    with patch("PySide6.QtGui.QDrag.exec", return_value=Qt.DropAction.CopyAction):
        widget.mouseMoveEvent(move_event)

