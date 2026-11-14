# DuckDock / TouchWM: Архитектурная спецификация модулей

> **Статус:** v0.1.5 (Актуальная спецификация)
> **Целевая среда:** Windows 10/11 x64, 27" Primary (dGPU) + 7" 1024×600 JRP7813S Touchscreen (iGPU AMD Radeon Graphics).

---

## 1. Схема взаимодействия подсистем

```mermaid
flowchart TD
    subgraph Bootstrap ["Точка входа & Платформа"]
        Main["main.py"] -->|1. Init DPI V2| DPI["core.dpi.init_dpi_awareness()"]
        Main -->|2. iGPU Chromium Flags| Env["os.environ (QTWEBENGINE_CHROMIUM_FLAGS)"]
        Main -->|3. Load Schema| Cfg["core.config.load_config()"]
        Main -->|4. Launch Qt| App["QApplication"]
        App --> Win["ui.main_window.MainWindow (1024x600)"]
    end

    subgraph CorePlat ["Слой ядра (Platform Layer)"]
        Bus["core.event_bus.EventBus (Qt Signals)"]
        FG["core.focus_guardian.FocusGuardian"]
        WM["core.window_manager.WindowManager"]
        MB["core.mouse_barrier.MouseBarrier"]
        TF["core.touch_filter.TouchFilter"]
        AIDA["core.aida_reader.AidaReader"]
        AM["core.audio_manager.AudioManager"]
        WP["core.web_profile.WebProfileManager"]
        ABI["core.web_interceptor.AdBlockInterceptor"]
        HM["core.hardware_monitor.HardwareMonitor (LHM Ring 0 / psutil)"]
        TW["core.telemetry_worker.TelemetryWorker (QThread 1000ms)"]
        TH["core.telemetry_history.TelemetryHistory & RingBuffer"]
        TM["core.telemetry_model.TelemetrySnapshot"]
        WP --> ABI
        TW -->|Poll 1000ms| HM
        TW -.->|Data Contract| TM
    end

    subgraph Presentation ["Графический интерфейс (UI Layer)"]
        Win --> SB["ui.sidebar.SidebarDock (80x600)"]
        SB --> MMB["ui.sidebar.MiniMediaBar (64x54)"]
        Win --> Stack["QStackedWidget (944x600)"]
        Win --> Dimmer["ui.dimmer_overlay.DimmerOverlay"]

        Stack --> Tab0["ui.modules.youtube_view.YouTubeView (Вкладка 0)"]
        Stack --> Tab1["ui.modules.sensors_view.SensorsView (Вкладка 1)"]
        Stack --> Tab2["Happ.exe Tiling View (Вкладка 2)"]
        Stack --> Tab3["ui.modules.audio_view.AudioMixerView (Вкладка 3)"]
        Stack --> Tab4["ui.showcase_view.ShowcaseView (Вкладка 4)"]

        Tab1 --> SPK["ui.widgets.sparkline.SparklineWidget (QPainter)"]
    end

    Win -.->|WS_EX_NOACTIVATE / WinEvent Hook| FG
    Win -.->|Tile / Strip / Hide / Show| WM
    Win -.->|ClipCursor / Screen Boundary| MB
    Win -.->|Touch Message Filter| TF
    Tab0 -.->|QWebEnginePage / Scripts| WP
    Tab3 -.->|Windows Core Audio API| AM
    Tab1 -.->|60s Metric Buffer| TH
    TW -.->|Signal: snapshot_ready| Tab1
    TW -.->|Signal: sensors_updated| Bus
    SB -.->|Signals: tab_changed, lock| Bus
    Tab4 -.->|Signal: dimmer_toggle_requested| Bus
    TF -.->|Signal: tab_changed (2-finger swipe)| Bus
    MMB -.->|Signals: media_action_requested| Bus
    Tab0 -.->|Signals: media_state_changed| Bus
    Bus -.->|Dispatch| Win
```

---

## 2. Контракты ядра (Core Contracts)

### `HardwareMonitor` (`core/hardware_monitor.py`)

Аппаратный мониторинг датчиков через динамическую загрузку `LibreHardwareMonitorLib.dll` (CLR / pythonnet) с бесшовным fallback на `psutil`:

