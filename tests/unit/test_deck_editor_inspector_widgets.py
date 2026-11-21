"""
Модульные тесты для шагов 4.1, 4.2 и 4.3 редактора DuckDeck:
- DTO структуры данных (dto.py)
- Стили и токены геометрии инспектора (styles.py)
- Плитка превью иконки (KeyPreviewTile)
- Кнопка интерактивного захвата хоткея (HotkeyCaptureButton)
"""
from __future__ import annotations

import os
from typing import Any

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from core.i18n import I18nManager, t
from modules.deck.editor.dto import (
    ButtonSlotDTO,
    TouchbarClockDTO,
    TouchbarMediaDTO,
    TouchbarTelemetryDTO,
)
from modules.deck.editor.styles import (
    BG_INSPECTOR,
    BG_PREVIEW_TILE,
    BTN_DELETE_HOVER,
    EDITOR_MAIN_QSS,
    FORM_LABEL_WIDTH,
    HOTKEY_CAPTURING_BORDER,
    ICON_BTN_SIZE,
    INPUT_HEIGHT,
    INSPECTOR_HEIGHT,
    PREVIEW_TILE_SIZE,
)
from modules.deck.editor.widgets.button_property_form import ButtonPropertyForm
from modules.deck.editor.widgets.hotkey_capture import HotkeyCaptureButton
from modules.deck.editor.widgets.key_preview_tile import KeyPreviewTile
from modules.deck.editor.widgets.touchbar_property_forms import (
    TouchbarClockForm,
    TouchbarMediaForm,
    TouchbarTelemetryForm,
)


@pytest.fixture
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ==============================================================================
# 1. Тесты DTO структур (Шаг 4.1 / dto.py)
# ==============================================================================
def test_button_slot_dto_defaults() -> None:
    """
    Проверка начальных значений и типов полей ButtonSlotDTO.
    """
    dto = ButtonSlotDTO(slot_index=3)
    assert dto.slot_index == 3
    assert dto.title == ""
    assert dto.icon == "🖲️"
    assert dto.category == "System: Hotkey"
    assert dto.action_type == "Hotkey"
    assert dto.hotkey == ""
    assert dto.font_size == 11
    assert dto.font_color == "#d4d4d8"


def test_touchbar_dtos_defaults() -> None:
    """
    Проверка моделей данных тачбара: Media, Clock, Telemetry.
    """
    media = TouchbarMediaDTO()
    assert media.player == "Default"
    assert media.marquee_enabled is True
    assert media.marquee_speed == 50

    clock = TouchbarClockDTO()
    assert clock.is_24h is True
    assert clock.show_date is True
    assert clock.swipe_sensitivity == 3

    telemetry = TouchbarTelemetryDTO()
    assert telemetry.show_cpu is True
    assert telemetry.show_gpu is True
    assert telemetry.refresh_interval_s == 2


# ==============================================================================
# 2. Тесты констант и стилей инспектора (Шаг 4.1 / styles.py)
# ==============================================================================
def test_styles_inspector_constants() -> None:
    """
    Проверка констант геометрии и токенов цветов инспектора.
    """
    assert INSPECTOR_HEIGHT == 220
    assert PREVIEW_TILE_SIZE == 84
    assert INPUT_HEIGHT == 30
    assert FORM_LABEL_WIDTH == 60
    assert ICON_BTN_SIZE == 18

    assert BG_INSPECTOR == "#18181b"
    assert BG_PREVIEW_TILE == "#222227"
    assert BTN_DELETE_HOVER == "#ef4444"
    assert HOTKEY_CAPTURING_BORDER == "#38bdf8"


def test_styles_qss_rules_presence() -> None:
    """
    Проверка наличия селекторов инспектора и виджетов в EDITOR_MAIN_QSS.
    """
    assert "KeyPropertyInspector" in EDITOR_MAIN_QSS
    assert "InspectorPlaceholder" in EDITOR_MAIN_QSS
    assert "InspectorCategoryLabel" in EDITOR_MAIN_QSS
    assert "InspectorDeleteButton" in EDITOR_MAIN_QSS
    assert "KeyPreviewTile" in EDITOR_MAIN_QSS
    assert "TileCornerButton" in EDITOR_MAIN_QSS
    assert "InspectorLineEdit" in EDITOR_MAIN_QSS
    assert "FontSettingButton" in EDITOR_MAIN_QSS
    assert "HotkeyCaptureButton" in EDITOR_MAIN_QSS
    assert 'capturing="true"' in EDITOR_MAIN_QSS


