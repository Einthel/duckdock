"""
Модульные тесты живых динамических тайлов DuckDeck (Live Status Tiles, Спринт 7.3).
Проверяют комбобокс status_source, бейджи статуса в EditorGridCell и DeckButtonWidget,
а также цветовые пороги телеметрии CPU/GPU в DeckView.
"""
import pytest
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from modules.deck.editor.widgets.button_property_form import (
    ButtonPropertyForm,
    STATUS_SOURCE_KEYS,
)
from modules.deck.editor.widgets.grid_cell import EditorGridCell
from modules.deck.models import (
    DeckActionConfig,
    DeckButtonConfig,
    DeckPageConfig,
)
from modules.deck.view import DeckView
from modules.deck.widgets.deck_button import DeckButtonWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_status_source_keys_in_property_form(qapp):
    """Проверка наличия всех источников статуса в комбобоксе формы инспектора."""
    form = ButtonPropertyForm()

    assert form.combo_status_source.count() == len(STATUS_SOURCE_KEYS)
    for i, key in enumerate(STATUS_SOURCE_KEYS):
        assert form.combo_status_source.itemData(i) == key

    received = []
    form.property_changed.connect(lambda k, v: received.append((k, v)))

    # Выбор cpu_temp
    idx_cpu = STATUS_SOURCE_KEYS.index("cpu_temp")
    form.combo_status_source.setCurrentIndex(idx_cpu)
    assert len(received) > 0
    assert ("status_source", "cpu_temp") in received


def test_editor_grid_cell_status_and_typography(qapp):
    """Проверка отображения бейджа статуса и типографики в EditorGridCell."""
    cell = EditorGridCell(slot_index=0)

    # По умолчанию бейдж скрыт
    assert cell.lbl_status.isHidden() is True

    # Обновление статуса
    cell.update_status("58°C", badge_color="#10b981")
    assert cell.lbl_status.isHidden() is False
    assert cell.lbl_status.text() == "58°C"
    assert "#10b981" in cell.lbl_status.styleSheet()

    # Скрытие статуса
    cell.update_status("")
    assert cell.lbl_status.isHidden() is True

    # Типографика
    cell.set_typography(font_size=15, font_color="#f59e0b", text_alignment="top", hide_title=True)
    assert cell.lbl_title.isHidden() is True
    assert "15px" in cell.lbl_title.styleSheet()
    assert "#f59e0b" in cell.lbl_title.styleSheet()

    data = cell.get_button_data()
    assert data["font_size"] == 15
    assert data["font_color"] == "#f59e0b"
    assert data["text_alignment"] == "top"
    assert data["hide_title"] is True


def test_deck_button_widget_status_badge_color(qapp):
    """Проверка обновления статуса с badge_color в DeckButtonWidget."""
    btn_config = DeckButtonConfig(
        id="btn_live",
        title="CPU Monitor",
        action=DeckActionConfig(action_type="hotkey"),
        icon="📊",
        status_source="cpu_temp",
    )
    btn = DeckButtonWidget(button_config=btn_config)

    # Проверка вызова update_status с разными цветами
    btn.update_status(status_text="52°C", badge_color="#10b981")
    assert btn.lbl_status.isHidden() is False
    assert btn.lbl_status.text() == "52°C"
    assert "#10b981" in btn.lbl_status.styleSheet()

    btn.update_status(status_text="⚠️ CPU: 78°C", badge_color="#ef4444")
    assert btn.lbl_status.text() == "⚠️ CPU: 78°C"
    assert "#ef4444" in btn.lbl_status.styleSheet()


def test_deck_view_sensors_updated_thresholds(qapp, monkeypatch):
    """Проверка реакции DeckView на sensors_updated с цветовыми градациями."""
    view = DeckView()

    # Настраиваем кнопки в сетке с источниками cpu_temp и gpu_temp
    btn_cpu = DeckButtonConfig(
        id="btn_cpu",
        slot_index=0,
        title="CPU",
        action=DeckActionConfig(action_type="hotkey"),
        status_source="cpu_temp",
    )
    btn_gpu = DeckButtonConfig(
        id="btn_gpu",
        slot_index=1,
        title="GPU",
        action=DeckActionConfig(action_type="hotkey"),
        status_source="gpu_temp",
    )

    page = DeckPageConfig(
        id="test_page",
        name="Test",
        buttons=[btn_cpu, btn_gpu],
    )
    view.grid.load_page(page)

    widget_cpu = view.grid.get_button("btn_cpu")
    widget_gpu = view.grid.get_button("btn_gpu")

    # 1. Холодный режим (< 60°C) -> изумрудный #10b981
    view._on_sensors_updated({"cpu_temp": 45.2, "gpu_temp": 55.0})
    assert widget_cpu.lbl_status.text() == "CPU: 45°C"
    assert "#10b981" in widget_cpu.lbl_status.styleSheet()
    assert widget_gpu.lbl_status.text() == "GPU: 55°C"
    assert "#10b981" in widget_gpu.lbl_status.styleSheet()

    # 2. Теплый режим (60..74°C) -> янтарный #f59e0b
    view._on_sensors_updated({"cpu_temp": 68.7, "gpu_temp": 71.0})
    assert widget_cpu.lbl_status.text() == "CPU: 69°C"
    assert "#f59e0b" in widget_cpu.lbl_status.styleSheet()
    assert widget_gpu.lbl_status.text() == "GPU: 71°C"
    assert "#f59e0b" in widget_gpu.lbl_status.styleSheet()

    # 3. Горячий режим (>= 75°C) -> рубиновый #ef4444 со значком ⚠️
    view._on_sensors_updated({"cpu_temp": 79.4, "gpu_temp": 82.1})
    assert widget_cpu.lbl_status.text() == "⚠️ CPU: 79°C"
    assert "#ef4444" in widget_cpu.lbl_status.styleSheet()
    assert widget_gpu.lbl_status.text() == "⚠️ GPU: 82°C"
    assert "#ef4444" in widget_gpu.lbl_status.styleSheet()

    # Проверка отписки в cleanup()
    view.cleanup()
    # После cleanup повторный сигнал не должен вызывать падений
    bus.sensors_updated.emit({"cpu_temp": 50.0, "gpu_temp": 50.0})