- `open() -> bool`: Инициализация LHM `Computer`, активация датчиков CPU, GPU, RAM, Storage, Motherboard, Fan Controllers.
- `close() -> None`: Безопасное освобождение неуправляемых ресурсов Ring 0 драйвера.
- `get_telemetry() -> TelemetrySnapshot`: Комплексный опрос датчиков с нормализацией в строго типизированную модель `TelemetrySnapshot`.
- `is_admin() -> bool`: Проверка повышенных привилегий Windows UAC (`IsUserAnAdmin`).
- Приоритезация дискретного GPU (NVIDIA/AMD dGPU) над интегрированным iGPU.
- Точный парсинг термодатчиков AMD Ryzen (`Tctl/Tdie`, `Core Max`) и Hotspot dGPU.

### `TelemetryWorker` (`core/telemetry_worker.py`)

Асинхронный рабочий поток опроса датчиков в изолированном `QThread`:

- Интервал опроса по умолчанию 1000 мс (0% дропов кадров и микрофризов в интерфейсе).
- `snapshot_ready = Signal(object)`: Передача готового `TelemetrySnapshot` в UI.
- `measure_network_latency(hosts, timeout) -> float`: Неблокирующий замер сетевого пинга к DNS 1.1.1.1/8.8.8.8 через TCP:53 без привилегий RAW Sockets.
- Публикация данных в глобальную шину `bus.sensors_updated(snapshot.to_dict())`.
- Корректная остановка потока `stop()` с `wait()` при выходе из приложения.

### `TelemetrySnapshot` (`core/telemetry_model.py`)

Строго типизированная модель данных телеметрии (Dataclass / Pydantic):

- Метрики CPU: `cpu_name`, `cpu_temp`, `cpu_load`, `cpu_clock`, `cpu_power`.
- Метрики GPU: `gpu_name`, `gpu_temp`, `gpu_hotspot`, `gpu_load`, `gpu_vram_used`, `gpu_vram_total`, `gpu_power`, `gpu_fan_rpm`.
- Метрики RAM: `ram_used_gb`, `ram_total_gb`, `ram_load_pct`.
- Метрики Storage: `storage_name`, `storage_temp`, `storage_activity`.
- Охлаждение: `cpu_fan_rpm`, `pump_rpm`, `chassis_fans_rpm: List[int]`, `vrm_temp`.
- Сеть и статус: `net_rx_kbps`, `net_tx_kbps`, `ping_ms`, `uptime_seconds`, `is_lhm_active`, `is_admin`, `timestamp`.
- Вспомогательные методы: `to_dict()`, `from_dict()`, `vram_pct`.

### `TelemetryHistory` & `RingBuffer` (`core/telemetry_history.py`)

Буфер скользящего окна метрик для построения графиков:

- `RingBuffer(maxlen=60, default_value=None)`: Кольцевой буфер фиксированного объема на базе `collections.deque` ($O(1)$ вставка, без утечек памяти).
- `TelemetryHistory(maxlen=60)`: Фасад управления историей ключевых метрик (`cpu_temp`, `cpu_load`, `gpu_temp`, `gpu_load`, `ram_load`, `net_rx`, `net_tx`, `ping`).
- Методы `add_snapshot(snapshot: TelemetrySnapshot)` и получение списков для Sparkline `to_list()`.

### `WebProfileManager` (`core/web_profile.py`)

Синглтон управления изолированным постоянным профилем Chromium `QWebEngineProfile`:

- `get_instance(base_dir=None) -> WebProfileManager`: Получение синглтона с путями в `%LOCALAPPDATA%/DuckDock/web_profile`.
- `get_profile() -> Optional[QWebEngineProfile]`: Возвращает настроенный постоянный профиль (`ForcePersistentCookies`, кэш 256 МБ, User-Agent Chrome Desktop Windows x64).
- Автоматическая инжекция CSS-темы `resources/css/ytm_touch_theme.css` и JS-сторожа `resources/js/ytm_touch_adblock.js` через `QWebEngineScript` (`DocumentReady`, `MainWorld`).

### `AdBlockInterceptor` (`core/web_interceptor.py`)

Сетевой фильтр сетевых запросов (`QWebEngineUrlRequestInterceptor`):

- `interceptRequest(info: QWebEngineUrlRequestInfo) -> None`: Блокировка рекламных доменов и аналитических трекеров (`googlesyndication.com`, `doubleclick.net`, `googleadservices.com`, `google-analytics.com`, `adservice.google.com`, `/api/stats/ads`, `play.google.com/log`).
- `is_blocked_url(url: str) -> bool`: Проверка сигнатур блокировки для произвольного URL.
- `blocked_count: int`: Счетчик заблокированных сетевых вызовов.

### `AudioManager` (`core/audio_manager.py`)