# ==============================================================================
# 3. Тесты KeyPreviewTile (Шаг 4.2 / widgets/key_preview_tile.py)
# ==============================================================================
def test_key_preview_tile_initialization(qapp: QApplication) -> None:
    """
    Проверка габаритов, геометрии и дочерних элементов плитки превью.
    """
    tile = KeyPreviewTile()
    assert tile.width() == 84
    assert tile.height() == 84
    assert tile.btn_add.width() == 18
    assert tile.btn_add.height() == 18
    assert tile.btn_menu.width() == 18
    assert tile.btn_menu.height() == 18
    assert tile.btn_add.text() == "+"
    assert tile.btn_menu.text() == "v"
    assert tile.get_icon() == "🖲️"


def test_key_preview_tile_tooltips_and_retranslate(qapp: QApplication) -> None:
    """
    Проверка локализации подсказок кнопок плитки превью и hot-reload при смене языка.
    """
    mgr = I18nManager()
    mgr.set_language("ru")
    tile = KeyPreviewTile()

    # Проверка на русском (по умолчанию)
    tile.retranslate_ui()
    assert tile.btn_add.toolTip() == t("deck.editor.inspector.tooltips.load_image")
    assert tile.btn_menu.toolTip() == t("deck.editor.inspector.tooltips.icon_options")
    assert tile.btn_add.toolTip() != ""

    # Переключение на английский
    mgr.set_language("en")
    tile.retranslate_ui()
    assert tile.btn_add.toolTip() == t("deck.editor.inspector.tooltips.load_image")
    assert tile.btn_menu.toolTip() == t("deck.editor.inspector.tooltips.icon_options")
    assert "Upload image" in tile.btn_add.toolTip()

    # Возврат на русский
    mgr.set_language("ru")
    tile.retranslate_ui()


def test_key_preview_tile_set_icon_text_and_pixmap(qapp: QApplication, tmp_path: Any) -> None:
    """
    Проверка установки строковой иконки (эмодзи) и растрового изображения.
    """
    tile = KeyPreviewTile()
    tile.set_icon("🚀")
    assert tile.get_icon() == "🚀"
    assert tile.lbl_icon.text() == "🚀"

    # Создание временного тестового PNG изображения
    img_path = str(tmp_path / "test_icon.png")
    pix = QPixmap(32, 32)
    pix.fill(Qt.blue)
    pix.save(img_path, "PNG")

    tile.set_icon(img_path)
    assert tile.get_icon() == img_path
    assert not tile.lbl_icon.pixmap().isNull()


def test_key_preview_tile_signals(qapp: QApplication) -> None:
    """
    Проверка сигналов клика по угловым кнопкам и по самой плитке.
    """
    tile = KeyPreviewTile()
    add_fired = False
    menu_fired = False
    tile_fired = False

    def on_add():
        nonlocal add_fired
        add_fired = True

    def on_menu():
        nonlocal menu_fired
        menu_fired = True

    def on_tile():
        nonlocal tile_fired
        tile_fired = True

    tile.add_icon_clicked.connect(on_add)
    tile.icon_menu_clicked.connect(on_menu)
    tile.tile_clicked.connect(on_tile)

    tile.btn_add.click()
    assert add_fired is True

    tile.btn_menu.click()
    assert menu_fired is True

    # Имитация клика мыши по плитке
    press_ev = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(20.0, 20.0),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    tile.mousePressEvent(press_ev)
    assert tile_fired is True


# ==============================================================================
# 4. Тесты HotkeyCaptureButton (Шаг 4.3 / widgets/hotkey_capture.py)
# ==============================================================================
def test_hotkey_capture_button_initialization(qapp: QApplication) -> None:
    """
    Проверка начального состояния, геометрии и текста HotkeyCaptureButton.
    """
    bus.language_changed.emit("ru")
    btn = HotkeyCaptureButton()
    assert btn.height() == 30
    assert btn.is_capturing() is False
    assert btn.get_hotkey() == ""
    assert t("deck.editor.inspector.hotkey.click_to_assign") in btn.text()
    assert "▾" in btn.text()


def test_hotkey_capture_button_start_and_cancel_capture(qapp: QApplication) -> None:
    """
    Проверка перехода в режим захвата и отмены по клику или клавише Escape.
    """
    bus.language_changed.emit("ru")
    btn = HotkeyCaptureButton()

    # Старт захвата по клику
    btn.click()
    assert btn.is_capturing() is True
    assert btn.property("capturing") == "true"
    assert btn.text() == t("deck.editor.inspector.hotkey.press_shortcut")

    # Повторный клик отменяет захват
    btn.click()
    assert btn.is_capturing() is False
    assert btn.property("capturing") == "false"
    assert t("deck.editor.inspector.hotkey.click_to_assign") in btn.text()

    # Старт и отмена через Escape
    btn.start_capture()
    esc_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    btn.keyPressEvent(esc_event)
    assert btn.is_capturing() is False
    assert btn.get_hotkey() == ""


