# DuckDock / TouchWM: Архитектурная спецификация модулей

> **Статус:** v0.6.0 (Редизайн инспектора `ButtonPropertyForm` с 8 ортогональными подформами, `CustomLibraryStorage`, пользовательские вкладки и сохранение кнопок `⭐`, Dark Obsidian v2, 552 теста 100% PASS)  
> **Целевая среда:** Windows 10/11 x64, 27" Primary (dGPU) + 7" 1024×600 JRP7813S Touchscreen (iGPU AMD Radeon Graphics).

---

## 1. Схема взаимодействия подсистем

```mermaid
flowchart TD
    subgraph Bootstrap ["Точка входа & Платформа"]
        Main["main.py"] -->|1. Init DPI V2| DPI["core.dpi.init_dpi_awareness()"]
        Main -->|2. iGPU Chromium Flags| Env["os.environ (QTWEBENGINE_CHROMIUM_FLAGS)"]
        Main -->|3. Load Config| Cfg["modules.settings.config.load_config()"]
        Main -->|4. Launch Qt| App["QApplication"]
        App --> Win["ui.main_window.MainWindow (1024x600)"]
        Main -->|CLI: --editor / --deck-editor| EditorWin["modules.deck.editor.DeckEditorWindow"]
    end

    subgraph CoreFoundation ["Слой фундамента (core/ - Foundation Layer)"]
        Bus["core.event_bus.bus (Central EventBus)"]
        I18N["core.i18n.I18nManager (t, tp, plural)"]
        FG["core.focus_guardian.FocusGuardian"]
        WM["core.window_manager.WindowManager & ProcessWatcher"]
        MB["core.mouse_barrier.MouseBarrier"]
        TF["core.touch_filter.TouchCursorFilter (Swipe Engine)"]
        UIB["core.ui_base.TouchModuleView (Qt.NoFocus & cleanup)"]
        Bus -.->|Signal: language_changed| UIB
    end

    subgraph FeatureModules ["Слой функциональных модулей (modules/ - Feature Layer)"]
        subgraph ModAudio ["modules.audio"]
            AM["service.AudioManager"]
            ASwitch["platform.device_switcher (COM IPolicyConfig)"]
            AModels["models.AudioDeviceInfo & AudioSessionInfo"]
            AView["view.AudioMixerView (TouchModuleView)"]
            AM --> ASwitch
            AM --> AModels
        end

        subgraph ModTelemetry ["modules.telemetry"]
            HM["hardware_monitor.HardwareMonitor (Ring 0 / psutil)"]
            AIDA["aida_reader.AidaReader"]
            TW["worker.TelemetryWorker (QThread 1000ms)"]
            TH["history.TelemetryHistory & RingBuffer"]
            TM["models.TelemetrySnapshot"]
            TView["view.SensorsView (TouchModuleView)"]
            TW --> HM
            TW -.-> TM
            TView -.-> TH
        end

        subgraph ModMedia ["modules.media"]
            WP["web_profile.WebProfileManager"]
            ABI["interceptor.AdBlockInterceptor"]
            MBar["widgets.mini_media_bar.MiniMediaBar"]
            MView["view.YouTubeView (TouchModuleView)"]
            WP --> ABI
        end

        subgraph ModDeck ["modules.deck"]
            DeckDisp["action_dispatcher.DeckActionDispatcher"]
            DeckSound["sound_engine.DeckSoundEngine (QSoundEffect)"]
            DeckActs["actions.* (Hotkey / Process / HTTP / Screen)"]
            DeckModels["models.DeckRootConfig, SoundSettings & ActionParams"]
            DeckView["view.DeckView (TouchModuleView, 944x600)"]
            DeckGrid["widgets.deck_grid.DeckGrid (944x372, 2x5)"]
            DeckPanel["widgets.interactive_panel.DeckInteractivePanel (920x216)"]
            DeckSwipe["widgets.swipe_detector.DeckSwipeDetector"]
            DeckDisp --> DeckActs
            DeckDisp -.-> DeckModels
            DeckView --> DeckGrid
            DeckView --> DeckPanel
            DeckView --> DeckSound
            DeckSound -.-> DeckModels
            DeckGrid --> DeckSwipe
            DeckPanel --> DeckSwipe
        end

        subgraph ModDeckEditor ["modules.deck.editor (WYSIWYG Configurator)"]
            EditorMgr["manager.DeckEditorManager (Singleton, 27'' Primary)"]
            EditorWin["DeckEditorWindow (QMainWindow, 1080x740)"]
            EditorAdapter["adapter.DeckConfigAdapter (Atomic I/O & Mapping)"]
            EditorHBar["widgets.header_bar.EditorHeaderBar (52px & Save Button)"]
            EditorCanvas["widgets.deck_canvas.DeckCanvasWidget (2x5 Grid + 3-Section Touchbar)"]
            EditorPaging["widgets.pagination_bar.PageNavigationBar (36px)"]
            EditorInsp["widgets.property_inspector.KeyPropertyInspector (Stacked 0..4)"]
            EditorDrawer["widgets.action_drawer.ActionLibraryDrawer (Search + Accordion)"]
            EditorCatalog["icon_catalog.IconCatalog & IconCache (Bilingual Search)"]
            EditorIconDlg["widgets.icon_library_dialog.IconLibraryDialog (580x640)"]
            EditorCommands["commands.* (QUndoStack & QUndoCommand)"]
            EditorDTO["dto.* (ButtonSlotDTO, Touchbar*DTO, ActionItemDTO)"]
            EditorDemo["demo_data & demo_launcher"]
            EditorMgr --> EditorWin
            EditorWin --> EditorHBar
            EditorWin --> EditorCanvas
            EditorWin --> EditorPaging
            EditorWin --> EditorInsp
            EditorWin --> EditorDrawer
            EditorWin --> EditorCommands
            EditorInsp --> EditorIconDlg
            EditorIconDlg --> EditorCatalog
            EditorWin -.-> EditorAdapter
            EditorWin -.-> EditorDTO
            EditorDemo -.-> EditorWin
        end

        subgraph ModSettings ["modules.settings"]
            SConfig["config.AppConfig & load_config"]
            SView["view.SettingsView (TouchModuleView)"]
        end
    end

    subgraph PresentationShell ["Слой шелла (ui/ - Presentation Shell)"]
        Win --> SB["ui.sidebar.SidebarDock (80x600)"]
        SB --> MBar
        Win --> Stack["QStackedWidget (944x600)"]
        Win --> Dimmer["ui.dimmer_overlay.DimmerOverlay"]
        Win --> Show["ui.showcase_view.ShowcaseView"]

        Stack --> MView
        Stack --> TView
        Stack --> DeckView
        Stack --> AView
        Stack --> Show

        TView --> SPK["ui.widgets.sparkline.SparklineWidget"]
        AView --> TSL["ui.widgets.touch_slider.TouchSlider"]
        MBar --> ML["ui.widgets.marquee_label.MarqueeLabel"]
    end

    %% Межмодульные связи через EventBus и интерфейсы
    Win -.->|WS_EX_NOACTIVATE / Focus Hook| FG
    Win -.->|Tile / Strip / Hide / Show| WM
    Win -.->|ClipCursor / Screen Boundary| MB
    Win -.->|Touch Message Filter| TF
    TF -.->|Signal: tab_changed (2-finger swipe)| Bus
    SB -.->|Signals: tab_changed, lock| Bus
    TW -.->|Signal: sensors_updated| Bus
    TW -.->|Signal: snapshot_ready| TView
    DeckDisp -.->|Request device toggle| Bus
    DeckPanel -.->|Click ⚙ -> open_editor| EditorMgr
    EditorWin -.->|Save / Ctrl+S: emit deck_config_updated| Bus
    Bus -.->|Signal: deck_config_updated (Hot Reload)| DeckView
    Bus -.->|playback_device_changed| AView
    Bus -.->|playback_device_changed| DeckView
    Bus -.->|Signal: language_changed| EditorWin
    MBar -.->|Signal: media_action_requested| Bus
    MView -.->|Signal: media_state_changed| Bus
    Bus -.->|Dispatch| Win
```