Потокобезопасный синглтон-фасад к Windows Core Audio API через `pycaw` и `comtypes`.

- `get_master_volume() -> float`: Текущая общая громкость системы (0.0 — 1.0).
- `set_master_volume(volume: float) -> None`: Установка общего уровня громкости.
- `toggle_master_mute() -> bool`: Переключение общего Mute, возвращает актуальный статус.
- `get_audio_sessions() -> List[AudioSessionInfo]`: Сканирование процессов со звуковыми потоками (Pydantic v2 модель).
- `set_session_volume(pid: int, volume: float) -> None`: Индивидуальная громкость процесса.
- `toggle_session_mute(pid: int) -> bool`: Отключение/включение звука для конкретного PID.

### `FocusGuardian` (`core/focus_guardian.py`)

Обеспечивает режим Stealth Focus (`WS_EX_NOACTIVATE`) и защиту от потери фокуса приложениями основного экрана.

- `enable_stealth_mode(hwnd: int) -> None`: Наложение `WS_EX_NOACTIVATE` на окно.
- `start_hook() -> bool`: Запуск глобального хука `SetWinEventHook` (`EVENT_SYSTEM_FOREGROUND`).
- `stop_hook() -> None`: Деактивация хука событий.
- `on_touch_detected(primary_pos: Tuple[int, int]) -> None`: Реакция на сенсорное касание и возврат фокуса/курсора.

### `MouseBarrier` (`core/mouse_barrier.py`)

Изоляция мыши на основном экране с предотвращением случайного вылета на сенсорную панель.

- `clip_cursor_to_primary() -> bool`: Ограничение перемещения системного курсора границами dGPU монитора.
- `release_cursor() -> None`: Освобождение курсора (`ClipCursor(NULL)`).
- `save_cursor_pos() -> None`: Запоминание координат курсора перед тач-событием.
- `restore_cursor_pos() -> None`: Возврат курсора на запомненные координаты основного монитора.

### `TouchCursorFilter` & Swipe Engine (`core/touch_filter.py`)

Перехват тач-событий сенсорного экрана, защита от дрифта курсора (Anti-Cursor Warp) и распознавание кинетических жестов:

- Распознавание двухпальцевого вертикального свайпа (`len(points) == 2`, `|avg_dy| >= 70px`, `dt <= 500ms`, `dy0 * dy1 > 0`, `|avg_dy| > 1.3 * |avg_dx|`):
  - Свайп снизу вверх (`avg_dy <= -70px`): циклическое переключение на следующий экран (`+1`).
  - Свайп сверху вниз (`avg_dy >= +70px`): циклическое переключение на предыдущий экран (`-1`).
- Подавление паразитного клика мыши (`_suppress_mouse_release = True`) после успешного распознавания свайпа.
- Свободный пропуск одиночных тапов (включая сайдбар) элементам UI без задержек.
- Восстановление курсора на координаты основного 27" экрана через `FocusGuardian`.

### `DimmerOverlay` (`ui/dimmer_overlay.py`)

Сквозной слой аппаратного затемнения (Software Dimmer) экрана 1024×600:

- Плавная анимация изменения уровня яркости через `QVariantAnimation` (200 мс, `QEasingCurve.Type.OutCubic`).
- `toggle(target_level=0.50)`: бинарное переключение между 0.0 (день) и 0.50 (ночь).
- Плавный реверс анимации на лету при повторном клике без рывков и скачков значений.
- Сквозной клик: `Qt.WA_TransparentForMouseEvents`, `Qt.WA_NoSystemBackground`, `Qt.WA_ShowWithoutActivating` и `Qt.NoFocus`.
- Оптимизация `paintEvent`: возврат без отрисовки при `opacity <= 0.001` (0% нагрузки на GPU).

### `WindowManager` (`core/window_manager.py`)

Низкоуровневые манипуляции окнами сторонних процессов через WinAPI.

- `find_window_by_process(exe_name: str) -> Optional[int]`: Поиск корневого HWND процесса.
- `strip_window_decorations(hwnd: int) -> bool`: Удаление системного заголовка (`WS_CAPTION`) и толстых рамок (`WS_THICKFRAME`).
- `tile_window(hwnd: int, rect: Tuple[int, int, int, int]) -> bool`: Принудительное позиционирование в область 944×600.
- `set_window_visible(hwnd: int, visible: bool) -> None`: Скрытие/отображение встроенного окна при переключении вкладок.

### `AidaReader` (`core/aida_reader.py`)