def test_hotkey_capture_key_combination(qapp: QApplication) -> None:
    """
    Проверка захвата комбинации модификаторов и символа (Ctrl+Shift+D).
    """
    btn = HotkeyCaptureButton()
    captured_hotkey = ""

    def on_hotkey_changed(val: str) -> None:
        nonlocal captured_hotkey
        captured_hotkey = val

    btn.hotkey_changed.connect(on_hotkey_changed)

    btn.start_capture()
    # Одиночный модификатор не завершает захват
    ctrl_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Control, Qt.ControlModifier)
    btn.keyPressEvent(ctrl_event)
    assert btn.is_capturing() is True

    # Нажатие Ctrl+Shift+D
    event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key_D,
        Qt.ControlModifier | Qt.ShiftModifier,
        "D",
    )
    btn.keyPressEvent(event)

    assert btn.is_capturing() is False
    assert btn.get_hotkey() == "Ctrl+Shift+D"
    assert captured_hotkey == "Ctrl+Shift+D"
    assert "Ctrl+Shift+D" in btn.text()
    assert "▾" in btn.text()


def test_hotkey_capture_clear_by_backspace_or_delete(qapp: QApplication) -> None:
    """
    Проверка очистки назначенного хоткея по клавише Delete/Backspace.
    """
    btn = HotkeyCaptureButton()
    btn.set_hotkey("F11")
    assert btn.get_hotkey() == "F11"

    # Захват и нажатие Backspace
    btn.start_capture()
    backspace_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Backspace, Qt.NoModifier)
    btn.keyPressEvent(backspace_event)

    assert btn.is_capturing() is False
    assert btn.get_hotkey() == ""
    assert t("deck.editor.inspector.hotkey.click_to_assign") in btn.text()


def test_hotkey_capture_focus_out_cancels(qapp: QApplication) -> None:
    """
    Проверка отмены режима захвата при потере фокуса ввода.
    """
    btn = HotkeyCaptureButton()
    btn.set_hotkey("Ctrl+C")
    btn.start_capture()
    assert btn.is_capturing() is True

    focus_event = QFocusEvent(QFocusEvent.Type.FocusOut)
    btn.focusOutEvent(focus_event)

    assert btn.is_capturing() is False
    assert btn.get_hotkey() == "Ctrl+C"
    assert "Ctrl+C" in btn.text()


def test_hotkey_capture_retranslate_preserves_user_hotkey(qapp: QApplication) -> None:
    """
    In-place Retranslate Invariant: при переключении языка назначенный пользователем
    хоткей строго сохраняется, а плейсхолдер при пустом значении переводится.
    """
    mgr = I18nManager()
    mgr.set_language("ru")
    btn = HotkeyCaptureButton()

    # Пустой хоткей: переключаем ru -> en
    btn.retranslate_ui()
    assert "Нажмите для назначения" in btn.text()

    mgr.set_language("en")
    btn.retranslate_ui()
    assert "Click to assign" in btn.text()

    # Заданный хоткей: проверяем сохранение
    btn.set_hotkey("Alt+F4")
    assert "Alt+F4" in btn.text()

    mgr.set_language("ru")
    btn.retranslate_ui()
    assert "Alt+F4" in btn.text()

    mgr.set_language("en")
    btn.retranslate_ui()
    assert "Alt+F4" in btn.text()

    # Возврат на русский
    mgr.set_language("ru")
    btn.retranslate_ui()


# ==============================================================================
# 5. Тесты формы редактирования кнопки (Шаг 4.4 / button_property_form.py)
# ==============================================================================
def test_button_property_form_initialization(qapp: QApplication) -> None:
    """
    Проверка верстки ButtonPropertyForm: высота 220 px, наличие шапки с корзиной,
    превью-плитки и полей формы с пресетами действий.
    """
    mgr = I18nManager()
    mgr.set_language("ru")
    form = ButtonPropertyForm()

    assert form.height() == INSPECTOR_HEIGHT
    assert form.lbl_category.text() == "System: Hotkey"
    assert form.btn_delete.text() == "🗑️"
    assert form.btn_delete.toolTip() == "Очистить действие кнопки"

    # Проверка наличия элементов формы
    assert form.preview_tile is not None
    assert form.edit_title is not None
    assert form.combo_actions is not None
    assert form.btn_hotkey is not None
    assert form.btn_font.text() == "T ▾"

    # Пресеты в комбобоксе
    assert form.combo_actions.count() == 5
    assert form.combo_actions.itemData(0) == "preset_actions"
    assert form.combo_actions.itemData(1) == "hotkey"