---

## 2. Архитектурные законы модульности (Modularity Laws)

1. **The Dependency Rule (Иерархия зависимостей):**  
   Зависимости строго направлены: `ui (Shell) -> modules (Features) -> core (Foundation)`.  
   - Слой `core/` изолирован и **НИКОГДА** не импортирует модули из `modules/` или компоненты шелла из `ui/`.
   - Модули в `modules/` не зависят от компонентов шелла из `ui/`.
2. **Sibling Modules Isolation (Изоляция соседних модулей):**  
   Прямой импорт между соседними функциональными модулями запрещен. Связь реализуется исключительно через события шины `core.event_bus.bus` и DTO.
3. **Audio Platform Decoupling (Разрыв циклической связи Audio <-> Deck):**  
   - Драйвер переключения Windows Core Audio вынесен в `modules/audio/platform/device_switcher.py`.
   - Модель `AudioDeviceInfo` размещена в `modules/audio/models.py`.
   - Диспетчер DuckDeck вызывает переключение через шину событий или внедренный экземпляр (DI).
4. **Stealth Focus & Reactive i18n Invariant (`TouchModuleView`):**  
   Все экраны модулей наследуются от `core.ui_base.TouchModuleView`, где принудительно задается `self.setFocusPolicy(Qt.NoFocus)`, автоматическая подписка на `bus.language_changed`, реализация `retranslate_ui()` и метод `cleanup()`.
