"""
Комплексные модульные тесты инспектора свойств DuckDeck (KeyPropertyInspector)
и его интеграции с холстом в главном окне DuckEditorWindow (Шаг 4.8).
Проверяют:
- Начальное состояние Index 0 (локализованный плейсхолдер).
- Переключение на форму кнопки (Index 1) и заполнение полей из ButtonSlotDTO.
- Тест клика по корзине 🗑️: эмиссия slot_cleared и возврат на Index 0.
- Отображение и кликабельность превью-плитки KeyPreviewTile с тултипами.
- Цикл интерактивного захвата хоткея в HotkeyCaptureButton (вход, модификаторы, Escape, Backspace).
- Переключение на формы тачбара (Index 2..4: Media, Clock, Telemetry).
- Инвариант In-place Retranslate: сохранение пользовательского ввода (Title и Hotkey) при смене языка.
- Интеграционный мост холст <-> инспектор внутри DeckEditorWindow.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from core.i18n import I18nManager, t
from modules.deck.editor.dto import (
    ButtonSlotDTO,
    TouchbarClockDTO,
    TouchbarMediaDTO,
    TouchbarTelemetryDTO,
)
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.editor.widgets.hotkey_capture import HotkeyCaptureButton
from modules.deck.editor.widgets.key_preview_tile import KeyPreviewTile
from modules.deck.editor.widgets.property_inspector import KeyPropertyInspector
from modules.deck.editor.window import DeckEditorWindow


@pytest.fixture
def inspector_widget(qapp):
    """Фикстура изолированного создания KeyPropertyInspector с восстановлением языка."""
    initial_lang = I18nManager().current_language
    inspector = KeyPropertyInspector()
    inspector.show()
    qapp.processEvents()
    yield inspector
    inspector.close()
    inspector.deleteLater()
    qapp.processEvents()
    I18nManager().set_language(initial_lang, emit_signal=False)


@pytest.fixture
def editor_window(qapp, sample_two_page_deck_config_path):
    """Фикстура создания и гарантированного закрытия окна DeckEditorWindow."""
    initial_lang = I18nManager().current_language
    window = DeckEditorWindow(config_path=sample_two_page_deck_config_path)
    window._skip_close_dialog = True
    window.show()
    qapp.processEvents()
    yield window
    window._is_dirty = False
    window._undo_stack.setClean()
    window.close()
    window.deleteLater()
    qapp.processEvents()
    I18nManager().set_language(initial_lang, emit_signal=False)


def test_inspector_initial_placeholder(inspector_widget, qtbot):
    """
    Проверка начального состояния инспектора:
    - Активен Index 0 (QStackedWidget).
    - Текст плейсхолдера соответствует t('deck.editor.inspector.placeholder').
    - Слот и секция сброшены в None, режим 'placeholder'.
    """
    qtbot.addWidget(inspector_widget)
    assert inspector_widget.stack.currentIndex() == 0
    assert inspector_widget.current_slot_index is None
    assert inspector_widget.current_section_type is None
    assert inspector_widget.current_mode == "placeholder"
    assert inspector_widget.lbl_placeholder.text() == t("deck.editor.inspector.placeholder")


def test_inspector_load_button_form(inspector_widget, qtbot):
    """
    Проверка загрузки данных кнопки в форму:
    - Переключение на Index 1.
    - Поля формы корректно заполнены из DTO (Title, Category, Hotkey, Icon).
    """
    qtbot.addWidget(inspector_widget)
    dto = ButtonSlotDTO(
        slot_index=0,
        title="OBS Recording",
        icon="⏺️",
        category="Streaming",
        action_type="hotkey",
        hotkey="Ctrl+F9",
    )
    inspector_widget.load_button_slot(0, dto)

    assert inspector_widget.stack.currentIndex() == 1
    assert inspector_widget.current_slot_index == 0
    assert inspector_widget.current_mode == "button"
    assert inspector_widget.button_form.edit_title.text() == "OBS Recording"
    assert inspector_widget.button_form.btn_hotkey.get_hotkey() == "Ctrl+F9"
    assert inspector_widget.button_form.get_category() == "Streaming"
    assert inspector_widget.button_form.preview_tile.get_icon() == "⏺️"


def test_inspector_delete_button_flow(inspector_widget, qtbot):
    """
    Проверка удаления действия кнопкой корзины 🗑️:
    - Клик по корзине через qtbot.
    - Эмиссия сигнала slot_cleared(0).
    - Автоматический возврат на Index 0 (Placeholder).
    """
    qtbot.addWidget(inspector_widget)
    dto = ButtonSlotDTO(slot_index=0, title="Discord Mute", hotkey="Ctrl+Shift+M")
    inspector_widget.load_button_slot(0, dto)
    assert inspector_widget.stack.currentIndex() == 1

    with qtbot.waitSignal(inspector_widget.slot_cleared, timeout=1000) as blocker:
        qtbot.mouseClick(inspector_widget.button_form.btn_delete, Qt.LeftButton)

    assert blocker.args == [0]
    assert inspector_widget.stack.currentIndex() == 0
    assert inspector_widget.current_slot_index is None
    assert inspector_widget.current_mode == "placeholder"


def test_key_preview_tile_rendering(qtbot):
    """
    Проверка отображения иконки и кликабельности угловых кнопок '+' и 'v'
    плитки KeyPreviewTile с локализованными подсказками.
    """
    tile = KeyPreviewTile()
    qtbot.addWidget(tile)
    tile.show()

    # Начальная иконка
    assert tile.get_icon() == "🖲️"
    assert tile.lbl_icon.text() == "🖲️"

    # Смена иконки
    tile.set_icon("🚀")
    assert tile.get_icon() == "🚀"
    assert tile.lbl_icon.text() == "🚀"

    # Локализованные тултипы
    assert tile.btn_add.toolTip() == t("deck.editor.inspector.tooltips.load_image")
    assert tile.btn_menu.toolTip() == t("deck.editor.inspector.tooltips.icon_options")

    # Сигналы кликов
    with qtbot.waitSignal(tile.add_icon_clicked, timeout=1000):
        qtbot.mouseClick(tile.btn_add, Qt.LeftButton)

    with qtbot.waitSignal(tile.icon_menu_clicked, timeout=1000):
        qtbot.mouseClick(tile.btn_menu, Qt.LeftButton)

    with qtbot.waitSignal(tile.tile_clicked, timeout=1000):
        qtbot.mouseClick(tile, Qt.LeftButton)

    tile.close()
    tile.deleteLater()


def test_hotkey_capture_button_cycle(qtbot):
    """
    Проверка полного цикла работы кнопки захвата сочетаний клавиш HotkeyCaptureButton:
    - Начальное состояние кнопки.
    - Вход в режим захвата (изменение текста на 'Press shortcut...').
    - Игнорирование одиночных клавиш-модификаторов.
    - Формирование комбинации (Ctrl+Shift+G) и эмиссия hotkey_changed.
    - Отмена захвата по нажатию Escape.
    - Очистка назначенного хоткея по Backspace.
    """
    btn = HotkeyCaptureButton()
    qtbot.addWidget(btn)
    btn.show()

    # 1. Начальное состояние
    assert not btn.is_capturing()
    assert btn.get_hotkey() == ""
    assert btn.text() == f"{t('deck.editor.inspector.hotkey.click_to_assign')}  ▾"

    # 2. Клик для входа в режим захвата
    qtbot.mouseClick(btn, Qt.LeftButton)
    assert btn.is_capturing()
    assert btn.text() == t("deck.editor.inspector.hotkey.press_shortcut")

    # 3. Нажатие одиночного модификатора не должно завершать захват
    ev_ctrl = QKeyEvent(QEvent.KeyPress, Qt.Key_Control, Qt.ControlModifier)
    btn.keyPressEvent(ev_ctrl)
    assert btn.is_capturing()

    # 4. Отправка комбинации клавиш Ctrl+Shift+G
    with qtbot.waitSignal(btn.hotkey_changed, timeout=1000) as blocker:
        ev_combo = QKeyEvent(
            QEvent.KeyPress,
            Qt.Key_G,
            Qt.ControlModifier | Qt.ShiftModifier,
            "G",
        )
        btn.keyPressEvent(ev_combo)

    assert blocker.args == ["Ctrl+Shift+G"]
    assert not btn.is_capturing()
    assert btn.get_hotkey() == "Ctrl+Shift+G"
    assert btn.text() == "Ctrl+Shift+G  ▾"

    # 5. Проверка отмены захвата по Escape
    btn.start_capture()
    assert btn.is_capturing()
    ev_esc = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    btn.keyPressEvent(ev_esc)
    assert not btn.is_capturing()
    assert btn.get_hotkey() == "Ctrl+Shift+G"

    # 6. Проверка очистки хоткея по Backspace
    btn.start_capture()
    assert btn.is_capturing()
    with qtbot.waitSignal(btn.hotkey_changed, timeout=1000) as blocker:
        ev_bs = QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier)
        btn.keyPressEvent(ev_bs)

    assert blocker.args == [""]
    assert not btn.is_capturing()
    assert btn.get_hotkey() == ""
    assert btn.text() == f"{t('deck.editor.inspector.hotkey.click_to_assign')}  ▾"

    btn.close()
    btn.deleteLater()


def test_touchbar_forms_switching(inspector_widget, qtbot):
    """
    Проверка переключения стэка инспектора на формы секций тачбара (Index 2..4: Media, Clock, Telemetry).
    """
    qtbot.addWidget(inspector_widget)

    # 1. Media (Index 2)
    media_dto = TouchbarMediaDTO(player="Spotify", marquee_enabled=False, marquee_speed=80)
    inspector_widget.load_touchbar_section("media", media_dto)
    assert inspector_widget.stack.currentIndex() == 2
    assert inspector_widget.current_section_type == "media"
    assert inspector_widget.current_mode == "touchbar"
    assert inspector_widget.media_form.combo_player.currentText() == "Spotify"
    assert inspector_widget.media_form.chk_marquee.isChecked() is False
    assert inspector_widget.media_form.slider_speed.value() == 80

    # 2. Clock (Index 3)
    clock_dto = TouchbarClockDTO(is_24h=False, show_date=False, swipe_sensitivity=7)
    inspector_widget.load_touchbar_section("clock", clock_dto)
    assert inspector_widget.stack.currentIndex() == 3
    assert inspector_widget.current_section_type == "clock"
    assert inspector_widget.current_mode == "touchbar"
    assert inspector_widget.clock_form.chk_24h.isChecked() is False
    assert inspector_widget.clock_form.chk_show_date.isChecked() is False
    assert inspector_widget.clock_form.slider_swipe.value() == 7

    # 3. Telemetry (Index 4)
    telemetry_dto = TouchbarTelemetryDTO(show_cpu=True, show_gpu=False, refresh_interval_s=5)
    inspector_widget.load_touchbar_section("telemetry", telemetry_dto)
    assert inspector_widget.stack.currentIndex() == 4
    assert inspector_widget.current_section_type == "telemetry"
    assert inspector_widget.current_mode == "touchbar"
    assert inspector_widget.telemetry_form.chk_cpu.isChecked() is True
    assert inspector_widget.telemetry_form.chk_gpu.isChecked() is False
    assert inspector_widget.telemetry_form.combo_refresh.currentData() == 5

    # 4. Неизвестная секция -> возврат в плейсхолдер
    inspector_widget.load_touchbar_section("invalid_unknown")
    assert inspector_widget.stack.currentIndex() == 0
    assert inspector_widget.current_mode == "placeholder"


def test_inspector_retranslate_preserves_user_input(inspector_widget, qtbot):
    """
    Проверка In-place Retranslate Invariant:
    При смене языка текстовые метки форм обновляются по локали,
    а пользовательский ввод в edit_title и назначенный хоткей строго сохраняются.
    """
    qtbot.addWidget(inspector_widget)

    # Устанавливаем базовый язык English
    I18nManager().set_language("en", emit_signal=False)
    inspector_widget.retranslate_ui()

    dto = ButtonSlotDTO(slot_index=0, title="", hotkey="")
    inspector_widget.load_button_slot(0, dto)

    # Пользовательский ввод
    inspector_widget.button_form.edit_title.setText("Discord Mute")
    inspector_widget.button_form.btn_hotkey.set_hotkey("Ctrl+M")

    assert inspector_widget.button_form.lbl_title_field.text() == "Title:"
    assert inspector_widget.button_form.lbl_actions_field.text() == "Actions:"
    assert inspector_widget.button_form.lbl_hotkey_field.text() == "Hotkey:"
    assert inspector_widget.button_form.btn_delete.toolTip() == "Clear button action"

    # Меняем язык на русский
    I18nManager().set_language("ru", emit_signal=False)
    inspector_widget.retranslate_ui()

    assert inspector_widget.lbl_placeholder.text() == "Выберите кнопку для настройки действия."
    assert inspector_widget.button_form.lbl_title_field.text() == "Название:"
    assert inspector_widget.button_form.lbl_actions_field.text() == "Действия:"
    assert inspector_widget.button_form.lbl_hotkey_field.text() == "Хоткей:"
    assert inspector_widget.button_form.btn_delete.toolTip() == "Очистить действие кнопки"

    # Пользовательские значения строго сохранены
    assert inspector_widget.button_form.edit_title.text() == "Discord Mute"
    assert inspector_widget.button_form.btn_hotkey.get_hotkey() == "Ctrl+M"
    assert inspector_widget.button_form.btn_hotkey.text() == "Ctrl+M  ▾"

    # Меняем язык обратно на английский
    I18nManager().set_language("en", emit_signal=False)
    inspector_widget.retranslate_ui()

    assert inspector_widget.lbl_placeholder.text() == "Select a key to configure its action."
    assert inspector_widget.button_form.lbl_title_field.text() == "Title:"
    assert inspector_widget.button_form.lbl_actions_field.text() == "Actions:"
    assert inspector_widget.button_form.lbl_hotkey_field.text() == "Hotkey:"
    assert inspector_widget.button_form.btn_delete.toolTip() == "Clear button action"
    assert inspector_widget.button_form.edit_title.text() == "Discord Mute"
    assert inspector_widget.button_form.btn_hotkey.get_hotkey() == "Ctrl+M"
    assert inspector_widget.button_form.btn_hotkey.text() == "Ctrl+M  ▾"


def test_inspector_canvas_signal_bridge(editor_window, qtbot):
    """
    Сквозной тест монтирования KeyPropertyInspector и связывания сигналов в DeckEditorWindow:
    1. Начальное состояние окна: инспектор смонтирован, активен Index 0.
    2. Клик по кнопке [2] холста -> инспектор переключается на Index 1 (Button Form).
    3. Редактирование названия в инспекторе -> превью ячейки холста обновляется реактивно.
    4. Клик по секции тачбара 'media' -> инспектор переключается на Index 2 (Media Form).
    5. Клик в пустоту холста (сброс выделения) -> инспектор возвращается на Index 0 (Placeholder).
    6. Клик по кнопке [2], нажатие корзины 🗑️ -> ячейка очищается, выделение снимается, инспектор на Index 0.
    """
    qtbot.addWidget(editor_window)
    inspector = editor_window.inspector
    canvas = editor_window.canvas_widget

    assert isinstance(inspector, KeyPropertyInspector)
    assert isinstance(canvas, DeckCanvasWidget)

    # 1. Начальное состояние
    assert inspector.stack.currentIndex() == 0
    assert inspector.current_mode == "placeholder"

    # 2. Выбор кнопки [2] на холсте кликом мыши
    cell_2 = canvas.get_cell(2)
    assert cell_2 is not None
    qtbot.mouseClick(cell_2, Qt.LeftButton)

    assert inspector.stack.currentIndex() == 1
    assert inspector.current_slot_index == 2
    assert cell_2.is_selected() is True

    # 3. Редактирование названия в инспекторе
    inspector.button_form.edit_title.setText("Obs Record")
    inspector.button_form.edit_title.textEdited.emit("Obs Record")

    # Проверка обновления данных модели окна и превью ячейки
    assert editor_window._button_slots[2].title == "Obs Record"
    assert cell_2.lbl_title.text() == "Obs Record"
    assert cell_2.get_button_data()["title"] == "Obs Record"

    # 4. Выбор секции тачбара media
    sec_media = canvas.touchbar_strip.sec_media
    qtbot.mouseClick(sec_media, Qt.LeftButton)

    assert inspector.stack.currentIndex() == 2
    assert inspector.current_section_type == "media"

    # 5. Сброс выделения на холсте
    canvas.clear_selection()
    assert inspector.stack.currentIndex() == 0
    assert inspector.current_mode == "placeholder"

    # 6. Повторный выбор и очистка корзиной
    qtbot.mouseClick(cell_2, Qt.LeftButton)
    assert inspector.stack.currentIndex() == 1

    qtbot.mouseClick(inspector.button_form.btn_delete, Qt.LeftButton)

    # Проверка очистки ячейки и сброса выделения
    assert inspector.stack.currentIndex() == 0
    assert editor_window._button_slots[2].title == ""
    assert cell_2.lbl_title.text() == ""
    assert cell_2.is_selected() is False
    assert canvas.get_selected_target() is None
