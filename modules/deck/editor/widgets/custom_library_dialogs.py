"""
Компактные диалоги управления пользовательской библиотекой DuckDeck:
- CreateTabDialog: создание пользовательской вкладки (название + иконка).
- SaveToLibraryDialog: сохранение настроенной кнопки в выбранную вкладку.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.i18n import t
from modules.deck.custom_library import CustomLibraryStorage
from modules.deck.editor.styles import EDITOR_MAIN_QSS, INPUT_HEIGHT

TAB_PRESET_ICONS = ["📁", "⭐", "🎮", "🎵", "⚙️", "🔥", "💻", "🚀"]


class CreateTabDialog(QDialog):
    """Компактный диалог создания пользовательской вкладки."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("createTabDialog")
        self.setWindowTitle(t("deck.editor.drawer.custom.create_tab_title"))
        self.setModal(True)
        self.setMinimumWidth(320)
        self.setStyleSheet(EDITOR_MAIN_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.lbl_name = QLabel(t("deck.editor.drawer.custom.tab_name_label"), self)
        self.edit_name = QLineEdit(self)
        self.edit_name.setObjectName("editCustomTabName")
        self.edit_name.setFixedHeight(INPUT_HEIGHT)
        self.edit_name.setPlaceholderText(t("deck.editor.drawer.custom.tab_name_placeholder"))
        self.edit_name.textChanged.connect(self._update_ok_state)
        form.addRow(self.lbl_name, self.edit_name)

        self.lbl_icon = QLabel(t("deck.editor.drawer.custom.tab_icon_label"), self)
        self.combo_icon = QComboBox(self)
        self.combo_icon.setObjectName("comboCustomTabIcon")
        self.combo_icon.setFixedHeight(INPUT_HEIGHT)
        self.combo_icon.setFocusPolicy(Qt.NoFocus)
        for ico in TAB_PRESET_ICONS:
            self.combo_icon.addItem(ico, ico)
        form.addRow(self.lbl_icon, self.combo_icon)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_cancel = QPushButton(t("deck.editor.drawer.custom.cancel_btn"), self)
        self.btn_cancel.setObjectName("iconLibraryCancelBtn")
        self.btn_cancel.setFocusPolicy(Qt.NoFocus)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton(t("deck.editor.drawer.custom.save_btn"), self)
        self.btn_ok.setObjectName("iconLibrarySelectBtn")
        self.btn_ok.setFocusPolicy(Qt.NoFocus)
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setEnabled(False)
        self.btn_ok.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        layout.addLayout(btn_row)

    def _update_ok_state(self, text: str) -> None:
        self.btn_ok.setEnabled(bool(text.strip()))

    def get_tab_title(self) -> str:
        return self.edit_name.text().strip()

    def get_tab_icon(self) -> str:
        return str(self.combo_icon.currentData() or "📁")


class SaveToLibraryDialog(QDialog):
    """Диалог сохранения настроенной кнопки в пользовательскую вкладку."""

    def __init__(
        self,
        storage: CustomLibraryStorage,
        default_title: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.storage = storage
        self.setObjectName("saveToLibraryDialog")
        self.setWindowTitle(t("deck.editor.drawer.custom.save_dialog_title"))
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setStyleSheet(EDITOR_MAIN_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.lbl_title = QLabel(t("deck.editor.drawer.custom.button_title_label"), self)
        self.edit_title = QLineEdit(self)
        self.edit_title.setObjectName("editSaveButtonTitle")
        self.edit_title.setFixedHeight(INPUT_HEIGHT)
        self.edit_title.setText(default_title or "")
        self.edit_title.textChanged.connect(self._update_save_state)
        form.addRow(self.lbl_title, self.edit_title)

        self.lbl_tab = QLabel(t("deck.editor.drawer.custom.target_tab_label"), self)
        tab_row = QHBoxLayout()
        tab_row.setSpacing(6)

        self.combo_tab = QComboBox(self)
        self.combo_tab.setObjectName("comboTargetCustomTab")
        self.combo_tab.setFixedHeight(INPUT_HEIGHT)
        self.combo_tab.setFocusPolicy(Qt.NoFocus)

        self.btn_new_tab = QPushButton(t("deck.editor.drawer.custom.new_tab_inline"), self)
        self.btn_new_tab.setObjectName("btnInlineNewTab")
        self.btn_new_tab.setFixedHeight(INPUT_HEIGHT)
        self.btn_new_tab.setFocusPolicy(Qt.NoFocus)
        self.btn_new_tab.setCursor(Qt.PointingHandCursor)
        self.btn_new_tab.clicked.connect(self._on_new_tab_clicked)

        tab_row.addWidget(self.combo_tab, 1)
        tab_row.addWidget(self.btn_new_tab, 0)
        form.addRow(self.lbl_tab, tab_row)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_cancel = QPushButton(t("deck.editor.drawer.custom.cancel_btn"), self)
        self.btn_cancel.setObjectName("iconLibraryCancelBtn")
        self.btn_cancel.setFocusPolicy(Qt.NoFocus)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton(t("deck.editor.drawer.custom.save_btn"), self)
        self.btn_save.setObjectName("iconLibrarySelectBtn")
        self.btn_save.setFocusPolicy(Qt.NoFocus)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

        self._populate_tabs()
        self._update_save_state(self.edit_title.text())

    def _populate_tabs(self, select_tab_id: Optional[str] = None) -> None:
        self.combo_tab.clear()
        tabs = self.storage.list_tabs()
        if not tabs:
            default_tab = self.storage.create_tab(t("deck.editor.drawer.custom.default_tab_name"), "⭐")
            tabs = [default_tab]
        for tab in tabs:
            self.combo_tab.addItem(f"{tab.icon} {tab.title}", tab.id)
        if select_tab_id:
            idx = self.combo_tab.findData(select_tab_id)
            if idx >= 0:
                self.combo_tab.setCurrentIndex(idx)

    def _on_new_tab_clicked(self) -> None:
        dlg = CreateTabDialog(self)
        if dlg.exec() == QDialog.Accepted:
            tab = self.storage.create_tab(dlg.get_tab_title(), dlg.get_tab_icon())
            self._populate_tabs(select_tab_id=tab.id)

    def _update_save_state(self, text: str) -> None:
        has_tab = self.combo_tab.count() > 0
        self.btn_save.setEnabled(bool(text.strip()) and has_tab)

    def get_button_title(self) -> str:
        return self.edit_title.text().strip()

    def get_selected_tab_id(self) -> str:
        return str(self.combo_tab.currentData() or "")
