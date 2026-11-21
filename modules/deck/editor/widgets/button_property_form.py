"""
Форма инспектора свойств кнопки (ButtonPropertyForm).
Включает шапку с категорией и корзиной 🗑️, плитку превью иконки (84x84 px),
поля Title, Actions (пресеты) и Hotkey. Поддерживает in-place retranslate без потери данных.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.editor.dto import ButtonSlotDTO
from modules.deck.editor.styles import (
    FORM_LABEL_WIDTH,
    INPUT_HEIGHT,
    INSPECTOR_HEIGHT,
)
from modules.deck.editor.widgets.hotkey_capture import HotkeyCaptureButton
from modules.deck.editor.widgets.key_preview_tile import KeyPreviewTile

# Пресеты типов действий в выпадающем списке
ACTION_PRESET_KEYS = [
    "preset_actions",
    "hotkey",
    "open_application",
    "media_control",
    "text_macro",
]


class ButtonPropertyForm(QWidget):
    """
    Форма редактирования свойств кнопки сетки DuckDeck (0..9).
    Размещается на Index 1 стэка инспектора свойств (KeyPropertyInspector).
    Строго соблюдает бюджет высоты 220 px и инвариант In-place Retranslate.
    """

    property_changed = Signal(str, object)
    delete_requested = Signal()
    font_settings_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("buttonPropertyForm")
        self.setFixedHeight(INSPECTOR_HEIGHT)

        self._slot_index: int = 0
        self._current_category_raw: str = "System: Hotkey"

        # Главный вертикальный лэйаут формы
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 8, 12, 8)
        root_layout.setSpacing(6)

        # ----------------------------------------------------------------------
        # 1. Шапка формы (Header Row: категория слева, корзина справа)
        # ----------------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_category = QLabel(self._current_category_raw, self)
        self.lbl_category.setObjectName("lblInspectorCategory")
        self.lbl_category.setProperty("class", "InspectorCategoryLabel")

        self.btn_delete = QPushButton("🗑️", self)
        self.btn_delete.setObjectName("btnInspectorDelete")
        self.btn_delete.setProperty("class", "InspectorDeleteButton")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self.delete_requested.emit)

        header_layout.addWidget(self.lbl_category)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_delete)
        root_layout.addLayout(header_layout)

        # Разделитель HLine (1px BORDER_SURFACE_1)
        separator = QFrame(self)
        separator.setObjectName("formSeparator")
        separator.setProperty("class", "FormSeparator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setFixedHeight(1)
        root_layout.addWidget(separator)

        # ----------------------------------------------------------------------
        # 2. Содержимое формы (Content Row: превью-плитка 84x84 + сетка полей)
        # ----------------------------------------------------------------------
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 2, 0, 2)
        content_layout.setSpacing(12)

        # Слева: интерактивная плитка превью иконки (84x84 px)
        self.preview_tile = KeyPreviewTile(self)
        self.preview_tile.tile_clicked.connect(
            lambda: self.property_changed.emit("icon_clicked", None)
        )
        self.preview_tile.add_icon_clicked.connect(
            lambda: self.property_changed.emit("load_image", None)
        )
        self.preview_tile.icon_menu_clicked.connect(
            lambda: self.property_changed.emit("icon_menu", None)
        )
        content_layout.addWidget(self.preview_tile)

        # Справа: сетка параметров (Title, Actions, Hotkey)
        fields_grid = QGridLayout()
        fields_grid.setContentsMargins(0, 0, 0, 0)
        fields_grid.setVerticalSpacing(6)
        fields_grid.setHorizontalSpacing(8)

        # Строка 0: Title
        self.lbl_title_field = QLabel(self)
        self.lbl_title_field.setObjectName("lblTitleField")
        self.lbl_title_field.setProperty("class", "InspectorFieldLabel")
        self.lbl_title_field.setFixedWidth(FORM_LABEL_WIDTH)

        self.edit_title = QLineEdit(self)
        self.edit_title.setObjectName("editTitle")
        self.edit_title.setProperty("class", "InspectorLineEdit")
        self.edit_title.setFixedHeight(INPUT_HEIGHT)
        self.edit_title.textEdited.connect(
            lambda text: self.property_changed.emit("title", text)
        )

        self.btn_font = QPushButton("T ▾", self)
        self.btn_font.setObjectName("btnFontSettings")
        self.btn_font.setProperty("class", "FontSettingButton")
        self.btn_font.setFixedSize(INPUT_HEIGHT, INPUT_HEIGHT)
        self.btn_font.setCursor(Qt.PointingHandCursor)
        self.btn_font.clicked.connect(self.font_settings_requested.emit)

        fields_grid.addWidget(self.lbl_title_field, 0, 0, Qt.AlignVCenter)
        fields_grid.addWidget(self.edit_title, 0, 1)
        fields_grid.addWidget(self.btn_font, 0, 2)

        # Строка 1: Actions (пресеты)
        self.lbl_actions_field = QLabel(self)
        self.lbl_actions_field.setObjectName("lblActionsField")
        self.lbl_actions_field.setProperty("class", "InspectorFieldLabel")
        self.lbl_actions_field.setFixedWidth(FORM_LABEL_WIDTH)

        self.combo_actions = QComboBox(self)
        self.combo_actions.setObjectName("comboActions")
        self.combo_actions.setFixedHeight(INPUT_HEIGHT)
        self.combo_actions.setCursor(Qt.PointingHandCursor)
        for key in ACTION_PRESET_KEYS:
            self.combo_actions.addItem(
                t(f"deck.editor.inspector.actions_presets.{key}"), key
            )
        self.combo_actions.currentIndexChanged.connect(self._on_action_type_changed)

        fields_grid.addWidget(self.lbl_actions_field, 1, 0, Qt.AlignVCenter)
        fields_grid.addWidget(self.combo_actions, 1, 1, 1, 2)

        # Строка 2: Hotkey (кнопка интерактивного захвата)
        self.lbl_hotkey_field = QLabel(self)
        self.lbl_hotkey_field.setObjectName("lblHotkeyField")
        self.lbl_hotkey_field.setProperty("class", "InspectorFieldLabel")
        self.lbl_hotkey_field.setFixedWidth(FORM_LABEL_WIDTH)

        self.btn_hotkey = HotkeyCaptureButton(self)
        self.btn_hotkey.hotkey_changed.connect(
            lambda hk: self.property_changed.emit("hotkey", hk)
        )

        fields_grid.addWidget(self.lbl_hotkey_field, 2, 0, Qt.AlignVCenter)
        fields_grid.addWidget(self.btn_hotkey, 2, 1, 1, 2)

        content_layout.addLayout(fields_grid)
        root_layout.addLayout(content_layout)

        # Эластичный спейсер для плотной фиксации в пределах 220 px
        root_layout.addStretch(1)

        # Начальная инициализация локализованных строк
        self.retranslate_ui()

    def set_category(self, category: str) -> None:
        """
        Устанавливает отображаемое имя категории/типа в шапке формы.
        """
        self._current_category_raw = category
        self.lbl_category.setText(category)

    def get_category(self) -> str:
        """
        Возвращает текущую строку категории.
        """
        return self._current_category_raw

    def get_slot_index(self) -> int:
        """
        Возвращает индекс текущего редактируемого слота кнопки.
        """
        return self._slot_index

    def load_slot_data(self, dto: ButtonSlotDTO) -> None:
        """
        Заполняет поля формы данными из DTO кнопки с защитой blockSignals(True)
        для предотвращения сигнального эха и ложных событий изменения.
        """
        self._slot_index = dto.slot_index

        self.edit_title.blockSignals(True)
        self.combo_actions.blockSignals(True)
        self.btn_hotkey.blockSignals(True)
        try:
            category_text = dto.category if dto.category else "System: Hotkey"
            self.set_category(category_text)
            self.edit_title.setText(dto.title)

            # Сопоставление типа действия с элементом комбобокса
            target_action = dto.action_type.strip().lower()
            target_key_matched = False
            for i in range(self.combo_actions.count()):
                data_val = str(self.combo_actions.itemData(i)).lower()
                text_val = self.combo_actions.itemText(i).lower()
                if (
                    target_action == data_val
                    or target_action == text_val
                    or target_action.replace(" ", "_") == data_val
                ):
                    self.combo_actions.setCurrentIndex(i)
                    target_key_matched = True
                    break

            if not target_key_matched and self.combo_actions.count() > 0:
                self.combo_actions.setCurrentIndex(0)

            self.btn_hotkey.set_hotkey(dto.hotkey)
            self.preview_tile.set_icon(dto.icon)
        finally:
            self.edit_title.blockSignals(False)
            self.combo_actions.blockSignals(False)
            self.btn_hotkey.blockSignals(False)

    def retranslate_ui(self) -> None:
        """
        Обновляет локализованные подписи полей, тултипы и элементы пресетов действий.
        Строго сохраняет введенный пользователем текст в edit_title и назначенный хоткей.
        (In-place Retranslate Invariant).
        """
        # Тултип кнопки удаления
        self.btn_delete.setToolTip(t("deck.editor.inspector.tooltips.delete_action"))

        # Подписи полей формы
        self.lbl_title_field.setText(t("deck.editor.inspector.fields.title"))
        self.lbl_actions_field.setText(t("deck.editor.inspector.fields.actions"))
        self.lbl_hotkey_field.setText(t("deck.editor.inspector.fields.hotkey"))

        # Пресеты в комбобоксе: обновление текстов по сохраненному userData ключу
        self.combo_actions.blockSignals(True)
        try:
            for i in range(self.combo_actions.count()):
                preset_key = self.combo_actions.itemData(i)
                if preset_key:
                    self.combo_actions.setItemText(
                        i, t(f"deck.editor.inspector.actions_presets.{preset_key}")
                    )
        finally:
            self.combo_actions.blockSignals(False)

        # Каскадный вызов локализации дочерних интерактивных компонентов
        self.preview_tile.retranslate_ui()
        self.btn_hotkey.retranslate_ui()

    def _on_action_type_changed(self, index: int) -> None:
        """
        Обработчик пользовательского выбора типа действия в комбобоксе.
        """
        preset_key = self.combo_actions.itemData(index)
        value_to_emit = preset_key if preset_key is not None else self.combo_actions.currentText()
        self.property_changed.emit("action_type", value_to_emit)
