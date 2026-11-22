"""
Главное окно конфигуратора макро-панели и тачбара DuckDeck (DeckEditorWindow).
Реализует двухпанельную компоновку на базе QSplitter (70% рабочая область / 30% библиотека действий),
реактивный протокол Localization-First (retranslate_ui, шина bus.language_changed)
и публичный API замены слотов-плейсхолдеров на функциональные виджеты.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeySequence, QShortcut, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.event_bus import bus
from core.i18n import t
from modules.deck.editor.actions_registry import get_default_action_catalog
from modules.deck.editor.commands import (
    AssignActionCommand,
    ClearSlotCommand,
    SwapButtonsCommand,
    UpdatePropertyCommand,
)
from modules.deck.editor.dto import (
    ButtonSlotDTO,
    TouchbarClockDTO,
    TouchbarMediaDTO,
    TouchbarTelemetryDTO,
)
from modules.deck.editor.styles import (
    DRAWER_MAX_WIDTH,
    DRAWER_MIN_WIDTH,
    WINDOW_DEFAULT_SIZE,
    WINDOW_MIN_SIZE,
    WORKSPACE_MIN_WIDTH,
    apply_editor_theme,
)
from modules.deck.editor.widgets.action_drawer import ActionLibraryDrawer
from modules.deck.editor.widgets.deck_canvas import DeckCanvasWidget
from modules.deck.editor.widgets.header_bar import EditorHeaderBar
from modules.deck.editor.widgets.pagination_bar import PageNavigationBar
from modules.deck.editor.widgets.placeholders import (
    ActionListSlot,
    CanvasAreaSlot,
    HeaderBarSlot,
    InspectorSlot,
    PaginationBarSlot,
    SearchSlot,
)
from modules.deck.editor.widgets.property_inspector import KeyPropertyInspector

logger = logging.getLogger("duckdock.deck.editor")


class DeckEditorWindow(QMainWindow):
    """
    Главное окно визуального редактора DuckDeck (WYSIWYG Configurator).
    Компонуется на базе горизонтального QSplitter с соотношением 70/30:
    - Левая часть: панель заголовка, сетка кнопок 2x5, тачбар, пагинация и Property Inspector.
    - Правая часть: библиотека действий и каталог макросов (Action Library Drawer).
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        config_path: Optional[str] = None,
    ) -> None:
        super().__init__(parent)

        self.resize(WINDOW_DEFAULT_SIZE[0], WINDOW_DEFAULT_SIZE[1])
        self.setMinimumSize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])

        # Презентационная модель данных окна редактора
        self.config_path: str = config_path if config_path else "config/deck_config.json"
        self.active_page_id: str | int = "default"
        self._button_slots: dict[int, ButtonSlotDTO] = {
            i: ButtonSlotDTO(slot_index=i) for i in range(10)
        }
        self._touchbar_media = TouchbarMediaDTO()
        self._touchbar_clock = TouchbarClockDTO()
        self._touchbar_telemetry = TouchbarTelemetryDTO()
        self._is_syncing_page: bool = False
        self._current_page_index: int = 1
        self._is_dirty: bool = False
        self._skip_close_dialog: bool = False
        self._is_applying_command: bool = False
        self.autosave_enabled: bool = False

        # Стек истории Undo / Redo и дебаунсер автосохранения
        self._undo_stack = QUndoStack(self)
        self._undo_stack.cleanChanged.connect(self._on_undo_clean_changed)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._on_autosave_timeout)

        self._init_ui()
        self.set_header_bar(EditorHeaderBar(self))
        self.set_canvas_widget(DeckCanvasWidget(self))
        self.set_pagination_bar(PageNavigationBar(self))
        self.set_inspector_widget(KeyPropertyInspector(self))
        drawer = ActionLibraryDrawer(self)
        drawer.populate_actions(get_default_action_catalog())
        self.set_action_drawer(drawer)
        self._center_on_primary_screen()
        apply_editor_theme(self)

        # Хоткеи быстрого сохранения Ctrl+S и истории Undo/Redo
        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._save_shortcut.activated.connect(self.save_configuration)

        self._undo_shortcut = QShortcut(QKeySequence.Undo, self)
        self._undo_shortcut.activated.connect(self._undo_stack.undo)

        self._redo_shortcut = QShortcut(QKeySequence.Redo, self)
        self._redo_shortcut.activated.connect(self._undo_stack.redo)

        self._redo_shift_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self._redo_shift_shortcut.activated.connect(self._undo_stack.redo)

        self.retranslate_ui()
        bus.language_changed.connect(self._handle_language_changed)
        bus.deck_page_changed.connect(self._on_bus_deck_page_changed)
        self.load_configuration()

    def _init_ui(self) -> None:
        """Инициализация компоновки окна, контейнеров и слотов-плейсхолдеров."""
        self.main_splitter = QSplitter(Qt.Horizontal, self)
        self.main_splitter.setObjectName("editorCentralWidget")
        self.main_splitter.setChildrenCollapsible(False)
        self.setCentralWidget(self.main_splitter)

        # ----------------------------------------------------------------------
        # Левая рабочая область (Workspace: Header + Canvas + Paging + Inspector)
        # ----------------------------------------------------------------------
        self.workspace_container = QWidget(self.main_splitter)
        self.workspace_container.setObjectName("workspaceContainer")
        self.workspace_container.setMinimumWidth(WORKSPACE_MIN_WIDTH)

        self._workspace_layout = QVBoxLayout(self.workspace_container)
        self._workspace_layout.setContentsMargins(12, 12, 12, 12)
        self._workspace_layout.setSpacing(8)

        self.header_bar: QWidget = HeaderBarSlot(self.workspace_container)
        self.canvas_widget: QWidget = CanvasAreaSlot(self.workspace_container)
        self.pagination_bar: QWidget = PaginationBarSlot(self.workspace_container)

        self.workspace_separator = self._create_separator(self.workspace_container)
        self.inspector: QWidget = InspectorSlot(self.workspace_container)

        self._workspace_layout.addWidget(self.header_bar)
        self._workspace_layout.addWidget(self.canvas_widget, 1)
        self._workspace_layout.addWidget(self.pagination_bar)
        self._workspace_layout.addWidget(self.workspace_separator)
        self._workspace_layout.addWidget(self.inspector)

        self.main_splitter.addWidget(self.workspace_container)

        # ----------------------------------------------------------------------
        # Правая панель каталога действий (Action Library Drawer)
        # ----------------------------------------------------------------------
        self.drawer_container = QWidget(self.main_splitter)
        self.drawer_container.setObjectName("drawerContainer")
        self.drawer_container.setMinimumWidth(DRAWER_MIN_WIDTH)
        self.drawer_container.setMaximumWidth(DRAWER_MAX_WIDTH)

        self._drawer_layout = QVBoxLayout(self.drawer_container)
        self._drawer_layout.setContentsMargins(12, 12, 12, 12)
        self._drawer_layout.setSpacing(8)

        self.search_slot = SearchSlot(self.drawer_container)
        self.drawer_separator = self._create_separator(self.drawer_container)
        self.action_list_slot = ActionListSlot(self.drawer_container)

        self._drawer_layout.addWidget(self.search_slot)
        self._drawer_layout.addWidget(self.drawer_separator)
        self._drawer_layout.addWidget(self.action_list_slot, 1)

        self.action_drawer: Optional[QWidget] = None

        self.main_splitter.addWidget(self.drawer_container)

        # ----------------------------------------------------------------------
        # Настройка сплиттера: 70% левая колонка / 30% правая колонка
        # ----------------------------------------------------------------------
        self.main_splitter.setStretchFactor(0, 7)
        self.main_splitter.setStretchFactor(1, 3)
        self.main_splitter.setSizes([756, 324])

    @staticmethod
    def _create_separator(parent: QWidget) -> QFrame:
        """Создает стилизованную тонкую горизонтальную линию разделителя."""
        separator = QFrame(parent)
        separator.setObjectName("editorSeparator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        return separator

    def _center_on_primary_screen(self) -> None:
        """Центрирует окно на доступной рабочей области основного монитора."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            geo = self.frameGeometry()
            geo.moveCenter(screen_geo.center())
            self.move(geo.topLeft())

    # ==========================================================================
    # Localization-First Protocol (retranslate_ui & EventBus)
    # ==========================================================================

    def _handle_language_changed(self, lang_code: str) -> None:
        """Реактивный обработчик сигнала смены языка из EventBus."""
        from core.i18n import I18nManager
        mgr = I18nManager()
        if mgr.current_language != lang_code:
            mgr.set_language(lang_code, emit_signal=False)
        self.retranslate_ui()

    def _on_undo_clean_changed(self, is_clean: bool) -> None:
        """Реакция на изменение состояния чистоты UndoStack."""
        self._is_dirty = not is_clean
        self._update_window_title()
        if self._is_dirty and getattr(self, "autosave_enabled", False):
            self._autosave_timer.start(500)

    def _on_autosave_timeout(self) -> None:
        """Таймер автосохранения (дебаунсер 500 мс)."""
        if self._is_dirty:
            logger.info("Autosave triggered after debounce timeout.")
            self.save_configuration()

    def _update_window_title(self) -> None:
        """Формирует заголовок окна с индикатором dirty-state (*)"""
        base_title = t("deck.editor.window.title")
        if self._is_dirty:
            self.setWindowTitle(f"{base_title} *")
        else:
            self.setWindowTitle(base_title)

    def retranslate_ui(self) -> None:
        """
        Обновляет локализацию заголовка окна и каскадно инициирует retranslate_ui()
        у всех смонтированных дочерних компонентов.
        """
        self._update_window_title()

        if self.header_bar is not None and hasattr(self.header_bar, "retranslate_ui") and callable(self.header_bar.retranslate_ui):
            try:
                self.header_bar.retranslate_ui()
            except Exception as exc:
                logger.warning("Error retranslating header bar: %s", exc)

        if self.canvas_widget is not None and hasattr(self.canvas_widget, "retranslate_ui") and callable(self.canvas_widget.retranslate_ui):
            try:
                self.canvas_widget.retranslate_ui()
            except Exception as exc:
                logger.warning("Error retranslating canvas widget: %s", exc)

        if self.pagination_bar is not None and hasattr(self.pagination_bar, "retranslate_ui") and callable(self.pagination_bar.retranslate_ui):
            try:
                self.pagination_bar.retranslate_ui()
            except Exception as exc:
                logger.warning("Error retranslating pagination bar: %s", exc)

        if self.inspector is not None and hasattr(self.inspector, "retranslate_ui") and callable(self.inspector.retranslate_ui):
            try:
                self.inspector.retranslate_ui()
            except Exception as exc:
                logger.warning("Error retranslating inspector: %s", exc)

        if self.action_drawer is not None and hasattr(self.action_drawer, "retranslate_ui") and callable(self.action_drawer.retranslate_ui):
            try:
                self.action_drawer.retranslate_ui()
            except Exception as exc:
                logger.warning("Error retranslating action drawer: %s", exc)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Перехват закрытия окна: проверка dirty-state и диалог сохранения."""
        if (
            getattr(self, "_is_dirty", False)
            and not getattr(self, "_skip_close_dialog", False)
        ):
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(t("deck.editor.dialogs.unsaved_title"))
            msg_box.setText(t("deck.editor.dialogs.unsaved_message"))
            btn_save = msg_box.addButton(t("deck.editor.dialogs.save"), QMessageBox.AcceptRole)
            btn_discard = msg_box.addButton(t("deck.editor.dialogs.discard"), QMessageBox.DestructiveRole)
            btn_cancel = msg_box.addButton(t("deck.editor.dialogs.cancel"), QMessageBox.RejectRole)
            msg_box.setDefaultButton(btn_save)
            msg_box.exec()
            clicked = msg_box.clickedButton()
            if clicked == btn_save:
                if not self.save_configuration():
                    event.ignore()
                    return
            elif clicked == btn_discard:
                pass
            else:
                event.ignore()
                return

        try:
            bus.language_changed.disconnect(self._handle_language_changed)
        except (RuntimeError, TypeError):
            pass
        try:
            bus.deck_page_changed.disconnect(self._on_bus_deck_page_changed)
        except (RuntimeError, TypeError):
            pass
        if hasattr(self.header_bar, "cleanup") and callable(self.header_bar.cleanup):
            try:
                self.header_bar.cleanup()
            except Exception:
                pass
        super().closeEvent(event)

    # ==========================================================================
    # Публичный API замены слотов-плейсхолдеров
    # ==========================================================================

    def set_header_bar(self, widget: QWidget) -> None:
        """Заменяет слот заголовка на указанный виджет."""
        if self.header_bar is not None and self.header_bar != widget:
            self._workspace_layout.replaceWidget(self.header_bar, widget)
            self.header_bar.setParent(None)
            self.header_bar.deleteLater()
        elif self.header_bar is None:
            self._workspace_layout.insertWidget(0, widget)
        self.header_bar = widget

        if isinstance(widget, EditorHeaderBar):
            widget.device_changed.connect(self._on_header_device_changed)
            widget.profile_changed.connect(self._on_header_profile_changed)
            widget.create_profile_requested.connect(self._on_header_create_profile_requested)
            widget.action_clicked.connect(self._on_header_action_clicked)
            widget.save_requested.connect(self.save_configuration)

    def _on_header_device_changed(self, device_id: str) -> None:
        logger.info("Header device selected: %s", device_id)

    def _on_header_profile_changed(self, profile_name: str) -> None:
        logger.info("Header profile selected: %s", profile_name)

    def _on_header_create_profile_requested(self) -> None:
        logger.info("Header create profile requested")

    def _on_header_action_clicked(self, action_id: str) -> None:
        logger.info("Header action clicked: %s", action_id)

    def set_canvas_widget(self, widget: QWidget) -> None:
        """Заменяет слот холста на указанный растягиваемый виджет."""
        if self.canvas_widget is not None and self.canvas_widget != widget:
            self._workspace_layout.replaceWidget(self.canvas_widget, widget)
            self.canvas_widget.setParent(None)
            self.canvas_widget.deleteLater()
        elif self.canvas_widget is None:
            self._workspace_layout.insertWidget(1, widget)
        self._workspace_layout.setStretchFactor(widget, 1)
        self.canvas_widget = widget

        if isinstance(widget, DeckCanvasWidget):
            widget.selection_changed.connect(self._on_canvas_selection_changed)
            widget.selection_cleared.connect(self._on_canvas_selection_cleared)
            widget.action_dropped.connect(self._on_canvas_action_dropped)
            widget.slot_dropped.connect(self._on_canvas_slot_dropped)

    def _on_canvas_action_dropped(self, slot_idx: int, action_data: dict) -> None:
        """Обработка сброса действия из библиотеки на ячейку холста."""
        old_dto = self.get_slot_dto(slot_idx)
        title_text = action_data.get("title", "")
        category_key = action_data.get("category", "")
        cat_name = t(category_key) if category_key else ""
        category_text = f"{cat_name}: {title_text}" if cat_name else title_text

        new_dto = old_dto.model_copy(deep=True)
        new_dto.title = title_text
        new_dto.icon = action_data.get("icon", "🖲️")
        new_dto.category = category_text
        new_dto.action_type = action_data.get("id", "")
        new_dto.action_params = {}

        cmd = AssignActionCommand(self, slot_idx, new_dto, old_dto)
        self._undo_stack.push(cmd)

    def _on_canvas_slot_dropped(self, src_slot: int, dst_slot: int, is_copy: bool) -> None:
        """Обработка перетаскивания и сброса между слотами холста (Swap / Copy)."""
        if src_slot == dst_slot:
            return
        cmd = SwapButtonsCommand(self, src_slot, dst_slot, is_copy=is_copy)
        self._undo_stack.push(cmd)

    def get_slot_dto(self, slot_idx: int) -> ButtonSlotDTO:
        """Возвращает глубокую копию DTO кнопки слота холста."""
        dto = self._button_slots.get(slot_idx)
        if dto is not None:
            return dto.model_copy(deep=True) if hasattr(dto, "model_copy") else ButtonSlotDTO(**dto.__dict__)
        return ButtonSlotDTO(slot_index=slot_idx)

    def apply_slot_dto(self, slot_idx: int, dto: ButtonSlotDTO, clear: bool = False) -> None:
        """Применяет DTO к слоту, обновляя модель, превью ячейки холста и инспектор."""
        self._is_applying_command = True
        try:
            cloned = dto.model_copy(deep=True) if hasattr(dto, "model_copy") else ButtonSlotDTO(**dto.__dict__)
            cloned.slot_index = slot_idx
            self._button_slots[slot_idx] = cloned

            if isinstance(self.canvas_widget, DeckCanvasWidget):
                if clear or (not cloned.title and not cloned.hotkey and (not cloned.icon or cloned.icon == "🖲️")):
                    self.canvas_widget.clear_cell(slot_idx)
                    if self.canvas_widget.get_selected_target() == ("button", slot_idx):
                        self.canvas_widget.clear_selection()
                else:
                    self.canvas_widget.update_cell_preview(slot_idx, "title", cloned.title)
                    self.canvas_widget.update_cell_preview(slot_idx, "icon", cloned.icon)
                    self.canvas_widget.update_cell_preview(slot_idx, "category", cloned.category)

            if isinstance(self.inspector, KeyPropertyInspector):
                if getattr(self.inspector, "_current_slot_index", None) == slot_idx:
                    if clear:
                        self.inspector.show_placeholder()
                    else:
                        self.inspector.load_button_slot(slot_idx, cloned)
        finally:
            self._is_applying_command = False

    def apply_property_value(self, slot_idx: int, prop_name: str, val: Any) -> None:
        """Применяет изменение отдельного свойства кнопки к модели и UI."""
        self._is_applying_command = True
        try:
            dto = self._button_slots.get(slot_idx)
            if dto is not None:
                if prop_name == "title":
                    dto.title = str(val) if val is not None else ""
                elif prop_name == "hotkey":
                    dto.hotkey = str(val) if val is not None else ""
                elif prop_name == "action_type":
                    dto.action_type = str(val) if val is not None else ""
                elif prop_name == "category":
                    dto.category = str(val) if val is not None else ""
                elif prop_name == "icon":
                    dto.icon = str(val) if val is not None else ""
                elif prop_name == "color_accent":
                    dto.color_accent = str(val) if val is not None else "#38bdf8"
                elif prop_name == "action_params":
                    dto.action_params = dict(val) if isinstance(val, dict) else {}

            if isinstance(self.canvas_widget, DeckCanvasWidget):
                self.canvas_widget.update_cell_preview(slot_idx, prop_name, val)

            if isinstance(self.inspector, KeyPropertyInspector):
                if getattr(self.inspector, "_current_slot_index", None) == slot_idx:
                    if dto is not None:
                        self.inspector.load_button_slot(slot_idx, dto)
        finally:
            self._is_applying_command = False

    def _on_canvas_selection_changed(self, target_type: str, target_id: object) -> None:
        """
        Связывает выбор элемента на холсте с переключением форм инспектора свойств.
        """
        logger.info("Canvas selection changed: type=%s, id=%s", target_type, target_id)
        if not isinstance(self.inspector, KeyPropertyInspector):
            return

        if target_type == "button" and isinstance(target_id, int):
            slot_idx = target_id
            dto = self._button_slots.setdefault(
                slot_idx, ButtonSlotDTO(slot_index=slot_idx)
            )
            self.inspector.load_button_slot(slot_idx, dto)
        elif target_type == "touchbar" and isinstance(target_id, str):
            sec_type = target_id
            if sec_type == "media":
                dto = self._touchbar_media
            elif sec_type == "clock":
                dto = self._touchbar_clock
            elif sec_type == "telemetry":
                dto = self._touchbar_telemetry
            else:
                dto = None
            self.inspector.load_touchbar_section(sec_type, dto)

    def _on_canvas_selection_cleared(self) -> None:
        """
        Сбрасывает инспектор в плейсхолдер при снятии выделения на холсте.
        """
        logger.info("Canvas selection cleared")
        if isinstance(self.inspector, KeyPropertyInspector):
            self.inspector.show_placeholder()

    def _on_inspector_button_updated(self, slot_idx: int, prop: str, val: object) -> None:
        """
        Обрабатывает изменение свойств кнопки в инспекторе:
        создает команду UpdatePropertyCommand в QUndoStack.
        """
        if self._is_applying_command:
            return
        logger.info("Inspector button updated: slot=%s, prop=%s, val=%s", slot_idx, prop, val)
        dto = self._button_slots.get(slot_idx)
        old_val = getattr(dto, prop, None) if dto else None
        if old_val == val:
            return
        cmd = UpdatePropertyCommand(self, slot_idx, prop, val, old_val)
        self._undo_stack.push(cmd)

    def update_cell_icon(self, slot_idx: int, icon_str: str) -> None:
        """Обновляет иконку слота через QUndoStack."""
        if self._is_applying_command:
            return
        dto = self._button_slots.get(slot_idx)
        old_val = dto.icon if dto else ""
        if old_val == icon_str:
            return
        cmd = UpdatePropertyCommand(self, slot_idx, "icon", icon_str, old_val)
        self._undo_stack.push(cmd)

    def _on_inspector_touchbar_updated(self, sec_type: str, prop: str, val: object) -> None:
        """
        Обрабатывает изменение настроек секции тачбара в инспекторе.
        """
        logger.info("Inspector touchbar updated: sec=%s, prop=%s, val=%s", sec_type, prop, val)
        if sec_type == "media" and hasattr(self._touchbar_media, prop):
            setattr(self._touchbar_media, prop, val)
            self._is_dirty = True
        elif sec_type == "clock" and hasattr(self._touchbar_clock, prop):
            setattr(self._touchbar_clock, prop, val)
            self._is_dirty = True
        elif sec_type == "telemetry" and hasattr(self._touchbar_telemetry, prop):
            setattr(self._touchbar_telemetry, prop, val)
            self._is_dirty = True

    def _on_inspector_slot_cleared(self, slot_idx: int) -> None:
        """
        Обрабатывает удаление действия корзиной 🗑️ через ClearSlotCommand.
        """
        if self._is_applying_command:
            return
        logger.info("Inspector slot cleared: slot=%s", slot_idx)
        old_dto = self.get_slot_dto(slot_idx)
        cmd = ClearSlotCommand(self, slot_idx, old_dto)
        self._undo_stack.push(cmd)

    def set_pagination_bar(self, widget: QWidget) -> None:
        """Заменяет слот панели пагинации на указанный виджет."""
        if self.pagination_bar is not None and self.pagination_bar != widget:
            self._workspace_layout.replaceWidget(self.pagination_bar, widget)
            self.pagination_bar.setParent(None)
            self.pagination_bar.deleteLater()
        elif self.pagination_bar is None:
            self._workspace_layout.insertWidget(2, widget)
        self.pagination_bar = widget

        if isinstance(widget, PageNavigationBar):
            widget.page_changed.connect(self._on_pagination_page_changed)
            widget.add_page_requested.connect(self._on_pagination_add_page_requested)
            widget.rename_page_requested.connect(self._on_pagination_rename_page_requested)
            widget.duplicate_page_requested.connect(self._on_pagination_duplicate_page_requested)
            widget.clear_page_requested.connect(self._on_pagination_clear_page_requested)
            widget.delete_page_requested.connect(self._on_pagination_delete_page_requested)

    def _on_pagination_page_changed(self, page_index: int) -> None:
        logger.info("Pagination page changed: %s", page_index)
        # Автосохранение изменений текущей страницы перед переходом на другую (только если были правки)
        if getattr(self, "_is_dirty", False) and self._button_slots and hasattr(self, "active_page_id") and self.active_page_id:
            try:
                self.save_configuration()
            except Exception as exc:
                logger.warning("Auto-saving page configuration before page switch failed: %s", exc)

        self._undo_stack.clear()
        self._is_dirty = False
        self._update_window_title()

        self._current_page_index = page_index
        from modules.deck.editor.adapter import DeckConfigAdapter
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)

        page_cfg = None
        idx = page_index - 1
        if 0 <= idx < len(root_config.pages):
            page_cfg = root_config.pages[idx]
            self.active_page_id = page_cfg.id
            page_title = page_cfg.name
        else:
            self.active_page_id = f"page_{page_index}"
            page_title = ""

        if hasattr(self.canvas_widget, "set_page") and callable(self.canvas_widget.set_page):
            self.canvas_widget.set_page(page_index)
        if hasattr(self.canvas_widget, "set_page_title") and callable(self.canvas_widget.set_page_title):
            self.canvas_widget.set_page_title(page_title)

        self.load_configuration(page_id=self.active_page_id)

        # Синхронизация с сенсорной панелью DuckDeck
        if not self._is_syncing_page and page_cfg is not None and len(page_cfg.buttons) > 0:
            self._is_syncing_page = True
            try:
                bus.deck_page_changed.emit(page_cfg.id)
            finally:
                self._is_syncing_page = False

    def _on_bus_deck_page_changed(self, page_id: str) -> None:
        """Реакция на переключение страницы на сенсорной панели DuckDeck."""
        if self._is_syncing_page:
            return
        if getattr(self, "_is_dirty", False) and self._button_slots and hasattr(self, "active_page_id") and self.active_page_id:
            try:
                self.save_configuration()
            except Exception as exc:
                logger.warning("Auto-saving page configuration before remote page switch failed: %s", exc)

        self._undo_stack.clear()
        self._is_dirty = False
        self._update_window_title()

        from modules.deck.editor.adapter import DeckConfigAdapter
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)

        found_idx = -1
        for idx, p in enumerate(root_config.pages):
            if p.id == page_id:
                found_idx = idx
                break

        if found_idx != -1:
            target_page_idx = found_idx + 1
            self._is_syncing_page = True
            try:
                self._current_page_index = target_page_idx
                self.active_page_id = page_id
                if hasattr(self.pagination_bar, "set_page_count"):
                    self.pagination_bar.set_page_count(len(root_config.pages))
                if hasattr(self.pagination_bar, "set_current_page"):
                    self.pagination_bar.set_current_page(target_page_idx)
                if hasattr(self.canvas_widget, "set_page"):
                    self.canvas_widget.set_page(target_page_idx)
                if hasattr(self.canvas_widget, "set_page_title"):
                    self.canvas_widget.set_page_title(root_config.pages[found_idx].name)
                self.load_configuration(page_id=page_id)
            finally:
                self._is_syncing_page = False

    def _on_pagination_add_page_requested(self) -> None:
        """Добавление новой страницы по нажатию на кнопку '+'."""
        logger.info("Pagination add page requested")
        if getattr(self, "_is_dirty", False) and self._button_slots and hasattr(self, "active_page_id") and self.active_page_id:
            try:
                self.save_configuration()
            except Exception as exc:
                logger.warning("Auto-saving page configuration before adding new page failed: %s", exc)
        from modules.deck.editor.adapter import DeckConfigAdapter
        from modules.deck.models import DeckPageConfig
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)

        new_page_index = len(root_config.pages) + 1
        new_page_id = f"page_{new_page_index}"

        # Создаем и сохраняем новую страницу в конфиг
        new_page = DeckPageConfig(
            id=new_page_id,
            name="",
            grid_rows=2,
            grid_cols=5,
            buttons=[],
        )
        root_config.pages.append(new_page)
        DeckConfigAdapter.save_deck_config_atomic(root_config, self.config_path)
        bus.deck_config_updated.emit()

        if isinstance(self.pagination_bar, PageNavigationBar):
            self.pagination_bar.set_page_count(new_page_index)
            self.pagination_bar.set_current_page(new_page_index)
        self._on_pagination_page_changed(new_page_index)

    def _on_pagination_rename_page_requested(self, page_index: int) -> None:
        """Контекстное меню: переименование страницы."""
        from modules.deck.editor.adapter import DeckConfigAdapter
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)

        idx = page_index - 1
        current_name = ""
        page_id = f"page_{page_index}"
        if 0 <= idx < len(root_config.pages):
            current_name = root_config.pages[idx].name
            page_id = root_config.pages[idx].id

        new_name, ok = QInputDialog.getText(
            self,
            t("deck.editor.canvas.pagination.rename_dialog_title"),
            t("deck.editor.canvas.pagination.rename_dialog_label"),
            text=current_name,
        )
        if ok:
            clean_name = new_name.strip()
            updated_root = DeckConfigAdapter.rename_page(root_config, page_id, clean_name)
            DeckConfigAdapter.save_deck_config_atomic(updated_root, self.config_path)
            if hasattr(self.canvas_widget, "set_page_title"):
                self.canvas_widget.set_page_title(clean_name)
            bus.deck_config_updated.emit()
            logger.info("Page %d renamed to '%s'", page_index, clean_name)

    def _on_pagination_duplicate_page_requested(self, page_index: int) -> None:
        """Контекстное меню: дублирование страницы."""
        from modules.deck.editor.adapter import DeckConfigAdapter
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)

        suffix = " " + t("deck.editor.canvas.pagination.duplicate_suffix")
        updated_root, new_page = DeckConfigAdapter.duplicate_page(
            root_config, page_index - 1, copy_suffix=suffix
        )
        DeckConfigAdapter.save_deck_config_atomic(updated_root, self.config_path)
        bus.deck_config_updated.emit()

        new_count = len(updated_root.pages)
        if isinstance(self.pagination_bar, PageNavigationBar):
            self.pagination_bar.set_page_count(new_count)
            self.pagination_bar.set_current_page(new_count)
        self._on_pagination_page_changed(new_count)
        logger.info("Page %d duplicated to new page '%s' (idx %d)", page_index, new_page.id, new_count)

    def _on_pagination_clear_page_requested(self, page_index: int) -> None:
        """Контекстное меню: очистка всех слотов страницы без ее удаления."""
        from modules.deck.editor.adapter import DeckConfigAdapter
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)

        idx = page_index - 1
        page_name = ""
        if 0 <= idx < len(root_config.pages):
            page_name = root_config.pages[idx].name

        display_name = page_name or str(page_index)
        confirm = QMessageBox.question(
            self,
            t("deck.editor.canvas.pagination.clear_confirm_title"),
            t("deck.editor.canvas.pagination.clear_confirm_message", name=display_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self._button_slots = {i: ButtonSlotDTO(slot_index=i) for i in range(10)}

            if isinstance(self.canvas_widget, DeckCanvasWidget):
                for i in range(10):
                    self.canvas_widget.clear_cell(i)
                self.canvas_widget.clear_selection()

            if hasattr(self, "inspector") and hasattr(self.inspector, "show_placeholder"):
                self.inspector.show_placeholder()

            page_id = self.active_page_id
            updated_root = DeckConfigAdapter.apply_slots_to_page(
                root_config=root_config,
                page_id_or_index=page_id,
                slots=self._button_slots,
            )
            DeckConfigAdapter.save_deck_config_atomic(updated_root, self.config_path)
            bus.deck_config_updated.emit()
            self._undo_stack.clear()
            self._is_dirty = False
            self._update_window_title()
            logger.info("Page %d ('%s') cleared.", page_index, page_id)

    def _on_pagination_delete_page_requested(self, page_index: int) -> None:
        """Контекстное меню: удаление страницы (недоступно, если осталась всего 1 страница)."""
        from modules.deck.editor.adapter import DeckConfigAdapter
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)

        if len(root_config.pages) <= 1:
            return

        idx = page_index - 1
        page_name = ""
        if 0 <= idx < len(root_config.pages):
            page_name = root_config.pages[idx].name

        display_name = page_name or str(page_index)
        confirm = QMessageBox.question(
            self,
            t("deck.editor.canvas.pagination.delete_confirm_title"),
            t("deck.editor.canvas.pagination.delete_confirm_message", name=display_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            updated_root = DeckConfigAdapter.delete_page(root_config, idx)
            DeckConfigAdapter.save_deck_config_atomic(updated_root, self.config_path)
            bus.deck_config_updated.emit()

            new_count = len(updated_root.pages)
            if isinstance(self.pagination_bar, PageNavigationBar):
                self.pagination_bar.set_page_count(new_count)

            new_target = max(1, min(page_index, new_count))
            if hasattr(self.pagination_bar, "set_current_page"):
                self.pagination_bar.set_current_page(new_target)
            self._on_pagination_page_changed(new_target)
            logger.info("Page %d deleted, switched to %d", page_index, new_target)

    def set_page(self, page_id: str | int) -> None:
        """
        Переключает активную страницу редактора (холст и панель пагинации).
        Поддерживает форматы: int (1..N), str ('page_0', 'page_1', '1', 'default', 'grid4x6').
        """
        from modules.deck.editor.adapter import DeckConfigAdapter
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)

        page_idx = 1
        if isinstance(page_id, int):
            page_idx = max(1, page_id)
        elif isinstance(page_id, str):
            found_idx = -1
            for idx, p in enumerate(root_config.pages):
                if p.id == page_id:
                    found_idx = idx
                    break
            if found_idx != -1:
                page_idx = found_idx + 1
            elif page_id.startswith("page_"):
                try:
                    num = int(page_id.split("_")[1])
                    page_idx = max(1, num + 1)
                except (ValueError, IndexError):
                    page_idx = 1
            else:
                try:
                    num = int(page_id)
                    page_idx = max(1, num)
                except ValueError:
                    page_idx = 1

        if self.pagination_bar is not None:
            if hasattr(self.pagination_bar, "set_page_count"):
                self.pagination_bar.set_page_count(max(len(root_config.pages), page_idx))
            if hasattr(self.pagination_bar, "set_current_page"):
                try:
                    self.pagination_bar.set_current_page(page_idx)
                except Exception as exc:
                    logger.warning("Error setting pagination page: %s", exc)

        self._on_pagination_page_changed(page_idx)

    def set_inspector_widget(self, widget: QWidget) -> None:
        """Заменяет слот инспектора свойств на указанный виджет."""
        if self.inspector is not None and self.inspector != widget:
            self._workspace_layout.replaceWidget(self.inspector, widget)
            self.inspector.setParent(None)
            self.inspector.deleteLater()
        elif self.inspector is None:
            self._workspace_layout.addWidget(widget)
        self.inspector = widget

        if isinstance(widget, KeyPropertyInspector):
            widget.button_updated.connect(self._on_inspector_button_updated)
            widget.touchbar_updated.connect(self._on_inspector_touchbar_updated)
            widget.slot_cleared.connect(self._on_inspector_slot_cleared)
            widget.test_action_requested.connect(self._on_test_action_requested)

    def set_action_drawer(self, widget: QWidget) -> None:
        """Монтирует панель библиотеки действий в правую колонку сплиттера."""
        if self.action_drawer is not None and self.action_drawer != widget:
            self._drawer_layout.replaceWidget(self.action_drawer, widget)
            self.action_drawer.setParent(None)
            self.action_drawer.deleteLater()
        else:
            while self._drawer_layout.count():
                item = self._drawer_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
            self._drawer_layout.addWidget(widget, 1)
        self.action_drawer = widget

        if hasattr(widget, "action_picked"):
            try:
                widget.action_picked.connect(self._on_action_drawer_action_picked)
            except Exception:
                pass

    def _on_action_drawer_action_picked(self, item_dto: object) -> None:
        """
        Обрабатывает выбор действия в каталоге через AssignActionCommand.
        """
        if not hasattr(item_dto, "id") or not hasattr(item_dto, "icon"):
            return

        selected_target = None
        if isinstance(self.canvas_widget, DeckCanvasWidget):
            selected_target = self.canvas_widget.get_selected_target()

        if selected_target is not None and selected_target[0] == "button":
            slot_idx = int(selected_target[1])
            old_dto = self.get_slot_dto(slot_idx)

            title_text = item_dto.get_title() if hasattr(item_dto, "get_title") else ""
            category_key = getattr(item_dto, "category_key", "")
            cat_name = t(category_key) if category_key else ""
            category_text = f"{cat_name}: {title_text}" if cat_name else title_text

            new_dto = old_dto.model_copy(deep=True)
            new_dto.title = title_text
            new_dto.icon = getattr(item_dto, "icon", "🖲️")
            new_dto.category = category_text
            new_dto.action_type = getattr(item_dto, "id", "")
            new_dto.action_params = {}

            logger.info(
                "Assigned action '%s' to slot %d: title='%s', icon='%s'",
                new_dto.action_type,
                slot_idx,
                new_dto.title,
                new_dto.icon,
            )

            cmd = AssignActionCommand(self, slot_idx, new_dto, old_dto)
            self._undo_stack.push(cmd)

    def _on_test_action_requested(self, slot_idx: int) -> None:
        """Безопасный тестовый запуск действия выбранной кнопки без потери фокуса."""
        dto = self._button_slots.get(slot_idx)
        if dto is None:
            return
        from modules.deck.editor.adapter import DeckConfigAdapter
        from modules.deck.action_dispatcher import DeckActionDispatcher
        btn_config = DeckConfigAdapter.dto_to_slot(dto)
        if btn_config and btn_config.action:
            logger.info("Executing test action for slot %d: %s", slot_idx, btn_config.action.action_type)
            DeckActionDispatcher.execute_action(btn_config.action)

    # ==========================================================================
    # I/O и сохранение конфигурации (DeckConfigAdapter & EventBus)
    # ==========================================================================

    def save_configuration(self) -> bool:
        """
        Сохраняет конфигурацию слотов кнопок через DeckConfigAdapter.
        Атомарно пишет в self.config_path, вызывает анимацию успеха
        в header_bar и эмитирует bus.deck_config_updated.
        """
        try:
            from modules.deck.editor.adapter import DeckConfigAdapter

            # 1. Загрузка исходного DeckRootConfig из файла
            root_config = DeckConfigAdapter.load_deck_config(self.config_path)

            # 2. Применение текущих слотов self._button_slots к активной странице
            page_id = getattr(self, "active_page_id", "default")
            updated_root = DeckConfigAdapter.apply_slots_to_page(
                root_config=root_config,
                page_id_or_index=page_id,
                slots=self._button_slots,
            )

            # 3. Атомарное сохранение файла
            saved = DeckConfigAdapter.save_deck_config_atomic(updated_root, self.config_path)
            if not saved:
                logger.error("Failed to atomically save deck configuration to '%s'", self.config_path)
                return False

            # 4. Анимация успеха кнопки на тулбаре
            if self.header_bar is not None and hasattr(self.header_bar, "show_save_success"):
                try:
                    self.header_bar.show_save_success()
                except Exception as exc:
                    logger.warning("Error showing save success in header bar: %s", exc)

            # 5. Эмиссия глобального сигнала обновления конфигурации
            self._undo_stack.setClean()
            self._is_dirty = False
            self._update_window_title()
            bus.deck_config_updated.emit()
            logger.info("Deck configuration successfully saved and bus.deck_config_updated emitted.")
            return True

        except Exception as exc:
            logger.error("Unexpected error in save_configuration: %s", exc, exc_info=True)
            return False

    def load_configuration(
        self,
        config_path: Optional[str] = None,
        page_id: Optional[Union[str, int]] = None,
    ) -> None:
        """
        Загружает слоты кнопок из файла конфигурации через DeckConfigAdapter.
        """
        if config_path:
            self.config_path = config_path
        if page_id is not None:
            self.active_page_id = page_id

        from modules.deck.editor.adapter import DeckConfigAdapter
        root_config = DeckConfigAdapter.load_deck_config(self.config_path)
        page = DeckConfigAdapter.get_page(root_config, self.active_page_id)
        if page is not None:
            self.active_page_id = page.id
        elif root_config.pages:
            self.active_page_id = root_config.pages[0].id
            page = root_config.pages[0]

        slots = DeckConfigAdapter.load_page_slots(root_config, self.active_page_id)
        self._button_slots = slots

        # Обновление подписи страницы на холсте
        if hasattr(self.canvas_widget, "set_page_title"):
            self.canvas_widget.set_page_title(page.name if page and page.name else "")

        if hasattr(self.pagination_bar, "set_page_count"):
            target_count = max(len(root_config.pages), getattr(self, "_current_page_index", 1))
            self.pagination_bar.set_page_count(target_count)
            self.pagination_bar.set_current_page(getattr(self, "_current_page_index", 1))

        if isinstance(self.canvas_widget, DeckCanvasWidget):
            for idx, dto in slots.items():
                is_empty = (
                    not dto.title
                    and not dto.hotkey
                    and (not dto.icon or dto.icon == "🖲️")
                    and not getattr(dto, "original_config", None)
                )
                if is_empty:
                    self.canvas_widget.clear_cell(idx)
                else:
                    self.canvas_widget.update_cell_preview(idx, "title", dto.title)
                    self.canvas_widget.update_cell_preview(idx, "icon", dto.icon)
                    self.canvas_widget.update_cell_preview(idx, "category", dto.category)

            # Если была выделена кнопка, обновляем инспектор актуальными данными
            sel = self.canvas_widget.get_selected_target()
            if sel is not None and sel[0] == "button" and isinstance(self.inspector, KeyPropertyInspector):
                slot_idx = int(sel[1])
                if slot_idx in self._button_slots:
                    self.inspector.load_button_slot(slot_idx, self._button_slots[slot_idx])

        self._undo_stack.clear()
        self._is_dirty = False
        self._update_window_title()

    # ==========================================================================
    # Свойства-алиасы для обратной и прямой совместимости
    # ==========================================================================

    @property
    def header_bar_slot(self) -> QWidget:
        """Алиас для слота / виджета заголовка."""
        return self.header_bar

    @property
    def header_bar_widget(self) -> QWidget:
        """Алиас для виджета панели заголовка."""
        return self.header_bar

    @header_bar_widget.setter
    def header_bar_widget(self, widget: QWidget) -> None:
        self.set_header_bar(widget)

    @property
    def canvas(self) -> QWidget:
        """Алиас для виджета холста."""
        return self.canvas_widget

    @property
    def canvas_slot(self) -> QWidget:
        """Алиас для слота / виджета холста."""
        return self.canvas_widget

    @property
    def pagination_slot(self) -> QWidget:
        """Алиас для слота / виджета пагинации."""
        return self.pagination_bar

    @property
    def inspector_slot(self) -> QWidget:
        """Алиас для слота / виджета инспектора свойств."""
        return self.inspector

    @property
    def inspector_widget(self) -> QWidget:
        """Алиас для виджета инспектора свойств."""
        return self.inspector

    @inspector_widget.setter
    def inspector_widget(self, widget: QWidget) -> None:
        self.set_inspector_widget(widget)


if __name__ == "__main__":
    try:
        from core.dpi import init_dpi_awareness
        init_dpi_awareness()
    except Exception:
        pass

    app = QApplication.instance() or QApplication(sys.argv)
    window = DeckEditorWindow()
    window.show()
    sys.exit(app.exec())
