"""
Модульные тесты верхней панели управления DuckDeck Editor (EditorHeaderBar).
Проверяют:
  - Инициализацию и геометрию EditorHeaderBar (фиксированная высота 52 px).
  - Наличие всех компонентов: селектор устройств, селектор профилей, сервисные кнопки.
  - Переключение устройств в DeviceComboBox и эмиссию device_changed.
  - Переключение профилей и эмиссию profile_changed.
  - Выбор пункта "+ New Profile..." с эмиссией create_profile_requested() и блокировкой смены активного индекса.
  - Клики по кнопкам тулбара и проверку сигнала action_clicked для всех 4 кнопок.
  - Интеграцию в DeckEditorWindow через set_header_bar.
  - Реактивный протокол Localization-First (test_header_bar_retranslate_ui):
    динамическое обновление названий и тултипов при вызове retranslate_ui()
    без сброса currentIndex.
"""
from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

from core.i18n import I18nManager, t
from modules.deck.editor.styles import HEADER_HEIGHT, ToolbarVLine
from modules.deck.editor.widgets.header_bar import (
    DEVICE_CLASSIC_3X5,
    DEVICE_TOUCH_2X5,
    PROFILE_DEFAULT_ID,
    PROFILE_NEW_ID,
    DeviceComboBox,
    EditorHeaderBar,
    HeaderIconButton,
    ProfileComboBox,
)
from modules.deck.editor.window import DeckEditorWindow


class QtBotFixture:
    """Хелпер имитации действий пользователя над виджетами Qt через QTest."""

    def __init__(self, qapp):
        self._qapp = qapp

    def mouseClick(
        self,
        widget: QWidget,
        button: Qt.MouseButton = Qt.LeftButton,
        modifier: Qt.KeyboardModifier = Qt.NoModifier,
        pos: Optional[QPoint] = None,
        delay: int = -1,
    ) -> None:
        """Имитирует клик мыши по виджету."""
        if pos is not None:
            QTest.mouseClick(widget, button, modifier, pos, delay)
        else:
            QTest.mouseClick(widget, button, modifier)
        self._qapp.processEvents()

    def keyClick(
        self,
        widget: QWidget,
        key: Qt.Key,
        modifier: Qt.KeyboardModifier = Qt.NoModifier,
        delay: int = -1,
    ) -> None:
        """Имитирует нажатие клавиши на клавиатуре."""
        QTest.keyClick(widget, key, modifier, delay)
        self._qapp.processEvents()

    def wait(self, ms: int = 50) -> None:
        """Приостанавливает выполнение на ms миллисекунд с обработкой событий Qt."""
        QTest.qWait(ms)
        self._qapp.processEvents()


@pytest.fixture
def qtbot(qapp):
    """Фикстура qtbot для имитации взаимодействия пользователя с UI."""
    return QtBotFixture(qapp)


@pytest.fixture
def header_bar(qapp):
    """Фикстура создания и безопасного удаления экземпляра EditorHeaderBar."""
    initial_lang = I18nManager().current_language
    bar = EditorHeaderBar()
    bar.show()
    qapp.processEvents()
    yield bar
    bar.close()
    bar.deleteLater()
    qapp.processEvents()
    I18nManager().set_language(initial_lang, emit_signal=False)


@pytest.fixture
def editor_window(qapp):
    """Фикстура для создания и закрытия DeckEditorWindow."""
    initial_lang = I18nManager().current_language
    win = DeckEditorWindow()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()
    I18nManager().set_language(initial_lang, emit_signal=False)


