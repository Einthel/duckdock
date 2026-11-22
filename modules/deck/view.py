"""
Сенсорная макро-панель DuckDeck (Presentation Layer).
Оптимизирована под геометрию рабочего пространства 944x600 (7" Touchscreen).
Архитектурные инварианты:
  - Наследование от TouchModuleView (Qt.NoFocus для сохранения фокуса на основном мониторе).
  - Сетка быстрых действий 2x5: сенсорные тайлы 174x168 px, высота сетки 372 px.
  - Нижняя интерактивная панель DeckInteractivePanel: 920x216 px.
  - Формула строгой высоты: 12 + 168 + 12 + 168 + 12 + 216 + 12 = 600 px.
  - Отсутствие залипающего :hover на тач-экранах; управление через свойства [state="..."]:
    idle, pressed, executing, success, error.
  - Тактильный отклик: вдавливание на 2 px и шейк содержимого через _content_offset без поломки QGridLayout.
  - Централизованная реактивность Live Dynamic Tiles и безопасная отписка от EventBus без утечек.
  - Sibling Decoupling: AudioManager принимается опционально через DI.
"""
import logging
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from core.event_bus import bus
from core.i18n import t
from core.ui_base import TouchModuleView
from modules.deck.action_dispatcher import DeckActionDispatcher
from modules.deck.sound_engine import DeckSoundEngine
from modules.deck.models import (
    DeckButtonConfig,
    DeckConfigLoader,
    DeckPageConfig,
    DeckRootConfig,
    NavigationParams,
)
from modules.deck.widgets.deck_button import DeckButtonWidget
from modules.deck.widgets.deck_grid import DeckGrid
from modules.deck.widgets.header_bar import HeaderBar
from modules.deck.widgets.interactive_panel import DeckInteractivePanel

logger = logging.getLogger("duckdock.deck.ui")

DECK_QSS = """
/* Базовый контейнер DeckView */
QWidget#DeckView {
    background-color: #0b0f19;
}

/* Зарезервированная интерактивная панель DeckInteractivePanel */
QWidget#DeckInteractivePanel, QFrame#DeckInteractivePanel {
    background-color: #111622;
    border: 1px solid #1e2638;
    border-radius: 14px;
}

/* Разделители между секциями интерактивной панели */
QFrame#DeckCenterSection {
    background-color: transparent;
    border-top: none;
    border-bottom: none;
    border-left: 1px solid #1e2638;
    border-right: 1px solid #1e2638;
}

QFrame#DeckLeftSection, QFrame#DeckRightSection {
    background-color: transparent;
    border: none;
}

/* Сенсорный тайл DeckButtonWidget (состояния [state="..."]) */
QFrame.deck-button {
    background-color: #161b26;
    border: 1px solid #232b3e;
}

QFrame.deck-button[state="idle"] {
    background-color: #161b26;
    border: 1px solid #232b3e;
}

QFrame.deck-button[state="pressed"] {
    background-color: #10141d;
    border: 1px solid #334155;
}

QFrame.deck-button[state="executing"] {
    background-color: #161b26;
    border: 2px solid #38bdf8;
}

QFrame.deck-button[state="success"] {
    background-color: #12241e;
    border: 2px solid #10b981;
}

QFrame.deck-button[state="error"] {
    background-color: #271417;
    border: 2px solid #ef4444;
}

/* Текстовые метки тайла */
QLabel.deck-btn-title {
    color: #e2e8f0;
    font-weight: bold;
}

QLabel.deck-btn-status {
    color: #94a3b8;
}
"""