def test_button_property_form_load_slot_data(qapp: QApplication) -> None:
    """
    Проверка метода load_slot_data(dto): заполнение полей с защитой blockSignals.
    """
    form = ButtonPropertyForm()
    signals_received: list[tuple[str, Any]] = []
    form.property_changed.connect(lambda name, val: signals_received.append((name, val)))

    dto = ButtonSlotDTO(
        slot_index=5,
        title="Mute Audio",
        icon="🔇",
        category="Media: Mute",
        action_type="media_control",
        hotkey="Ctrl+Shift+M",
    )

    form.load_slot_data(dto)

    # Во время load_slot_data сигналы должны быть заблокированы
    assert len(signals_received) == 0

    assert form.get_slot_index() == 5
    assert form.lbl_category.text() == "Media: Mute"
    assert form.edit_title.text() == "Mute Audio"
    assert form.preview_tile.get_icon() == "🔇"
    assert form.btn_hotkey.get_hotkey() == "Ctrl+Shift+M"
    assert form.combo_actions.currentData() == "media_control"


def test_button_property_form_signals(qapp: QApplication) -> None:
    """
    Проверка эмиссии сигналов property_changed и delete_requested.
    """
    form = ButtonPropertyForm()
    signals: list[tuple[str, Any]] = []
    form.property_changed.connect(lambda name, val: signals.append((name, val)))

    delete_fired = False

    def on_delete() -> None:
        nonlocal delete_fired
        delete_fired = True

    form.delete_requested.connect(on_delete)

    # 1. Изменение Title через textEdited
    form.edit_title.textEdited.emit("New Title")
    assert ("title", "New Title") in signals

    # 2. Выбор действия в комбобоксе
    form.combo_actions.setCurrentIndex(2)  # open_application
    assert ("action_type", "open_application") in signals

    # 3. Изменение хоткея
    form.btn_hotkey.hotkey_changed.emit("Ctrl+Alt+T")
    assert ("hotkey", "Ctrl+Alt+T") in signals

    # 4. Клик по корзине
    form.btn_delete.click()
    assert delete_fired is True


def test_button_property_form_retranslate_preserves_user_inputs(qapp: QApplication) -> None:
    """
    In-place Retranslate Invariant: при смене языка интерфейса введенный пользователем
    текст Title, назначенный хоткей и выбранный индекс комбобокса строго сохраняются.
    """
    mgr = I18nManager()
    mgr.set_language("ru")

    form = ButtonPropertyForm()
    form.edit_title.setText("Мой Макрос")
    form.btn_hotkey.set_hotkey("Ctrl+F12")
    form.combo_actions.setCurrentIndex(3)  # media_control

    assert form.lbl_title_field.text() == "Название:"
    assert form.lbl_actions_field.text() == "Действия:"
    assert form.lbl_hotkey_field.text() == "Хоткей:"
    assert "Управление медиа" in form.combo_actions.currentText()

    # Переключаем язык на английский
    mgr.set_language("en")
    form.retranslate_ui()

    assert form.lbl_title_field.text() == "Title:"
    assert form.lbl_actions_field.text() == "Actions:"
    assert form.lbl_hotkey_field.text() == "Hotkey:"
    assert form.btn_delete.toolTip() == "Clear button action"
    assert "Media Control" in form.combo_actions.currentText()
    assert form.combo_actions.currentIndex() == 3

    # Пользовательские значения строго сохранены
    assert form.edit_title.text() == "Мой Макрос"
    assert form.btn_hotkey.get_hotkey() == "Ctrl+F12"
    assert "Ctrl+F12" in form.btn_hotkey.text()

    # Возврат на русский
    mgr.set_language("ru")
    form.retranslate_ui()
    assert form.lbl_title_field.text() == "Название:"
    assert form.edit_title.text() == "Мой Макрос"
    assert form.btn_hotkey.get_hotkey() == "Ctrl+F12"