- `read_sensors() -> Dict[str, Any]`: Парсинг XML-структуры из Shared Memory AIDA64 (`AIDA64_SensorValues`).
- `is_available() -> bool`: Проверка доступности shared memory региона.

---

## 3. Шина событий (`core/event_bus.py`)

Централизованный диспетчер сигналов Qt:

- `tab_changed = Signal(int)`: Переключение активной вкладки рабочего пространства (0–4).
- `dimmer_opacity_changed = Signal(float)`: Изменение прозрачности диммера (0.0 - 0.95).
- `dimmer_toggle_requested = Signal()`: Запрос включения/выключения затемнения.
- `input_lock_toggled = Signal(bool)`: Переключение режима ввода текста / Stealth Focus.
- `sensors_updated = Signal(dict)`: Оповещение об обновлении аппаратной телеметрии (CPU, GPU, RAM, Storage, Fan, Network, Ping).
- `external_window_tiled = Signal(str, int)`: Уведомление о тайлинге стороннего окна `(app_name, hwnd)`.
- `master_volume_changed = Signal(float, bool)`: Оповещение об изменении общего звука `(volume, is_muted)`.
- `session_volume_changed = Signal(int, float, bool)`: Изменение сессии процесса `(pid, volume, is_muted)`.
- `media_state_changed = Signal(dict)`: Обновление метаданных трека и воспроизведения YouTube `{"title": str, "artist": str, "is_playing": bool}`.
- `media_action_requested = Signal(str)`: Управление медиаплеером (`"toggle_play"`, `"next"`, `"prev"`).
- `touch_detected = Signal(int, int)`: Координаты касания на втором экране `(x, y)`.
- `primary_focus_lost = Signal(int)`: HWND окна основного экрана, потерявшего фокус.

---

## 4. Спецификация сенсорных компонентов UI (`ui/`)

- **Главное окно (`ui/main_window.py`)**: Размер 1024×600, `Qt.FramelessWindowHint`, `Qt.WA_ShowWithoutActivating`, горизонтальный `QHBoxLayout` (сайдбар 80px + стек 944px).
- **Сайдбар (`ui/sidebar.py`)**: Ширина 80px, сенсорные кнопки 64×60px с отступами, политика `Qt.NoFocus`.
- **Mini Media Bar (`ui/sidebar.py`)**: Сквозной компактный плеер (64×54px), бегущая строка `MarqueeLabel`, кнопки ⏮ ⏯ ⏭ (`Qt.NoFocus`), клик по бару открывает вкладку YouTube.
- **Сенсорный аудиомикшер (`ui/modules/audio_view.py`)**:
  - Сенсорный слайдер `TouchSlider` (`QSlider` с мгновенным расчетом позиции `QStyle.sliderValueFromPosition`, `Qt.NoFocus`).
  - Карточки аудиосессий с иконками `QFileIconProvider` и кнопками мгновенного Mute.
- **Аппаратный NOC-дашборд 944×600 (`ui/modules/sensors_view.py`)**:
  - Header Bar (36px): Статус `● LibreHardwareMonitor (Direct Ring0)` / `● Fallback psutil`, UAC бейдж, системный аптайм.
  - Верхний ярус (Hero Cards 2× ~250px): Карточки CPU Master и GPU Master с крупными термоиндикаторами (36px), загрузкой, тактовой частотой, энергопотреблением, оборотами кулеров/помпы и живыми графиками Sparkline.
  - Нижний ярус (NOC Grid 4× ~220px): Карточки RAM DDR5 (GB/ProgressBar/Sparkline), Network & Ping (MB/s / Ping ms / Sparkline), NVMe Storage (SSD Temp/Activity), Chassis & Motherboard (вентиляторы корпуса / VRM).
  - Инвариант `Stealth Focus`: `Qt.NoFocus` на всех виджетах дашборда.
- **Аппаратный Sparkline-виджет (`ui/widgets/sparkline.py`)**:
  - Высокопроизводительный рендеринг кривых Безье `QPainterPath` с полупрозрачным градиентом `QLinearGradient`.
  - Трехуровневая адаптивная цветовая шкала: Cyan (<60°C), Amber (60–78°C), Crimson (>=80°C).
  - Маяк последней точки (Beacon dot) и сетка уровней, полная изоляция отрисовки на iGPU.
- **Кинетическая прокрутка**: `QScroller.grabGesture(..., QScroller.LeftMouseButtonGesture)` во всех скролл-списках.