5. **Re-export Shims & Backward Compatibility:**  
   Для сохранения обратной совместимости файлов старых версий настроены легковесные фасады в `core/` и `ui/modules/` с алиасингом `sys.modules`.
6. **Bilingual & Localization-First (i18n Law):**  
   Любые новые окна, панели, карточки, виджеты и кнопки обязаны с самого начала создаваться на двух языках (RU/EN) с выносом строк в `locales/*.json` (100% паритет ключей) и запретом хардкода строк в UI коде.

---

## 3. Спецификация модулей (Feature Modules)

### `modules.audio` — Сенсорный аудиомикшер и управление устройствами

- `service.AudioManager`: Потокобезопасный синглтон-фасад к Windows Core Audio API (WASAPI) через `pycaw`.
  - `get_master_volume() -> float` & `set_master_volume(level: float)`: Общая громкость.
  - `is_master_muted() -> bool` & `set_master_mute(muted: bool)`: Состояние мастер-Mute.
  - `get_sessions() -> List[AudioSessionInfo]`: Перечисление сессий приложений со сбором иконок.
  - `set_session_volume(pid, level)` & `set_session_mute(pid, muted)`: Управление звуком процесса.
  - `get_playback_devices() -> List[AudioDeviceInfo]`: Активные устройства вывода (`eRender`).
  - `set_default_playback_device(device_id)`: Переключение дефолтного устройства вывода.
  - `toggle_playback_device(targets)`: Циклическое сенсорное переключение (Наушники 🎧 <-> Колонки 🔊).
  - `is_mic_muted()`, `set_mic_mute()`, `toggle_mic_mute()`: Управление микрофоном (`eCapture`).
- `platform.device_switcher`: Прямой COM-клиент `IPolicyConfigClient` для ролей `eConsole`, `eMultimedia`, `eCommunications`.
- `models.py`: Pydantic V2 модели `AudioSessionInfo` и `AudioDeviceInfo`.
- `view.py`: `AudioMixerView(TouchModuleView)` с кнопкой быстрого переключения эндпоинта `btn_switch_device`, карточкой мастера и динамическими сессиями с `TouchSlider`.

### `modules.telemetry` — Аппаратный мониторинг и NOC-дашборд

- `hardware_monitor.HardwareMonitor`: Ring 0 опрос через `LibreHardwareMonitorLib.dll` (pythonnet) с fallback на `psutil`. Поддержка AMD Ryzen (`Tctl/Tdie`), Hotspot dGPU, NVMe.
- `aida_reader.AidaReader`: Синхронизация с памятью AIDA64 mmap (XML).
- `worker.TelemetryWorker`: Фоновый поток `QThread` (интервал 1000 мс) с неблокирующим TCP-пингом `measure_network_latency()`.
- `history.TelemetryHistory` & `history.RingBuffer`: Кольцевой буфер 60 точек метрик без утечек памяти.
- `models.TelemetrySnapshot`: Типизированная схема метрик CPU, GPU, RAM, Storage, Fan, Net, Ping.
- `view.SensorsView(TouchModuleView)`: Полноэкранный NOC-дашборд 944×600 (Hero-карточки CPU/GPU, NOC-сетка RAM/Net/SSD/Chassis, графики Sparkline).