def test_header_bar_initialization(header_bar):
    """
    Проверка инициализации и геометрии EditorHeaderBar:
      - Экземпляр создан и является EditorHeaderBar.
      - Фиксированная высота равна 52 px (HEADER_HEIGHT).
      - Наличие селектора устройств (DeviceComboBox).
      - Наличие вертикального микро-разделителя (ToolbarVLine).
      - Наличие селектора профилей (ProfileComboBox).
      - Наличие 4 сервисных кнопок тулбара (HeaderIconButton):
        notifications, store, settings, account.
      - Начальные значения селекторов (индекс 0 по умолчанию).
    """
    assert header_bar is not None
    assert header_bar.height() == HEADER_HEIGHT
    assert header_bar.maximumHeight() == HEADER_HEIGHT
    assert header_bar.minimumHeight() == HEADER_HEIGHT

    # Селекторы
    assert isinstance(header_bar.device_combo, DeviceComboBox)
    assert isinstance(header_bar.v_line, ToolbarVLine)
    assert isinstance(header_bar.profile_combo, ProfileComboBox)

    # Кнопка сохранения
    assert hasattr(header_bar, "btn_save")
    assert header_bar.btn_save.objectName() == "btnSaveConfig"
    assert "💾" in header_bar.btn_save.text()
    assert isinstance(header_bar.v_line_save, ToolbarVLine)

    # Сервисные кнопки
    assert isinstance(header_bar.btn_notifications, HeaderIconButton)
    assert isinstance(header_bar.btn_store, HeaderIconButton)
    assert isinstance(header_bar.btn_settings, HeaderIconButton)
    assert isinstance(header_bar.btn_account, HeaderIconButton)

    assert header_bar.btn_notifications.action_id == "notifications"
    assert header_bar.btn_store.action_id == "store"
    assert header_bar.btn_settings.action_id == "settings"
    assert header_bar.btn_account.action_id == "account"

    # Начальные состояния
    assert header_bar.device_combo.currentIndex() == 0
    assert header_bar.device_combo.get_current_device_id() == DEVICE_TOUCH_2X5

    assert header_bar.profile_combo.currentIndex() == 0
    assert header_bar.profile_combo.get_current_profile_id() == PROFILE_DEFAULT_ID


def test_device_selector_signal(header_bar):
    """
    Проверка переключения устройств в DeviceComboBox:
      - Выбор устройства 'Classic Stream Deck (3x5)' эмитирует сигнал device_changed('classic_3x5').
      - Возврат на 'touch_2x5_strip' эмитирует device_changed('touch_2x5_strip').
      - Корректная работа вспомогательных методов get_current_device_id() и set_current_device().
    """
    received_devices: List[str] = []
    header_bar.device_changed.connect(received_devices.append)

    # Переключаем на второе устройство (classic_3x5)
    header_bar.device_combo.setCurrentIndex(1)
    assert len(received_devices) == 1
    assert received_devices[-1] == DEVICE_CLASSIC_3X5
    assert header_bar.device_combo.get_current_device_id() == DEVICE_CLASSIC_3X5

    # Переключаем программно через set_current_device
    ok = header_bar.device_combo.set_current_device(DEVICE_TOUCH_2X5)
    assert ok is True
    assert len(received_devices) == 2
    assert received_devices[-1] == DEVICE_TOUCH_2X5
    assert header_bar.device_combo.get_current_device_id() == DEVICE_TOUCH_2X5
    assert header_bar.device_combo.currentIndex() == 0


def test_profile_selector_change(header_bar):
    """
    Проверка обычного переключения профилей:
      - Выбор профиля эмитирует profile_changed с именем профиля.
      - Активный индекс корректно обновляется.
    """
    received_profiles: List[str] = []
    header_bar.profile_changed.connect(received_profiles.append)

    # Переключаем на второй профиль (Gaming, индекс 1)
    header_bar.profile_combo.setCurrentIndex(1)
    assert len(received_profiles) == 1
    assert received_profiles[-1] == "Gaming"
    assert header_bar.profile_combo.get_current_profile() == "Gaming"

    # Переключаем на третий профиль (Streaming, индекс 2)
    header_bar.profile_combo.setCurrentIndex(2)
    assert len(received_profiles) == 2
    assert received_profiles[-1] == "Streaming"
    assert header_bar.profile_combo.get_current_profile() == "Streaming"


