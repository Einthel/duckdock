# DuckDock / TouchWM: Архитектурная спецификация модулей

> **Статус:** v0.4.0 (Спринт 6: Модуляризация Feature-First и Deck Foundation)  
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
    end

    subgraph CoreFoundation ["Слой фундамента (core/ - Foundation Layer)"]
        Bus["core.event_bus.bus (Central EventBus)"]
        FG["core.focus_guardian.FocusGuardian"]
        WM["core.window_manager.WindowManager & ProcessWatcher"]
        MB["core.mouse_barrier.MouseBarrier"]
        TF["core.touch_filter.TouchCursorFilter (Swipe Engine)"]
        UIB["core.ui_base.TouchModuleView (Qt.NoFocus & cleanup)"]
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
            DeckGrid --> DeckSwipe
            DeckPanel --> DeckSwipe
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
    Bus -.->|playback_device_changed| AView
    Bus -.->|playback_device_changed| DeckView
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
4. **Stealth Focus Invariant (`TouchModuleView`):**  
   Все экраны модулей наследуются от `core.ui_base.TouchModuleView`, где принудительно задается `self.setFocusPolicy(Qt.NoFocus)` и метод `cleanup()`.
5. **Re-export Shims & Backward Compatibility:**  
   Для сохранения обратной совместимости файлов старых версий настроены легковесные фасады в `core/` и `ui/modules/` с алиасингом `sys.modules`.

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

### `modules.deck` — Сенсорная макро-панель DuckDeck v0.4.0

- `models.py`: Pydantic V2 модели конфигурации DuckDeck (`DeckRootConfig`, `DeckPageConfig`, `DeckButtonConfig`, `DeckActionConfig`, `SoundSettings`) и типизированные параметры действий.
- `action_dispatcher.DeckActionDispatcher`: Асинхронный диспетчер задач в пуле `QThreadPool` с антидребезгом (250 мс) и сторожевым таймером (5000 мс).
- `actions/`:
  - `hotkey_sender.py`: Аппаратные скан-коды `SendInput` (`KEYEVENTF_SCANCODE`) с восстановлением фокуса целевого окна.
  - `process_launcher.py`: Detached-запуск процессов и URL-схем (`CREATE_NO_WINDOW`, `DETACHED_PROCESS`).
  - `http_client.py`: Неблокирующие REST-запросы к локальным сервисам (Home Assistant, OpenRGB, OBS).
  - `screen_capture.py`: Захват экрана 1 (2560×1440) через `QScreen` / `BitBlt` в буфер обмена.
- `widgets/`:
  - `deck_button.py` (`DeckButtonWidget`): Сенсорный тайл 174×168 px с тактильной анимацией вдавливания (+2 px), защитой от дребезга, шейком ошибки, авто-сбросом при горизонтальном сдвиге $|dx| \ge 20$ px и подавлением ложных кликов.
  - `deck_grid.py` (`DeckGrid`): Сетка 944×372 px (2 строки × 5 колонок = 10 кнопок), плавная Fade-In анимация (160 мс) при смене страниц.
  - `interactive_panel.py` (`DeckInteractivePanel`): Нижняя панель 920×216 px из 3 секций:
    - Левая (280 px): медиа-пульт (обложка, `MarqueeLabel`, кнопки ⏮ ⏯ ⏭).
    - Центральная (360 px): часы HH:mm, дата, сенсорный трек свайпа и `DotPagingWidget` (● ○ ○) с кинетической анимацией активной точки (220 мс, OutCubic) и световой вспышкой шевронов.
    - Правая (280 px): мини-датчики CPU/GPU, бегущий `NotificationTicker` (3с затухание) и сенсорная кнопка настроек ⚙.
  - `swipe_detector.py` (`DeckSwipeDetector`): Кинематический сенсорный детектор 1-пальцевого свайпа ($dt \le 600$ мс, $|dx| \ge 60$ px, $|dx| > 1.5 \cdot |dy|$) с изоляцией от глобального 2-пальцевого фильтра `TouchCursorFilter`.
- `view.DeckView(TouchModuleView)`: Сенсорный экран 944×600 px (формула: $12 + 168 + 12 + 168 + 12 + 216 + 12 = 600$ px), двусторонняя реактивность пагинации (`deck_page_changed`), перелистывание страниц свайпом и кликом по точкам.

### `modules.settings` — Управление конфигурацией приложения

- `config.py`: Валидация и загрузка настроек приложения (`load_config()`), модели `DisplayConfig`, `StealthConfig`, `AppConfig`.
- `view.SettingsView(TouchModuleView)`: Каркас экрана настроек разрешения экрана, диммера и горячих клавиш.

---

## 4. Слой фундамента ядра (`core/`)

- `dpi.py`: Инициализация Per-Monitor DPI Awareness V2 (`SetProcessDpiAwarenessContext(-4)`).
- `event_bus.py`: Централизованная шина сигналов Qt `bus` (навигация, громкость, телеметрия, медиа, DuckDeck: `deck_notification`, `deck_page_changed`).
- `focus_guardian.py`: Защита от перехвата фокуса и восстановление курсора мыши (`WS_EX_NOACTIVATE`, `SetWinEventHook`).
- `mouse_barrier.py`: Аппаратный барьер курсора мыши (`ClipCursor`) для предотвращения случайного вылета на второй экран.
- `touch_filter.py`: Перехват сенсорных касаний и движок двухпальцевого вертикального свайпа (Swipe Engine).
- `window_manager.py`: WinAPI фасад управления внешними окнами, удаление рамок и тайлинг на 944×600.
- `ui_base.py`: Базовый класс экранов `TouchModuleView(QWidget)`.

---

## 5. Общие сенсорные виджеты (`ui/widgets/`)

- `sparkline.py` (`SparklineWidget`): Отрисовка графиков телеметрии на `QPainter` с кривыми Безье и адаптивной палитрой (Cyan/Amber/Crimson).
- `touch_slider.py` (`TouchSlider`): Сенсорный слайдер громкости с `Qt.NoFocus` и мгновенным расчетом позиции касания `sliderValueFromPosition`.
- `marquee_label.py` (`MarqueeLabel`): Бегущая строка для длинных названий треков с плавной анимацией по таймеру.