### `modules.media` — Сенсорный медиаплеер YouTube и браузерный профиль

- `web_profile.WebProfileManager`: Изолированный постоянный профиль Chromium `%LOCALAPPDATA%/DuckDock/web_profile` с инжекцией скриптов блокировки рекламы и стилей.
- `interceptor.AdBlockInterceptor`: Сетевой фильтр (`QWebEngineUrlRequestInterceptor`), блокирующий трекеры и рекламу.
- `widgets.mini_media_bar.MiniMediaBar`: Сенсорный виджет управления медиа в сайдбаре (64×54px) с бегущей строкой `MarqueeLabel` и кнопками ⏮ ⏯ ⏭.
- `view.YouTubeView(TouchModuleView)`: Полноэкранный плеер с двунаправленной синхронизацией состояния через `EventBus`.

### `modules.deck` — Сенсорная макро-панель DuckDeck v0.6.4

- `models.py`: Pydantic V2 модели конфигурации DuckDeck (`DeckRootConfig`, `DeckPageConfig`, `DeckButtonConfig`, `DeckActionConfig`, `SoundSettings`, `AudioActionParams`, `LaunchActionParams`, `SystemActionParams`, `HotkeyActionParams`). Пространство действий сведено к 8 ортогональным примитивам (`hotkey`, `launch`, `audio`, `media`, `text`, `system`, `deck_nav`, `macro`). Прозрачный нормализатор `DeckActionNormalizer` автоматически мигрирует 18+ устаревших типов конфигураций при загрузке. Чистый первый запуск (Factory Default): ровно 1 пустая страница без демо-данных.
- `presets.py`: Реестр эталонных пресетов `ActionPresetsRegistry` (Единый источник правды — SSOT): 7 системных категорий таксономии (саундборд удалён, `macro_sequence` сохранён с `is_wip=True`) с типизированными `base_action`, сериализацией `params` с `exclude_none=True`, цветами акцента и `status_source`. Устаревший `actions_registry.py` переведен на фасад над `ActionPresetsRegistry.get_categories_dto()`.
- `custom_library.py` (`CustomLibraryStorage`): Хранилище пользовательской библиотеки (`CustomTabConfig`, `CustomButtonPreset`, `CustomLibraryData`) с атомарным чтением/записью (`.tmp` + `os.replace`) в `config/deck_custom_library.json` изолированно от системных пресетов.
- `action_dispatcher.DeckActionDispatcher`: Асинхронный диспетчер задач в пуле `QThreadPool` на базе чистого `match-case` по 8 базовым примитивам с антидребезгом (250 мс), сторожевым таймером (5000 мс), режимом заглушек `simulation_mode` и изоляцией COM-аудио. Маршрутизация навигации `next_page` / `prev_page` / `folder_back` через `DeckNavExecutor` с безопасным фолбэком.
- `sound_engine.DeckSoundEngine`: Звуковой движок интерфейса (Zero-Latency Audio) на базе `PySide6.QtMultimedia.QSoundEffect` с предзагрузкой семплов в RAM (tap, page_switch, offline/error, online/success), регулировкой громкости, поддержкой индивидуального `sound_override` и предпрослушкой `preview_sound`.
- `actions/`:
  - `hotkey_sender.py`: Аппаратные скан-коды `SendInput` (`KEYEVENTF_SCANCODE`) с восстановлением фокуса целевого окна.
  - `process_launcher.py`: Detached-запуск процессов и URL-схем (`CREATE_NO_WINDOW`, `DETACHED_PROCESS`).
  - `http_client.py`: Неблокирующие REST-запросы к локальным сервисам (Home Assistant, OpenRGB, OBS).
  - `screen_capture.py`: Захват экрана 1 (2560×1440) через `QScreen` / `BitBlt` в буфер обмена.