# ==============================================================================
# 6. Тесты форм секций тачбара (Шаг 4.5 / touchbar_property_forms.py)
# ==============================================================================
def test_touchbar_media_form_lifecycle_and_retranslate(qapp: QApplication) -> None:
    """
    Проверка TouchbarMediaForm: лимит 220 px, загрузка данных, сброс и сохранение
    пользовательских параметров при смене языка.
    """
    mgr = I18nManager()
    mgr.set_language("ru")

    form = TouchbarMediaForm()
    assert form.height() == INSPECTOR_HEIGHT
    assert form.lbl_header.text() == "Тачбар: Медиаплеер"
    assert form.btn_reset.toolTip() == "Сбросить настройки секции"

    # Загружаем кастомные данные
    dto = TouchbarMediaDTO(player="Spotify", marquee_enabled=False, marquee_speed=85)
    form.load_data(dto)

    assert form.combo_player.currentText() == "Spotify"
    assert form.chk_marquee.isChecked() is False
    assert form.slider_speed.value() == 85
    assert form.lbl_speed_val.text() == "85"

    # Перевод ru -> en с сохранением значений
    mgr.set_language("en")
    form.retranslate_ui()

    assert form.lbl_header.text() == "Touchbar: Media Player"
    assert form.btn_reset.toolTip() == "Reset section settings"
    assert form.lbl_player.text() == "Player:"
    assert form.chk_marquee.text() == "Marquee scrolling title"
    assert form.lbl_speed.text() == "Scroll speed:"

    # Пользовательские параметры неизменны
    assert form.combo_player.currentText() == "Spotify"
    assert form.chk_marquee.isChecked() is False
    assert form.slider_speed.value() == 85

    # Проверка сброса
    form.btn_reset.click()
    assert form.combo_player.currentText() == "Default"
    assert form.chk_marquee.isChecked() is True
    assert form.slider_speed.value() == 50


def test_touchbar_clock_form_lifecycle_and_retranslate(qapp: QApplication) -> None:
    """
    Проверка TouchbarClockForm: лимит 220 px, 24h/date чекбоксы, свайп и In-place Retranslate.
    """
    mgr = I18nManager()
    mgr.set_language("ru")

    form = TouchbarClockForm()
    assert form.height() == INSPECTOR_HEIGHT
    assert form.lbl_header.text() == "Тачбар: Часы и навигация"

    dto = TouchbarClockDTO(is_24h=False, show_date=False, swipe_sensitivity=7)
    form.load_data(dto)

    assert form.chk_24h.isChecked() is False
    assert form.chk_show_date.isChecked() is False
    assert form.slider_swipe.value() == 7
    assert form.lbl_swipe_val.text() == "7"

    # Перевод на английский
    mgr.set_language("en")
    form.retranslate_ui()

    assert form.lbl_header.text() == "Touchbar: Clock & Navigation"
    assert form.chk_24h.text() == "24-hour format"
    assert form.chk_show_date.text() == "Show date"
    assert form.lbl_swipe.text() == "Swipe sensitivity:"

    # Сохранение значений
    assert form.chk_24h.isChecked() is False
    assert form.chk_show_date.isChecked() is False
    assert form.slider_swipe.value() == 7

    # Сброс
    form.btn_reset.click()
    assert form.chk_24h.isChecked() is True
    assert form.chk_show_date.isChecked() is True
    assert form.slider_swipe.value() == 3


def test_touchbar_telemetry_form_lifecycle_and_retranslate(qapp: QApplication) -> None:
    """
    Проверка TouchbarTelemetryForm: мониторинг CPU/GPU, интервалы и оповещения.
    """
    mgr = I18nManager()
    mgr.set_language("ru")

    form = TouchbarTelemetryForm()
    assert form.height() == INSPECTOR_HEIGHT
    assert form.lbl_header.text() == "Тачбар: Системные датчики"

    dto = TouchbarTelemetryDTO(show_cpu=False, show_gpu=True, refresh_interval_s=5)
    form.load_data(dto)

    assert form.chk_cpu.isChecked() is False
    assert form.chk_gpu.isChecked() is True
    assert form.combo_refresh.currentData() == 5
    assert form.combo_refresh.currentText() == "5 сек"

    # Перевод на английский
    mgr.set_language("en")
    form.retranslate_ui()

    assert form.lbl_header.text() == "Touchbar: System Sensors"
    assert form.chk_cpu.text() == "Monitor CPU"
    assert form.chk_gpu.text() == "Monitor GPU"
    assert form.lbl_refresh.text() == "Refresh interval:"
    assert form.chk_overheat.text() == "Overheat alert notifications"
    assert form.combo_refresh.currentText() == "5 sec"
    assert form.combo_refresh.currentData() == 5

    # Сохранение значений
    assert form.chk_cpu.isChecked() is False
    assert form.chk_gpu.isChecked() is True

    # Сброс
    form.btn_reset.click()
    assert form.chk_cpu.isChecked() is True
    assert form.chk_gpu.isChecked() is True
    assert form.combo_refresh.currentData() == 2
    mgr.set_language("ru")