class DeckView(TouchModuleView):
    """
    Главный интерфейсный модуль сенсорной макро-панели DuckDeck v0.4.0.
    Габариты: 944x600 px (DeckGrid 944x372 px + DeckInteractivePanel 920x216 px + 12 px margin).
    Формула высоты:
      12 px (top) + 168 px (r1) + 12 px (gap) + 168 px (r2) + 12 px (gap)
      + 216 px (панель) + 12 px (bottom) = 600 px.
    Реализует:
      - Связку с DeckActionDispatcher (асинхронное исполнение с антидребезгом).
      - Централизованную реактивность Live Dynamic Tiles (EventBus).
      - Сетку быстрых действий 2x5 (10 кнопок 174x168 px).
      - Резерв нижней области 920x216 px под DeckInteractivePanel.
      - Гарантированную отписку от шины событий без утечек памяти.
    """

    def __init__(
        self,
        config_path: str = "config/deck_config.json",
        dispatcher: Optional[DeckActionDispatcher] = None,
        audio_manager: Optional[Any] = None,
        sound_engine: Optional[DeckSoundEngine] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.config_path = config_path
        self._audio_manager = audio_manager
        self._custom_dispatcher = (dispatcher is not None)
        self.dispatcher = dispatcher or DeckActionDispatcher(
            audio_manager=self._audio_manager,
            parent=self,
        )
        self._custom_sound_engine = (sound_engine is not None)
        self.sound_engine = sound_engine or DeckSoundEngine(parent=self)

        # Инварианты геометрии и фокуса
        self.setObjectName("DeckView")
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(944, 600)
        self.setStyleSheet(DECK_QSS)

        self.root_config: Optional[DeckRootConfig] = None
        self.active_page_id: str = "default"
        self._eventbus_connected: bool = False
        self._is_emitting_page_changed: bool = False
        self._status_message: str = ""

        self._setup_ui()
        self._connect_signals()
        self._subscribe_eventbus()
        self.load_config()

    @property
    def audio_manager(self) -> Any:
        """Ленивая инициализация или получение внедренного аудиоменеджера."""
        if self._audio_manager is None:
            try:
                from modules.audio.service import AudioManager
                self._audio_manager = AudioManager()
            except Exception as e:
                logger.debug(f"Не удалось инициализировать AudioManager: {e}")
        return self._audio_manager

    @audio_manager.setter
    def audio_manager(self, value: Any) -> None:
        self._audio_manager = value

    @property
    def status_message(self) -> str:
        """Текущее статусное сообщение."""
        return self._status_message

    def set_status(self, message: str) -> None:
        """Установка статуса (в v0.4.0 транслируется в тикер интерактивной панели)."""
        self._status_message = message
        logger.debug(f"Deck status: {message}")
        if hasattr(self, "interactive_panel") and hasattr(self.interactive_panel, "set_status"):
            try:
                self.interactive_panel.set_status(message)
            except Exception:
                pass

    def _setup_ui(self) -> None:
        """
        Построение вертикального макета DeckView.
        Геометрия строго 600 px:
          DeckGrid: 372 px (12 px top + 168 px + 12 px gap + 168 px + 12 px gap)
          DeckInteractivePanel: 216 px
          Bottom margin: 12 px
          Итого: 372 + 216 + 12 = 600 px.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(0)

        # 1. Сетка макро-кнопок 2x5 (габариты 944x372 px)
        self.grid = DeckGrid(self)
        layout.addWidget(self.grid)

        # 2. Интерактивная сенсорная панель DeckInteractivePanel (920x216 px)
        self.interactive_panel = DeckInteractivePanel(self)
        layout.addWidget(self.interactive_panel, 0, Qt.AlignHCenter)

    def _connect_signals(self) -> None:
        """Внутренние сигналы между компонентами UI и диспетчером действий."""
        self.grid.button_triggered.connect(self._on_button_triggered)
        self.dispatcher.action_started.connect(self._on_action_started)
        self.dispatcher.action_finished.connect(self._on_action_finished)

        # Связка свайпов сетки и интерактивной панели с пагинацией страниц
        self.grid.swipe_left.connect(self.next_page)
        self.grid.swipe_right.connect(self.prev_page)
        self.interactive_panel.swipe_left.connect(self.next_page)
        self.interactive_panel.swipe_right.connect(self.prev_page)

        # Связка прямого выбора точки в DotPagingWidget
        self.interactive_panel.center_section.dots.page_selected.connect(
            self._on_dot_page_selected
        )

    def _subscribe_eventbus(self) -> None:
        """Подписка на сигналы шины событий для живых тайлов и синхронизации страниц."""
        if not self._eventbus_connected:
            bus.playback_device_changed.connect(self._on_playback_device_changed)
            bus.mic_mute_changed.connect(self._on_mic_mute_changed)
            bus.dimmer_opacity_changed.connect(self._on_dimmer_opacity_changed)
            bus.sensors_updated.connect(self._on_sensors_updated)
            bus.deck_page_changed.connect(self._on_deck_page_changed)
            bus.deck_config_updated.connect(self._on_deck_config_updated)
            self._eventbus_connected = True

    def _unsubscribe_eventbus(self) -> None:
        """Безопасная отписка от шины событий без возникновения исключений."""
        if self._eventbus_connected:
            try:
                bus.playback_device_changed.disconnect(self._on_playback_device_changed)
            except Exception:
                pass
            try:
                bus.mic_mute_changed.disconnect(self._on_mic_mute_changed)
            except Exception:
                pass
            try:
                bus.dimmer_opacity_changed.disconnect(self._on_dimmer_opacity_changed)
            except Exception:
                pass
            try:
                bus.sensors_updated.disconnect(self._on_sensors_updated)
            except Exception:
                pass
            try:
                bus.deck_page_changed.disconnect(self._on_deck_page_changed)
            except Exception:
                pass
            try:
                bus.deck_config_updated.disconnect(self._on_deck_config_updated)
            except Exception:
                pass
            self._eventbus_connected = False

    def get_display_pages(self) -> list[DeckPageConfig]:
        """
        Возвращает только непустые страницы для отображения на сенсорной панели.
        Пустые страницы (без кнопок) не отображаются на панели и не попадают в счетчик страниц.
        Если все страницы пустые, возвращается первая страница для избежания нулевого счетчика.
        """
        if not self.root_config or not self.root_config.pages:
            return []
        non_empty = [p for p in self.root_config.pages if len(p.buttons) > 0]
        return non_empty if non_empty else [self.root_config.pages[0]]

    def load_config(self) -> None:
        """Загрузка конфигурации макро-панели с откатом на дефолт при ошибке."""
        self.root_config = DeckConfigLoader.load_from_file(self.config_path)
        if not self.root_config.pages:
            self.root_config = DeckConfigLoader.get_default_config()

        # Регистрация страниц в виджете пагинации (только непустые страницы панели)
        display_pages = self.get_display_pages()
        if hasattr(self, "interactive_panel"):
            page_ids = [p.id for p in display_pages]
            self.interactive_panel.set_page_ids(page_ids)

        self.active_page_id = self.root_config.active_profile or (display_pages[0].id if display_pages else "default")
        if display_pages and not any(p.id == self.active_page_id for p in display_pages):
            self.active_page_id = display_pages[0].id
        self.set_active_page(self.active_page_id, emit_signal=False, animated_dots=False)

        # Синхронизация simulation_mode из конфигурации, если диспетчер не переопределен вручную
        if hasattr(self, "dispatcher") and self.dispatcher is not None:
            if not getattr(self, "_custom_dispatcher", False):
                self.dispatcher.simulation_mode = getattr(self.root_config, "simulation_mode", False)

        # Синхронизация настроек звукового движка из конфигурации
        if hasattr(self, "sound_engine") and self.sound_engine is not None:
            if not getattr(self, "_custom_sound_engine", False) and hasattr(self.root_config, "sound_settings"):
                self.sound_engine.apply_settings(self.root_config.sound_settings)

    def reload_config(self) -> None:
        """Горячая перезагрузка конфигурации с обновлением статуса."""
        try:
            self.load_config()
            self.set_status("Конфигурация перезагружена")
        except Exception as e:
            logger.error(f"Ошибка перезагрузки конфигурации DuckDeck: {e}")
            self.set_status(f"Ошибка: {e}")

    def get_current_page_index(self) -> int:
        """Возвращает индекс активной страницы среди отображаемых на панели (0-based)."""
        display_pages = self.get_display_pages()
        for idx, p in enumerate(display_pages):
            if p.id == self.active_page_id:
                return idx
        return 0

    def next_page(self) -> None:
        """
        Переход на следующую страницу (жест свайпа влево: dx < -60 px).
        page_idx + 1 с синхронной анимацией точек DotPagingWidget и эмиссией bus.deck_page_changed.
        """
        display_pages = self.get_display_pages()
        if not display_pages:
            return
        curr_idx = self.get_current_page_index()
        if curr_idx < len(display_pages) - 1:
            next_page = display_pages[curr_idx + 1]
            logger.info("Свайп влево: переход на следующую страницу '%s'", next_page.id)
            if hasattr(self, "interactive_panel"):
                self.interactive_panel.trigger_swipe_feedback("left")
            self.set_active_page(next_page.id, emit_signal=True, animated_dots=True)

    def prev_page(self) -> None:
        """
        Переход на предыдущую страницу (жест свайпа вправо: dx > +60 px).
        page_idx - 1 с синхронной анимацией точек DotPagingWidget и эмиссией bus.deck_page_changed.
        """
        display_pages = self.get_display_pages()
        if not display_pages:
            return
        curr_idx = self.get_current_page_index()
        if curr_idx > 0:
            prev_page = display_pages[curr_idx - 1]
            logger.info("Свайп вправо: переход на предыдущую страницу '%s'", prev_page.id)
            if hasattr(self, "interactive_panel"):
                self.interactive_panel.trigger_swipe_feedback("right")
            self.set_active_page(prev_page.id, emit_signal=True, animated_dots=True)

    def set_active_page(
        self,
        page_id: str,
        emit_signal: bool = True,
        animated_dots: bool = True,
    ) -> None:
        """
        Переключение отображаемой страницы сетки.
        Синхронизирует активную точку DotPagingWidget и эмитирует bus.deck_page_changed.
        """
        if not self.root_config or not self.root_config.pages:
            return

        display_pages = self.get_display_pages()
        target_page = None
        target_index = -1
        for idx, p in enumerate(display_pages):
            if p.id == page_id:
                target_page = p
                target_index = idx
                break

        # Fallback на индекс, если передан формат 'page_X'
        if target_page is None and page_id.startswith("page_") and page_id[5:].isdigit():
            idx = int(page_id[5:])
            if 0 <= idx < len(display_pages):
                target_page = display_pages[idx]
                target_index = idx

        # Если не найдено среди display_pages, проверим среди всех страниц root_config
        if target_page is None:
            for idx, p in enumerate(self.root_config.pages):
                if p.id == page_id:
                    target_page = p
                    break

        if not target_page:
            logger.warning("Страница '%s' не найдена в конфигурации DuckDeck", page_id)
            return

        page_changed = (self.active_page_id != target_page.id)
        self.active_page_id = target_page.id
        self.grid.load_page(target_page)

        # Синхронизация точек пагинации
        if hasattr(self, "interactive_panel") and target_index >= 0:
            self.interactive_panel.set_current_page(target_index, animated=animated_dots)

        # Звуковой отклик смены страницы (при фактическом изменении)
        if page_changed and hasattr(self, "sound_engine") and self.sound_engine is not None:
            self.sound_engine.play_page_switch()

        # Начальная синхронизация Live Dynamic Tiles с реальным состоянием
        self._sync_live_tiles()

        # Эмиссия сигнала в шину событий при смене страницы
        if emit_signal and page_changed:
            self._is_emitting_page_changed = True
            try:
                bus.deck_page_changed.emit(target_page.id)
            finally:
                self._is_emitting_page_changed = False

    def _on_deck_page_changed(self, page_id: str) -> None:
        """Реакция на внешнюю смену страницы через шину событий EventBus."""
        if getattr(self, "_is_emitting_page_changed", False):
            return
        if page_id != self.active_page_id:
            self.set_active_page(page_id, emit_signal=False, animated_dots=True)

    def _on_deck_config_updated(self) -> None:
        """
        Реакция на сигнал bus.deck_config_updated (горячая перезагрузка конфигурации).
        In-place обновляет кнопки 2x5 текущей страницы без мерцания,
        синхронизирует живые тайлы и транслирует статус в тикер интерактивной панели.
        """
        logger.info("Received bus.deck_config_updated: reloading deck configuration in-place")
        try:
            self.root_config = DeckConfigLoader.load_from_file(self.config_path)
            if not self.root_config.pages:
                self.root_config = DeckConfigLoader.get_default_config()

            display_pages = self.get_display_pages()
            if hasattr(self, "interactive_panel"):
                page_ids = [p.id for p in display_pages]
                self.interactive_panel.set_page_ids(page_ids)

            target_page = None
            for p in display_pages:
                if p.id == self.active_page_id:
                    target_page = p
                    break
            if target_page is None and display_pages:
                target_page = display_pages[0]
                self.active_page_id = target_page.id

            if target_page:
                if hasattr(self.grid, "update_page"):
                    self.grid.update_page(target_page)
                else:
                    self.grid.load_page(target_page)

            self._sync_live_tiles()
            self.set_status(t("deck.interactive.config_reloaded"))
        except Exception as exc:
            logger.error("Error in _on_deck_config_updated: %s", exc)

    def _on_dot_page_selected(self, page_idx: int) -> None:
        """Обработка нажатия на точку в DotPagingWidget."""
        display_pages = self.get_display_pages()
        if 0 <= page_idx < len(display_pages):
            target_page = display_pages[page_idx]
            self.set_active_page(target_page.id, emit_signal=True, animated_dots=True)

    def _on_button_triggered(self, btn_config: DeckButtonConfig) -> None:
        """Обработка нажатия на кнопку тайла."""
        # Звуковой отклик клика кнопки (с поддержкой sound_override)
        if hasattr(self, "sound_engine") and self.sound_engine is not None:
            self.sound_engine.play_tap(sound_override=btn_config.sound_override)

        # Навигационные действия обрабатываются внутри UI без отправки в worker thread
        if btn_config.action.action_type == "navigation":
            typed = btn_config.action.get_typed_params()
            if isinstance(typed, NavigationParams):
                self.set_active_page(typed.target_page_id)
                self.set_status(f"Страница: {typed.target_page_id}")
                btn = self.grid.get_button(btn_config.id)
                if btn:
                    btn.set_state("success")
                return

        # Игнорирование ненастроенных кнопок-пустышек (тактильный щелчок без действия)
        if btn_config.id.startswith("btn_unconfigured_") or (
            not btn_config.title and not btn_config.icon and not btn_config.action.params
        ):
            btn = self.grid.get_button(btn_config.id)
            if btn:
                btn.set_state("idle")
            return

        # Отправка действия в ActionDispatcher
        try:
            accepted = self.dispatcher.dispatch(
                btn_config.id,
                btn_config.action,
                button_title=btn_config.title,
            )
        except TypeError:
            accepted = self.dispatcher.dispatch(btn_config.id, btn_config.action)
        if not accepted:
            # Сработал антидребезг (cooldown 250 мс)
            btn = self.grid.get_button(btn_config.id)
            if btn:
                btn.set_state("idle")

    def _on_action_started(self, button_id: str) -> None:
        """Индикация начала исполнения действия."""
        btn = self.grid.get_button(button_id)
        if btn:
            btn.set_state("executing")

    def _on_action_finished(self, button_id: str, success: bool, message: str) -> None:
        """Индикация завершения действия."""
        btn = self.grid.get_button(button_id)
        if btn:
            btn.set_state("success" if success else "error")

        # Звуковой отклик при ошибке выполнения действия
        if not success and hasattr(self, "sound_engine") and self.sound_engine is not None:
            self.sound_engine.play_error()

        if message:
            self.set_status(message)

    # ---------------------------------------------------------
    # Централизованная реактивность Live Dynamic Tiles
    # ---------------------------------------------------------
    def _sync_live_tiles(self) -> None:
        """Первичная синхронизация живых тайлов текущей страницы."""
        try:
            mgr = self.audio_manager
            if mgr is not None:
                # 1. Аудиовыход
                dev_name = mgr.get_master_device_name()
                dev_id = mgr.get_default_playback_device_id() or ""
                self._on_playback_device_changed(dev_name, dev_id)

                # 2. Микрофон
                is_mic_muted = mgr.is_mic_muted()
                self._on_mic_mute_changed(is_mic_muted)
        except Exception as e:
            logger.debug(f"Ошибка первичной синхронизации живых тайлов: {e}")

    def _on_playback_device_changed(self, device_name: str, device_id: str) -> None:
        """Обновление тайлов с источником статуса 'audio_device'."""
        is_headphones = any(k in device_name.lower() for k in ["наушники", "headphone", "headset"])
        icon = "🎧" if is_headphones else "🔊"

        for btn in self.grid.get_buttons().values():
            if btn.button_config.status_source == "audio_device":
                btn.update_status(status_text=device_name, icon=icon)

    def _on_mic_mute_changed(self, is_muted: bool) -> None:
        """Обновление тайлов с источником статуса 'mic_mute'."""
        icon = "🔇" if is_muted else "🎙"
        status_text = t("deck.status.mic_muted") if is_muted else t("deck.status.mic_unmuted")

        for btn in self.grid.get_buttons().values():
            if btn.button_config.status_source == "mic_mute":
                btn.update_status(status_text=status_text, icon=icon)

    def _on_dimmer_opacity_changed(self, opacity: float) -> None:
        """Обновление тайлов с источником статуса 'dimmer'."""
        status_text = f"{int(opacity * 100)}%" if opacity > 0.0 else t("common.state.off")
        for btn in self.grid.get_buttons().values():
            if btn.button_config.status_source == "dimmer":
                btn.update_status(status_text=status_text)

    def _on_sensors_updated(self, data: dict) -> None:
        """Обновление тайлов телеметрии с источниками 'cpu_temp' и 'gpu_temp'."""
        if not isinstance(data, dict):
            return

        cpu_temp = data.get("cpu_temp")
        gpu_temp = data.get("gpu_temp")

        for btn in self.grid.get_buttons().values():
            src = getattr(btn.button_config, "status_source", None)
            if src == "cpu_temp" and cpu_temp is not None:
                try:
                    val = float(cpu_temp)
                    if val < 60.0:
                        color = "#10b981"
                        prefix = ""
                    elif val < 75.0:
                        color = "#f59e0b"
                        prefix = ""
                    else:
                        color = "#ef4444"
                        prefix = "⚠️ "
                    btn.update_status(status_text=f"{prefix}CPU: {int(round(val))}°C", badge_color=color)
                except (ValueError, TypeError):
                    pass
            elif src == "gpu_temp" and gpu_temp is not None:
                try:
                    val = float(gpu_temp)
                    if val < 60.0:
                        color = "#10b981"
                        prefix = ""
                    elif val < 75.0:
                        color = "#f59e0b"
                        prefix = ""
                    else:
                        color = "#ef4444"
                        prefix = "⚠️ "
                    btn.update_status(status_text=f"{prefix}GPU: {int(round(val))}°C", badge_color=color)
                except (ValueError, TypeError):
                    pass

    def retranslate_ui(self) -> None:
        """Обновление локализованных надписей DeckView и дочерних панелей."""
        if hasattr(self, "interactive_panel"):
            self.interactive_panel.retranslate_ui()
        self._sync_live_tiles()

    # ---------------------------------------------------------
    # Жизненный цикл и гарантированное освобождение ресурсов
    # ---------------------------------------------------------
    def cleanup(self) -> None:
        """Гарантированное освобождение ресурсов при закрытии или смене вкладки."""
        self._unsubscribe_eventbus()
        if hasattr(self, "interactive_panel") and hasattr(self.interactive_panel, "cleanup"):
            self.interactive_panel.cleanup()
        if hasattr(self, "sound_engine") and hasattr(self.sound_engine, "cleanup"):
            self.sound_engine.cleanup()
        self.grid.cleanup()
        super().cleanup()

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)


__all__ = [
    "DECK_QSS",
    "DeckButtonWidget",
    "DeckGrid",
    "HeaderBar",
    "DeckView",
    "DeckSoundEngine",
]