- `widgets/`:
  - `deck_button.py` (`DeckButtonWidget`): Сенсорный тайл 174×168 px с полиморфным рендерингом `_render_icon()` (`QPixmap` для кастомных PNG/SVG иконок и фолбэк на Unicode/эмодзи), тактильной анимацией вдавливания (+2 px), защитой от дребезга, шейком ошибки, авто-сбросом при горизонтальном сдвиге $|dx| \ge 20$ px и подавлением ложных кликов.
  - `deck_grid.py` (`DeckGrid`): Сетка 944×372 px (2 строки × 5 колонок = 10 кнопок), плавная Fade-In анимация (160 мс) при смене страниц.
  - `interactive_panel.py` (`DeckInteractivePanel`): Нижняя панель 920×216 px из 3 секций:
    - Левая (280 px): медиа-пульт (обложка, `MarqueeLabel`, кнопки ⏮ ⏯ ⏭).
    - Центральная (360 px): часы HH:mm, дата, сенсорный трек свайпа и `DotPagingWidget` (● ○ ○) с кинетической анимацией активной точки (220 мс, OutCubic) и световой вспышкой шевронов.
    - Правая (280 px): мини-датчики CPU/GPU, бегущий `NotificationTicker` (3с затухание) и сенсорная кнопка настроек ⚙.
  - `swipe_detector.py` (`DeckSwipeDetector`): Кинематический сенсорный детектор 1-пальцевого свайпа ($dt \le 600$ мс, $|dx| \ge 60$ px, $|dx| > 1.5 \cdot |dy|$) с изоляцией от глобального 2-пальцевого фильтра `TouchCursorFilter`.
- `view.DeckView(TouchModuleView)`: Сенсорный экран 944×600 px (формула: $12 + 168 + 12 + 168 + 12 + 216 + 12 = 600$ px), двусторонняя реактивность пагинации (`deck_page_changed`), перелистывание страниц свайпом, кликом по точкам и через действия `deck_nav`.

### `modules.deck.editor` — Визуальный конфигуратор DuckDeck (WYSIWYG Configurator)