def test_profile_selector_create_new(header_bar):
    """
    Проверка выбора пункта '+ New Profile...':
      - Эмитируется сигнал create_profile_requested().
      - Сигнал profile_changed НЕ эмитируется.
      - Активный индекс возвращается к предыдущему валидному (блокировка смены индекса).
      - Добавление профиля через add_profile вставляет пункт перед '+ New Profile...'.
    """
    create_profile_calls = []
    profile_changed_calls = []

    header_bar.create_profile_requested.connect(lambda: create_profile_calls.append(True))
    header_bar.profile_changed.connect(profile_changed_calls.append)

    # Устанавливаем исходный активный профиль: Gaming (индекс 1)
    header_bar.profile_combo.setCurrentIndex(1)
    profile_changed_calls.clear()
    assert header_bar.profile_combo.currentIndex() == 1

    # Находим индекс пункта '+ New Profile...' (последний элемент)
    new_profile_idx = header_bar.profile_combo.findData(PROFILE_NEW_ID)
    assert new_profile_idx > 0

    # Выбираем пункт '+ New Profile...'
    header_bar.profile_combo.setCurrentIndex(new_profile_idx)

    # Проверяем эмиссию create_profile_requested
    assert len(create_profile_calls) == 1
    # Сигнал смены профиля не должен был эмитироваться
    assert len(profile_changed_calls) == 0
    # Индекс должен быть восстановлен на 1 (Gaming)
    assert header_bar.profile_combo.currentIndex() == 1
    assert header_bar.profile_combo.get_current_profile() == "Gaming"

    # Добавляем новый профиль через add_profile
    header_bar.profile_combo.add_profile("Workplace", select=True)
    assert header_bar.profile_combo.get_current_profile() == "Workplace"
    assert header_bar.profile_combo.findData(PROFILE_NEW_ID) == header_bar.profile_combo.count() - 1

    # Снова кликаем на '+ New Profile...'
    header_bar.profile_combo.setCurrentIndex(header_bar.profile_combo.findData(PROFILE_NEW_ID))
    assert len(create_profile_calls) == 2
    assert header_bar.profile_combo.get_current_profile() == "Workplace"


def test_header_utility_buttons(header_bar, qtbot):
    """
    Проверка кликов по кнопкам тулбара и получения сигнала action_clicked:
      - 🔔 btn_notifications -> action_clicked('notifications')
      - 🧩 btn_store -> action_clicked('store')
      - ⚙ btn_settings -> action_clicked('settings')
      - 👤 btn_account -> action_clicked('account')
    """
    actions: List[str] = []
    header_bar.action_clicked.connect(actions.append)

    # Клик по кнопке уведомлений
    qtbot.mouseClick(header_bar.btn_notifications)
    assert len(actions) == 1
    assert actions[-1] == "notifications"

    # Клик по кнопке магазина
    qtbot.mouseClick(header_bar.btn_store)
    assert len(actions) == 2
    assert actions[-1] == "store"

    # Клик по кнопке настроек
    qtbot.mouseClick(header_bar.btn_settings)
    assert len(actions) == 3
    assert actions[-1] == "settings"

    # Клик по кнопке профиля оператора
    qtbot.mouseClick(header_bar.btn_account)
    assert len(actions) == 4
    assert actions[-1] == "account"


def test_header_bar_replacement_in_window(editor_window):
    """
    Проверка интеграции EditorHeaderBar в DeckEditorWindow через set_header_bar:
      - Изначально в окне смонтирован экземпляр EditorHeaderBar.
      - Повторный вызов set_header_bar с новым экземпляром корректно заменяет виджет.
      - Новый виджет сохраняет свойства и привязан к лэйауту окна.
      - Вызов retranslate_ui() окна каскадно вызывает retranslate_ui() у нового тулбара.
    """
    assert isinstance(editor_window.header_bar, EditorHeaderBar)

    new_header = EditorHeaderBar(editor_window.workspace_container)
    editor_window.set_header_bar(new_header)

    assert editor_window.header_bar is new_header
    assert editor_window.header_bar_widget is new_header
    assert editor_window.header_bar_slot is new_header

    # Проверяем каскадный вызов retranslate_ui при вызове у окна
    retranslate_mock = MagicMock()
    new_header.retranslate_ui = retranslate_mock

    editor_window.retranslate_ui()
    retranslate_mock.assert_called_once()


