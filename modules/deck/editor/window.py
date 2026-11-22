"""
Главное окно конфигуратора макро-панели и тачбара DuckDeck (DeckEditorWindow).
Реализует двухпанельную компоновку на базе QSplitter (70% рабочая область / 30% библиотека действий),
реактивный протокол Localization-First (retranslate_ui, шина bus.language_changed)
и публичный API замены слотов-плейсхолдеров на функциональные виджеты.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.event_bus import bus
from core.i18n import t
from modules.deck.editor.actions_registry import get_default_action_catalog
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

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.resize(WINDOW_DEFAULT_SIZE[0], WINDOW_DEFAULT_SIZE[1])
        self.setMinimumSize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])

        # Презентационная модель данных окна редактора
        self.config_path: str = "config/deck_config.json"
        self.active_page_id: str | int = "default"
        self._button_slots: dict[int, ButtonSlotDTO] = {
            i: ButtonSlotDTO(slot_index=i) for i in range(10)
        }
        self._touchbar_media = TouchbarMediaDTO()
        self._touchbar_clock = TouchbarClockDTO()
        self._touchbar_telemetry = TouchbarTelemetryDTO()

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

        # Хоткей быстрого сохранения конфигурации Ctrl+S
        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._save_shortcut.activated.connect(self.save_configuration)

        self.retranslate_ui()
        bus.language_changed.connect(self._handle_language_changed)

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

    def retranslate_ui(self) -> None:
        """
        Обновляет локализацию заголовка окна и каскадно инициирует retranslate_ui()
        у всех смонтированных дочерних компонентов.
        """
        self.setWindowTitle(t("deck.editor.window.title"))

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
        """Безопасное отключение подписки на шину событий при закрытии окна."""
        try:
            bus.language_changed.disconnect(self._handle_language_changed)
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
        обновляет локальный DTO и транслирует точечное превью в ячейку холста.
        """
        logger.info("Inspector button updated: slot=%s, prop=%s, val=%s", slot_idx, prop, val)
        dto = self._button_slots.get(slot_idx)
        if dto is not None:
            if prop == "title":
                dto.title = str(val) if val is not None else ""
            elif prop == "hotkey":
                dto.hotkey = str(val) if val is not None else ""
            elif prop == "action_type":
                dto.action_type = str(val) if val is not None else ""
            elif prop == "category":
                dto.category = str(val) if val is not None else ""
            elif prop == "icon":
                dto.icon = str(val) if val is not None else ""
        if isinstance(self.canvas_widget, DeckCanvasWidget):
            self.canvas_widget.update_cell_preview(slot_idx, prop, val)

    def _on_inspector_touchbar_updated(self, sec_type: str, prop: str, val: object) -> None:
        """
        Обрабатывает изменение настроек секции тачбара в инспекторе.
        """
        logger.info("Inspector touchbar updated: sec=%s, prop=%s, val=%s", sec_type, prop, val)
        if sec_type == "media" and hasattr(self._touchbar_media, prop):
            setattr(self._touchbar_media, prop, val)
        elif sec_type == "clock" and hasattr(self._touchbar_clock, prop):
            setattr(self._touchbar_clock, prop, val)
        elif sec_type == "telemetry" and hasattr(self._touchbar_telemetry, prop):
            setattr(self._touchbar_telemetry, prop, val)

    def _on_inspector_slot_cleared(self, slot_idx: int) -> None:
        """
        Обрабатывает удаление действия корзиной 🗑️:
        сбрасывает данные слота, очищает превью кнопки и снимает выделение.
        """
        logger.info("Inspector slot cleared: slot=%s", slot_idx)
        self._button_slots[slot_idx] = ButtonSlotDTO(
            slot_index=slot_idx,
            title="",
            icon="",
            category="",
            action_type="",
            hotkey="",
        )
        if isinstance(self.canvas_widget, DeckCanvasWidget):
            self.canvas_widget.clear_cell(slot_idx)
            self.canvas_widget.clear_selection()

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

    def _on_pagination_page_changed(self, page_index: int) -> None:
        logger.info("Pagination page changed: %s", page_index)
        self.active_page_id = page_index - 1
        if hasattr(self.canvas_widget, "set_page") and callable(self.canvas_widget.set_page):
            self.canvas_widget.set_page(page_index)

    def _on_pagination_add_page_requested(self) -> None:
        logger.info("Pagination add page requested")

    def set_page(self, page_id: str | int) -> None:
        """
        Переключает активную страницу редактора (холст и панель пагинации).
        Поддерживает форматы: int (1..8), str ('page_0', 'page_1', '1').
        """
        self.active_page_id = page_id
        page_idx = 1
        if isinstance(page_id, int):
            page_idx = max(1, min(8, page_id))
        elif isinstance(page_id, str):
            if page_id.startswith("page_"):
                try:
                    num = int(page_id.split("_")[1])
                    page_idx = max(1, min(8, num + 1))
                except (ValueError, IndexError):
                    page_idx = 1
            else:
                try:
                    num = int(page_id)
                    page_idx = max(1, min(8, num))
                except ValueError:
                    page_idx = 1

        if self.pagination_bar is not None and hasattr(self.pagination_bar, "set_current_page"):
            try:
                self.pagination_bar.set_current_page(page_idx)
            except Exception as exc:
                logger.warning("Error setting pagination page: %s", exc)

        if self.canvas_widget is not None and hasattr(self.canvas_widget, "set_page"):
            try:
                self.canvas_widget.set_page(page_idx)
            except Exception as exc:
                logger.warning("Error setting canvas page: %s", exc)

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
        Обрабатывает выбор действия в каталоге: если на холсте выделен слот кнопки,
        назначает выбранное действие на эту кнопку, обновляет инспектор и превью ячейки.
        """
        if not hasattr(item_dto, "id") or not hasattr(item_dto, "icon"):
            return

        selected_target = None
        if isinstance(self.canvas_widget, DeckCanvasWidget):
            selected_target = self.canvas_widget.get_selected_target()

        if selected_target is not None and selected_target[0] == "button":
            slot_idx = int(selected_target[1])
            dto = self._button_slots.setdefault(
                slot_idx, ButtonSlotDTO(slot_index=slot_idx)
            )

            title_text = item_dto.get_title() if hasattr(item_dto, "get_title") else ""
            category_key = getattr(item_dto, "category_key", "")
            cat_name = t(category_key) if category_key else ""
            category_text = f"{cat_name}: {title_text}" if cat_name else title_text

            dto.title = title_text
            dto.icon = getattr(item_dto, "icon", "🖲️")
            dto.category = category_text
            dto.action_type = getattr(item_dto, "id", "")

            logger.info(
                "Assigned action '%s' to slot %d: title='%s', icon='%s'",
                dto.action_type,
                slot_idx,
                dto.title,
                dto.icon,
            )

            # Обновление превью ячейки на холсте
            if isinstance(self.canvas_widget, DeckCanvasWidget):
                self.canvas_widget.update_cell_preview(slot_idx, "title", dto.title)
                self.canvas_widget.update_cell_preview(slot_idx, "icon", dto.icon)
                self.canvas_widget.update_cell_preview(slot_idx, "category", dto.category)

            # Обновление формы инспектора свойств
            if isinstance(self.inspector, KeyPropertyInspector):
                self.inspector.load_button_slot(slot_idx, dto)

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
        slots = DeckConfigAdapter.load_page_slots(root_config, self.active_page_id)
        self._button_slots = slots

        if isinstance(self.canvas_widget, DeckCanvasWidget):
            for idx, dto in slots.items():
                self.canvas_widget.update_cell_preview(idx, "title", dto.title)
                self.canvas_widget.update_cell_preview(idx, "icon", dto.icon)
                self.canvas_widget.update_cell_preview(idx, "category", dto.category)

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
