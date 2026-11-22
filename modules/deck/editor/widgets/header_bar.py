"""
Компоненты верхней панели управления DuckDeck Editor (Header Bar).
Включает селектор устройств (DeviceComboBox), селектор профилей (ProfileComboBox),
сервисные кнопки утилит (HeaderIconButton) и контейнер EditorHeaderBar
со строгой поддержкой Dark Obsidian и реактивной локализации retranslate_ui().
"""
from __future__ import annotations

import logging
from typing import Optional, Sequence

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QListView,
    QPushButton,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.styles import (
    HEADER_HEIGHT,
    TOOL_BUTTON_SIZE,
    ToolbarVLine,
)

logger = logging.getLogger(__name__)

# Системные идентификаторы устройств
DEVICE_TOUCH_2X5 = "touch_2x5_strip"
DEVICE_CLASSIC_3X5 = "classic_3x5"

SUPPORTED_DEVICES = (
    DEVICE_TOUCH_2X5,
    DEVICE_CLASSIC_3X5,
)

# Системные идентификаторы профилей
PROFILE_DEFAULT_ID = "default"
PROFILE_NEW_ID = "__new_profile__"


class DeviceComboBox(QComboBox):
    """
    Выпадающий список выбора аппаратного устройства (Touch 2x5 + Strip или Classic 3x5).
    Использует QListView для темного стиля Dark Obsidian без системных белых рамок.
    Поддерживает retranslate_ui() и эмитирует device_selected(str device_id).
    """

    device_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("deviceComboBox")
        self.setView(QListView(self))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)
        self.setFixedHeight(32)

        self._is_retranslating = False

        self._init_items()
        self.currentIndexChanged.connect(self._on_index_changed)

    def _init_items(self) -> None:
        """Наполняет список поддерживаемыми устройствами."""
        for dev_id in SUPPORTED_DEVICES:
            self.addItem(t(f"deck.editor.header.devices.{dev_id}"), dev_id)

    def _on_index_changed(self, index: int) -> None:
        if self._is_retranslating or index < 0:
            return
        dev_id = self.itemData(index)
        if dev_id:
            self.device_selected.emit(str(dev_id))

    def get_current_device_id(self) -> str:
        """Возвращает идентификатор текущего выбранного устройства."""
        data = self.currentData()
        return str(data) if data is not None else ""

    def set_current_device(self, device_id: str) -> bool:
        """Устанавливает выбранное устройство по его идентификатору."""
        for i in range(self.count()):
            if self.itemData(i) == device_id:
                self.setCurrentIndex(i)
                return True
        return False

    def retranslate_ui(self) -> None:
        """Обновляет видимый текст устройств по ключам локализации, сохраняя индекс."""
        self._is_retranslating = True
        current_idx = self.currentIndex()
        for i in range(self.count()):
            dev_id = self.itemData(i)
            if dev_id:
                self.setItemText(i, t(f"deck.editor.header.devices.{dev_id}"))
        self.setCurrentIndex(current_idx)
        self._is_retranslating = False