def test_header_bar_retranslate_ui(header_bar):
    """
    Проверка динамического обновления названий и тултипов при retranslate_ui():
      - В комбобоксе устройств обновляются локализованные названия.
      - В комбобоксе профилей обновляются системные пункты ('default', 'new_profile').
      - У всех 4 сервисных кнопок обновляются всплывающие подсказки (setToolTip).
      - Текущие выбранные индексы комбобоксов строго сохраняются (In-place Retranslate Invariant).
    """
    # Устанавливаем не нулевые индексы для проверки сохранения currentIndex
    header_bar.device_combo.setCurrentIndex(1)  # classic_3x5
    header_bar.profile_combo.setCurrentIndex(2)  # Streaming

    # 1. Переключаем локализацию на русский (RU)
    I18nManager().set_language("ru", emit_signal=False)
    header_bar.retranslate_ui()

    # Индексы сохранены
    assert header_bar.device_combo.currentIndex() == 1
    assert header_bar.profile_combo.currentIndex() == 2

    # Проверка текстов устройств в RU
    assert header_bar.device_combo.itemText(0) == t("deck.editor.header.devices.touch_2x5_strip")
    assert header_bar.device_combo.itemText(1) == t("deck.editor.header.devices.classic_3x5")

    # Проверка текстов профилей в RU
    assert header_bar.profile_combo.itemText(0) == t("deck.editor.header.profiles.default")
    assert header_bar.profile_combo.itemText(0) == "Основной профиль"
    new_prof_idx = header_bar.profile_combo.findData(PROFILE_NEW_ID)
    assert header_bar.profile_combo.itemText(new_prof_idx) == t("deck.editor.header.profiles.new_profile")
    assert header_bar.profile_combo.itemText(new_prof_idx) == "+ Новый профиль..."

    # Проверка кнопки сохранения в RU
    assert "Сохранить" in header_bar.btn_save.text()
    assert header_bar.btn_save.toolTip() == "Сохранить конфигурацию (Ctrl+S)"

    # Проверка тултипов сервисных кнопок в RU
    assert header_bar.btn_notifications.toolTip() == "Уведомления и лог макросов"
    assert header_bar.btn_store.toolTip() == "Магазин расширений и иконок"
    assert header_bar.btn_settings.toolTip() == "Настройки редактора DuckDeck"
    assert header_bar.btn_account.toolTip() == "Профиль пользователя"

    # 2. Переключаем локализацию на английский (EN)
    I18nManager().set_language("en", emit_signal=False)
    header_bar.retranslate_ui()

    # Индексы сохранены
    assert header_bar.device_combo.currentIndex() == 1
    assert header_bar.profile_combo.currentIndex() == 2

    # Проверка текстов устройств в EN
    assert header_bar.device_combo.itemText(0) == "DuckDeck Touch (2x5 + Strip)"
    assert header_bar.device_combo.itemText(1) == "Classic Stream Deck (3x5)"

    # Проверка текстов профилей в EN
    assert header_bar.profile_combo.itemText(0) == "Default Profile"
    assert header_bar.profile_combo.itemText(new_prof_idx) == "+ New Profile..."

    # Проверка кнопки сохранения в EN
    assert "Save" in header_bar.btn_save.text()
    assert header_bar.btn_save.toolTip() == "Save configuration (Ctrl+S)"

    # Проверка тултипов сервисных кнопок в EN
    assert header_bar.btn_notifications.toolTip() == "Notifications & Macro Log"
    assert header_bar.btn_store.toolTip() == "Extensions & Icons Store"
    assert header_bar.btn_settings.toolTip() == "DuckDeck Editor Settings"
    assert header_bar.btn_account.toolTip() == "User Profile"


def test_header_save_button_signals_and_feedback(header_bar, qtbot):
    """
    Проверка кнопки сохранения:
      - Клик по кнопке эмитирует сигнал save_requested.
      - Вызов show_save_success() переводит кнопку в состояние 'success' с текстом '✓ ...'.
      - Истечение таймера возвращает кнопку в исходное состояние.
    """
    save_calls = []
    header_bar.save_requested.connect(lambda: save_calls.append(True))

    qtbot.mouseClick(header_bar.btn_save)
    assert len(save_calls) == 1

    header_bar.show_save_success()
    assert "✓" in header_bar.btn_save.text()
    assert header_bar.btn_save.property("state") == "success"
    assert header_bar._save_timer is not None
    assert header_bar._save_timer.isActive() is True

    # Имитируем срабатывание таймера
    header_bar._reset_save_state()
    assert "💾" in header_bar.btn_save.text()
    assert header_bar.btn_save.property("state") == "normal"


def test_header_save_timer_cleanup(header_bar):
    """
    Проверка безопасной остановки и удаления таймера в cleanup():
      - Отсутствие утечек таймеров при закрытии/очистке виджета.
    """
    header_bar.show_save_success()
    assert header_bar._save_timer is not None
    assert header_bar._save_timer.isActive() is True

    header_bar.cleanup()
    assert header_bar._save_timer is None