- `manager.py` (`DeckEditorManager`):
  - Потокобезопасный синглтон-менеджер жизненного цикла окна конфигуратора (`open_editor()`, `get_instance()`, `close_editor()`).
  - Центрирование окна (1080×740) в доступной рабочей области `primaryScreen` (27" dGPU).
  - Сохранение архитектурного инварианта Stealth Focus: `parent=None`, независимое top-level окно ОС, не передающее фокус тачскрину.
- `adapter.py` (`DeckConfigAdapter`):
  - Двусторонний адаптер трансляции моделей Pydantic v2 (`DeckRootConfig`, `DeckButtonConfig`) и презентационных `ButtonSlotDTO` со 100% сохранением расширенных полей (`status_source`, `color_accent`, `sound_override`, `toggle_action`) и поддержкой 8 базовых примитивов.
  - Методы `load_page_slots()` и `apply_slots_to_page()` с полной изоляцией многостраничной структуры (Pages 1..N).
  - Атомарное сохранение `save_deck_config_atomic()`: безопасная запись в `.tmp` со сбросом системных буферов (`os.fsync`), создание `.bak` и атомарная замена через `os.replace()`.
- `window.py` (`DeckEditorWindow(QMainWindow)`):
  - Главное окно конфигуратора (1080×740, min 960×640), центрирование на основном 27" экране.
  - Двухпанельная компоновка на базе `QSplitter(Qt.Horizontal)` с пропорцией 70/30 (рабочая область 756 px / каталог действий 324 px, `childrenCollapsible=False`).
  - Реактивный протокол Localization-First: метод `retranslate_ui()`, каскадный перевод дочерних компонентов и подписка на `bus.language_changed`.
  - Публичный API слотов-плейсхолдеров: `set_header_bar()`, `set_canvas_widget()`, `set_pagination_bar()`, `set_inspector_widget()`, `set_action_drawer()`.
  - Поддержка истории отмены `QUndoStack` (Undo/Redo), индикация несохраненных изменений `_is_dirty` и безопасный `closeEvent`.
- `styles.py`:
  - Дизайн-система Dark Obsidian: палитра (`#0f0f11`, `#18181b`, `#222227`, `#27272a`, `#3f3f46`, `#71717a`, `#9ca3af`, `#f4f4f5`, акценты `#0078d4`, `#38bdf8`, семантические `#10b981`, `#ef4444`).
  - Полная таблица стилей `EDITOR_MAIN_QSS` (окно, сплиттер 2px, выпадающие списки `QComboBox`, всплывающие меню, карточки, инпуты, тултипы, скроллбары 6px).
  - Безопасная функция Win32 DWM `apply_immersive_dark_titlebar(window)` с защитой от `OSError`.
  - Фасад применения темы `apply_editor_theme(window)`.
- `dto.py`:
  - Презентационные DTO структуры: `ButtonSlotDTO`, `TouchbarMediaDTO`, `TouchbarClockDTO`, `TouchbarTelemetryDTO`, `ActionItemDTO`, `ActionCategoryDTO`.
  - Метод `ActionItemDTO.get_title()` с поддержкой локализации через `t(self.title_key)`.
  - Двуязычные списки `keywords` (RU/EN) для моментальной фильтрации действий.
- `presets/`:
  - Реестр `ActionPresetsRegistry` с генерацией категорий пресетов для `ActionLibraryDrawer` и быстрого выпадающего меню «⚡ Шаблоны...».
- `widgets/`:
  - `header_bar.py` (`EditorHeaderBar`): Верхняя панель 52 px с селекторами устройств (`DeviceComboBox`) и профилей (`ProfileComboBox`), сохранением `userData` и каскадным `retranslate_ui()` без сброса `currentIndex`.
  - `deck_canvas.py` (`DeckCanvasWidget`): Холст макро-панели (сетка 2×5 из 10 ячеек `EditorGridCell` 80×80 px и полоса тачбара из 3 секций `TouchbarSectionWidget`). Поддержка Drag-and-Drop назначения пресетов и обмена слотов.
  - `grid_cell.py` (`EditorGridCell`): Интерактивная ячейка сетки с поддержкой состояний `empty` (`+`), иконки, заголовка, категории, цвета акцента и бейджа статуса.
  - `touchbar_section.py` (`TouchbarSectionWidget`): Интерактивный блок тачбара (Media, Clock, Telemetry).
  - `pagination_bar.py` (`PageNavigationBar`): Нижняя панель пагинации 36 px со стрелками и точечными индикаторами (`● ○ ○`).
  - `property_inspector.py` (`KeyPropertyInspector`): Инспектор свойств на базе `QStackedWidget` в карточном стиле Dark Obsidian v2 (`border: 1px solid BORDER_SURFACE_1`, `border-radius: 10px`) с бюджетом высоты `INSPECTOR_HEIGHT = 260 px`.
  - `button_property_form.py`:
    - `ButtonPropertyForm`: Комбобокс выбора 8 чистых примитивов (`hotkey`, `launch`, `audio`, `media`, `text`, `system`, `deck_nav`, `macro`), кнопка сохранения в библиотеку `⭐` (`btnSaveToLibrary`, `Qt.NoFocus`), компактные подформы параметров высотой `INPUT_HEIGHT = 28 px` (`HotkeySubform`, `LaunchSubform`, `AudioSubform` с DI-списком аудиоустройств через `set_audio_devices()`, `MediaSubform`, `TextSubform`, `SystemSubform`, `DeckNavSubform`, `MacroSubform`, `UnconfiguredSubform`).
    - Прямая маршрутизация `stack_idx` строго по `action_type` (`0..7`) и `unconfigured` (`8`) без legacy-эвристик; `FORM_LABEL_WIDTH = 96` (отсутствие обрезки «Живой статус:» / «Параметры:»), симметричная строка 3 без layout-сдвигов, `formVerticalSeparator` и `feedbackSeparator`.
    - `ColorAccentPicker`: Компактный стрип свотчей шириной `82 px` (свотчи `14 px`, шаг `3 px`) под плитку превью `84 px`.
  - `action_drawer.py` (`ActionLibraryDrawer`) & `action_item.py` (`ActionItemWidget`): Панель каталога пресетов с кнопкой `+ Вкладка` (`btnAddTab`), строкой поиска `ActionSearchBar` и аккордеоном системных категорий (`ActionPresetsRegistry`) + пользовательских вкладок (`CustomLibraryStorage`). Поддержка контекстного меню переименования/удаления вкладок и карточек, WIP-маркировки (`macro_sequence`) и полного Drag-and-Drop пользовательских кнопок на холст.
  - `Pure DND Invariant`: Назначение пресетов на кнопки холста производится строго через Drag & Drop. Клик по карточке в шторке нейтрализован (No-Op), исключая случайную перезапись выделенного или свободного слота. При Drop карточки на ячейку холста выполняется автоматическое выделение слота в `KeyPropertyInspector`.
  - Дорожные карты и архивация: Исторические планы `edit_action.md` и `edit_deckv2.md` перемещены в архив `.md/.archive/deck/`. Актуальные дорожные карты разработки: `.md/deck/edit_atrib1.md` (стабилизация ядра и типов) и `.md/deck/edit_atrib2.md` (спецификация и редизайн инспектора).

### `modules.settings` — Управление конфигурацией приложения

- `config.py`: Валидация и загрузка настроек приложения (`load_config()`), модели `DisplayConfig`, `StealthConfig`, `AppConfig`, атомарное сохранение `save_config()`.
- `view.SettingsView(TouchModuleView)`: Каркас экрана настроек разрешения экрана, диммера, горячих клавиш и селектора языка.

### `ui.showcase_view` — Экран диагностики подсистем и быстрых настроек

- `showcase_view.py` (`ShowcaseView(TouchModuleView)`): Экран витрины диагностики подсистем и инвариантов DuckDock (DPI, Stealth Touch Guardian, Borderless Tiling, QoL Services, ночной режим/диммер) с интегрированной сенсорной карточкой выбора языка интерфейса (`btn_lang_ru` / `btn_lang_en`), визуальной подсветкой активного языка (`active="true"`), атомарным сохранением в `config.json` и мгновенной сменой локали всего приложения через `bus.language_changed`.

---

## 4. Слой фундамента ядра (`core/`)

- `dpi.py`: Инициализация Per-Monitor DPI Awareness V2 (`SetProcessDpiAwarenessContext(-4)`).
- `i18n/`: Полнофункциональный движок интернационализации и локализации (I18n):
  - `manager.py` (`I18nManager`): Потокобезопасный синглтон с предзагрузкой словарей `locales/*.json` в плоскую хэш-таблицу dot-notation ($O(1)$ поиск), симметричным fallback-каскадом (RU <-> EN -> raw_key) и защищенным форматтером `SafeFormatter`.
  - `plural.py`: Вычисление грамматических форм множественных чисел для RU (`one`, `few`, `many`) и EN (`one`, `other`).
  - Экспорт функций быстрого доступа `t(key, **kwargs)` и `tp(key, count, **kwargs)`.
- `event_bus.py`: Централизованная шина сигналов Qt `bus` (навигация, громкость, телеметрия, медиа, язык: `language_changed`, DuckDeck: `deck_notification`, `deck_page_changed`, `deck_config_updated`).
- `focus_guardian.py`: Защита от перехвата фокуса и восстановление курсора мыши (`WS_EX_NOACTIVATE`, `SetWinEventHook`).
- `mouse_barrier.py`: Аппаратный барьер курсора мыши (`ClipCursor`) для предотвращения случайного вылета на второй экран.
- `touch_filter.py`: Перехват сенсорных касаний и движок двухпальцевого вертикального свайпа (Swipe Engine).
- `window_manager.py`: WinAPI фасад управления внешними окнами, удаление рамок и тайлинг на 944×600.
- `ui_base.py`: Базовый класс экранов `TouchModuleView(QWidget)` с `Qt.NoFocus`, автоматической подпиской на `bus.language_changed`, виртуальным методом `retranslate_ui()` и гарантированной отпиской в `cleanup()`.

---

## 5. Общие сенсорные виджеты (`ui/widgets/`)

- `sparkline.py` (`SparklineWidget`): Отрисовка графиков телеметрии на `QPainter` с кривыми Безье и адаптивной палитрой (Cyan/Amber/Crimson).
- `touch_slider.py` (`TouchSlider`): Сенсорный слайдер громкости с `Qt.NoFocus` и мгновенным расчетом позиции касания `sliderValueFromPosition`.
- `marquee_label.py` (`MarqueeLabel`): Бегущая строка для длинных названий треков с плавной анимацией по таймеру.