class ProfileComboBox(QComboBox):
    """
    Выпадающий список выбора профиля макросов с перехватом клика на '+ New Profile...'.
    Использует QListView для темного стиля Dark Obsidian без системных белых рамок.
    Эмитирует profile_selected(str) и create_profile_requested().
    """

    profile_selected = Signal(str)
    create_profile_requested = Signal()

    def __init__(
        self,
        profiles: Optional[Sequence[str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("profileComboBox")
        self.setView(QListView(self))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(150)
        self.setMaximumWidth(190)
        self.setFixedHeight(32)

        self._last_valid_index = 0
        self._is_retranslating = False

        initial_profiles = list(profiles) if profiles else [PROFILE_DEFAULT_ID, "Gaming", "Streaming"]
        self.set_profiles(initial_profiles, current=PROFILE_DEFAULT_ID)

        self.currentIndexChanged.connect(self._on_index_changed)

    def set_profiles(self, profiles: Sequence[str], current: Optional[str] = None) -> None:
        """
        Динамически задает список доступных профилей, добавляя в конец '+ New Profile...'.
        """
        self._is_retranslating = True
        self.blockSignals(True)
        self.clear()

        for name in profiles:
            if name == PROFILE_DEFAULT_ID:
                self.addItem(t("deck.editor.header.profiles.default"), PROFILE_DEFAULT_ID)
            else:
                self.addItem(str(name), str(name))

        # Специальный пункт-триггер добавления нового профиля
        self.addItem(t("deck.editor.header.profiles.new_profile"), PROFILE_NEW_ID)

        target_index = 0
        if current is not None:
            for i in range(self.count()):
                if self.itemData(i) == current or self.itemText(i) == current:
                    target_index = i
                    break

        self.setCurrentIndex(target_index)
        self._last_valid_index = target_index
        self.blockSignals(False)
        self._is_retranslating = False

    def add_profile(self, name: str, select: bool = True) -> None:
        """Добавляет новый профиль перед пунктом '+ New Profile...'."""
        new_prof_idx = self.count() - 1
        if new_prof_idx < 0:
            new_prof_idx = 0
        self.insertItem(new_prof_idx, str(name), str(name))
        if select:
            self.setCurrentIndex(new_prof_idx)

    def get_current_profile(self) -> str:
        """Возвращает имя текущего профиля."""
        return self.itemText(self.currentIndex())

    def get_current_profile_id(self) -> str:
        """Возвращает идентификатор текущего профиля."""
        data = self.currentData()
        return str(data) if data is not None else ""

    def _on_index_changed(self, index: int) -> None:
        if self._is_retranslating or index < 0:
            return

        user_data = self.itemData(index)
        if user_data == PROFILE_NEW_ID:
            # Перехват клика без смены выбранного профиля
            self.blockSignals(True)
            self.setCurrentIndex(self._last_valid_index)
            self.blockSignals(False)
            self.create_profile_requested.emit()
            return

        self._last_valid_index = index
        self.profile_selected.emit(self.itemText(index))

    def retranslate_ui(self) -> None:
        """Обновляет текст системных пунктов (default, new_profile) без смены индекса."""
        self._is_retranslating = True
        self.blockSignals(True)
        current_idx = self.currentIndex()

        for i in range(self.count()):
            data = self.itemData(i)
            if data == PROFILE_DEFAULT_ID:
                self.setItemText(i, t("deck.editor.header.profiles.default"))
            elif data == PROFILE_NEW_ID:
                self.setItemText(i, t("deck.editor.header.profiles.new_profile"))

        self.setCurrentIndex(current_idx)
        self.blockSignals(False)
        self._is_retranslating = False


class HeaderIconButton(QPushButton):
    """
    Плоская сервисная кнопка 32x32 px для тулбара редактора.
    Имеет прозрачный фон с подсветкой при наведении, отображает векторный символ / эмодзи
    и обновляет всплывающую подсказку через retranslate_ui().
    """

    action_triggered = Signal(str)

    def __init__(
        self,
        icon_text: str = "",
        tooltip_key: str = "",
        action_id: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(icon_text, parent)
        self.tooltip_key = tooltip_key
        self.action_id = action_id

        self.setProperty("class", "HeaderIconButton")
        self.setFixedSize(TOOL_BUTTON_SIZE, TOOL_BUTTON_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

        if self.tooltip_key:
            self.setToolTip(t(self.tooltip_key))

        self.clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        self.action_triggered.emit(self.action_id)

    def retranslate_ui(self) -> None:
        """Обновляет подсказку кнопки по ключу локализации."""
        if self.tooltip_key:
            self.setToolTip(t(self.tooltip_key))


class EditorHeaderBar(QFrame):
    """
    Верхняя панель управления редактора DuckDeck (Header Bar).
    Включает:
    - DeviceComboBox (DuckDeck Touch vs Classic Stream Deck)
    - ProfileComboBox (профили макросов + триггер '+ New Profile...')
    - ToolbarVLine (микро-разделитель)
    - Эластичный спейсер
    - Сервисные кнопки утилит (Уведомления, Магазин, Настройки, Профиль)
    """

    device_changed = Signal(str)
    profile_changed = Signal(str)
    create_profile_requested = Signal()
    action_clicked = Signal(str)
    save_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("editorHeaderBar")
        self.setFixedHeight(HEADER_HEIGHT)

        self._save_timer: Optional[QTimer] = None
        self._is_saved_state: bool = False

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # Селектор устройств
        self.device_combo = DeviceComboBox(self)
        self.device_combo.device_selected.connect(self.device_changed.emit)
        layout.addWidget(self.device_combo)

        # Вертикальный разделитель
        self.v_line = ToolbarVLine(self)
        layout.addWidget(self.v_line)

        # Селектор профилей
        self.profile_combo = ProfileComboBox(parent=self)
        self.profile_combo.profile_selected.connect(self.profile_changed.emit)
        self.profile_combo.create_profile_requested.connect(self.create_profile_requested.emit)
        layout.addWidget(self.profile_combo)

        # Растягиваемый спейсер
        layout.addStretch(1)

        # Кнопка сохранения конфигурации
        self.btn_save = QPushButton(self)
        self.btn_save.setObjectName("btnSaveConfig")
        self.btn_save.setProperty("class", "HeaderSaveButton")
        self.btn_save.setProperty("state", "normal")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFocusPolicy(Qt.NoFocus)
        self.btn_save.setFixedHeight(32)
        self.btn_save.setText(f"💾 {t('deck.editor.header.save')}")
        self.btn_save.setToolTip(t("deck.editor.header.save_tooltip"))
        self.btn_save.clicked.connect(self.save_requested.emit)
        layout.addWidget(self.btn_save)

        # Вертикальный разделитель перед сервисными кнопками
        self.v_line_save = ToolbarVLine(self)
        layout.addWidget(self.v_line_save)

        # Сервисные кнопки
        self.btn_notifications = HeaderIconButton(
            icon_text="🔔",
            tooltip_key="deck.editor.header.tooltips.notifications",
            action_id="notifications",
            parent=self,
        )
        self.btn_store = HeaderIconButton(
            icon_text="🧩",
            tooltip_key="deck.editor.header.tooltips.store",
            action_id="store",
            parent=self,
        )
        self.btn_settings = HeaderIconButton(
            icon_text="⚙",
            tooltip_key="deck.editor.header.tooltips.settings",
            action_id="settings",
            parent=self,
        )
        self.btn_account = HeaderIconButton(
            icon_text="👤",
            tooltip_key="deck.editor.header.tooltips.account",
            action_id="account",
            parent=self,
        )

        for btn in (
            self.btn_notifications,
            self.btn_store,
            self.btn_settings,
            self.btn_account,
        ):
            btn.action_triggered.connect(self.action_clicked.emit)
            layout.addWidget(btn)

    def show_save_success(self) -> None:
        """
        Отображает визуальный отклик успешного сохранения:
        зеленый изумрудный акцент, иконку '✓' и текст 'Сохранено!'.
        Через 2000 мс автоматически возвращает исходное состояние.
        """
        self._is_saved_state = True
        self.btn_save.setText(f"✓ {t('deck.editor.header.saved')}")
        self.btn_save.setProperty("state", "success")
        self.btn_save.style().unpolish(self.btn_save)
        self.btn_save.style().polish(self.btn_save)

        if self._save_timer is not None and self._save_timer.isActive():
            self._save_timer.stop()

        if self._save_timer is None:
            self._save_timer = QTimer(self)
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._reset_save_state)

        self._save_timer.start(2000)

    def _reset_save_state(self) -> None:
        """Сброс кнопки сохранения в штатное состояние."""
        self._is_saved_state = False
        self.btn_save.setText(f"💾 {t('deck.editor.header.save')}")
        self.btn_save.setProperty("state", "normal")
        self.btn_save.style().unpolish(self.btn_save)
        self.btn_save.style().polish(self.btn_save)

    def cleanup(self) -> None:
        """Освобождение ресурсов и безопасная остановка таймеров."""
        if self._save_timer is not None:
            if self._save_timer.isActive():
                self._save_timer.stop()
            self._save_timer.deleteLater()
            self._save_timer = None

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)

    def retranslate_ui(self) -> None:
        """Каскадное обновление локализации всех компонентов тулбара."""
        self.device_combo.retranslate_ui()
        self.profile_combo.retranslate_ui()
        if getattr(self, "_is_saved_state", False):
            self.btn_save.setText(f"✓ {t('deck.editor.header.saved')}")
        else:
            self.btn_save.setText(f"💾 {t('deck.editor.header.save')}")
        self.btn_save.setToolTip(t("deck.editor.header.save_tooltip"))
        self.btn_notifications.retranslate_ui()
        self.btn_store.retranslate_ui()
        self.btn_settings.retranslate_ui()
        self.btn_account.retranslate_ui()
