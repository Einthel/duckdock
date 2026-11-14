# Changelog: DuckDock / TouchWM

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.5] - 2026-11-14

### Added
- **Спринт 5: Аппаратный мониторинг датчиков Ring 0 (LibreHardwareMonitor) и NOC-дашборд 944×600**:
  - `core/telemetry_model.py`:
    - Строго типизированный датакласс `TelemetrySnapshot` для контракта аппаратной телеметрии:
      - CPU: температура (Ryzen Tctl/Tdie), нагрузка %, тактовая частота GHz, энергопотребление Package Power W.
      - GPU: температура dGPU (RTX 3080) и Hotspot, загрузка GPU %, заполнение VRAM (занято/всего ГБ), энергопотребление W, обороты вентиляторов Fan RPM.
      - RAM: занято/всего ГБ DDR5, процент нагрузки %.
      - Storage: NVMe/SSD температура, активность % чтения/записи.
      - Охлаждение: обороты помпы AIO Pump RPM, кулера CPU, корпусных вентиляторов Chassis Fans RPM, температура VRM материнской платы.
      - Network & Latency: скорость Download/Upload в КБ/с, сетевой пинг (мс) к DNS.
      - Системный статус: Uptime ОС, флаги `is_lhm_active` (Ring 0) и `is_admin` (UAC).
      - Вспомогательные методы `to_dict()`, `from_dict()`, расчет процента `vram_pct`.
  - `core/hardware_monitor.py`:
    - Модуль прямой интеграции с `LibreHardwareMonitorLib.dll` через `pythonnet` (CLR C#/.NET bridge).
    - Автоматический поиск и динамическая загрузка сборки DLL (`sys._MEIPASS`, `resources/bin/LibreHardwareMonitorLib.dll`, системный RTSS LHMDataProvider).
    - Реализация шаблона `UpdateVisitor` (`IVisitor`) для обхода и циклического опроса датчиков материнской платы, CPU, GPU, RAM, накопителей и сети.
    - Приоритезация дискретного GPU (dGPU) над интегрированным (iGPU).
    - Интеллектуальный парсинг сенсоров Ryzen (приоритет датчиков Tctl/Tdie) и Hotspot dGPU.
    - Надежный fallback-режим сбора базовых метрик через `psutil` при отсутствии сборки DLL, прав Администратора UAC или сбое CLR.
    - Проверка прав Windows UAC (`is_admin()`).
  - `core/telemetry_worker.py`:
    - Асинхронный рабочий поток сбора телеметрии `TelemetryWorker` в изолированном `QThread`.
    - Опрос датчиков `HardwareMonitor` и сетевого пинга с интервалом 1000 мс без блокировки GUI-потока (0% дропов FPS).
    - Замер сетевой задержки `measure_network_latency` через быстрый неблокирующий TCP-коннект к DNS (1.1.1.1, 8.8.8.8:53) без потребности в RAW Sockets.
    - Эмиссия сигнала `snapshot_ready(TelemetrySnapshot)` и публикация в шину `bus.sensors_updated(dict)`.
  - `core/telemetry_history.py`:
    - Кольцевой буфер `RingBuffer(maxlen=60)` с константной памятью $O(1)$ для скользящего окна метрик (60 секунд).
    - Фасад `TelemetryHistory` с раздельными буферами для ключевых метрик (CPU Temp/Load, GPU Temp/Load, RAM, Net RX/TX, Ping).
    - Автоматическая очистка и фильтрация невалидных данных (NaN/None/inf).
  - `ui/widgets/sparkline.py`:
    - Аппаратный Sparkline-виджет `SparklineWidget` на базе нативного `QPainter` и векторных кривых Безье (`QPainterPath`).
    - Полупрозрачная градиентная заливка площади под графиком (`QLinearGradient`).
    - Адаптивная цветовая палитра: <60°C Cyan (`#38bdf8`), 60–78°C Amber (`#f59e0b`), >=80°C Crimson (`#ef4444`).
    - Пульсирующий маяк (Beacon dot) на последней точке графика и пунктирная сетка уровней.
    - Полная изоляция отрисовки на iGPU (AMD Radeon Graphics), 0% нагрузки на dGPU.
    - Строгий инвариант `Qt.NoFocus`.
  - `ui/modules/sensors_view.py`:
    - Двухуровневый NOC-дашборд в рабочей области 944×600:
      - **Header Bar (36px):** Живой статус-индикатор драйвера (`● LibreHardwareMonitor Ring 0` / `● Fallback psutil`), UAC badge, системный Uptime в часах/минутах.
      - **Верхний ярус (Hero Cards 2× ~250px):**
        - *CPU Master Card:* крупная температура Tctl/Tdie (36px с цветовой индикацией), загрузка ядер %, частота GHz, Package Power W, обороты AIO Pump / CPU Fan RPM, 60s живой Sparkline.
        - *GPU Master Card:* крупная температура dGPU и Hotspot, загрузка %, VRAM Bar (занято/всего ГБ), энергопотребление W, кулеры Fan RPM, 60s живой Sparkline.
      - **Нижний ярус (NOC Grid 4× ~220px):**
        - *RAM DDR5 Card:* Занято / Всего ГБ, градиентный ProgressBar, мини-спарклайн динамики загрузки.
        - *Network & Ping Card:* Download / Upload MB/s, Ping (мс), мини-спарклайн сетевой активности.
        - *Storage NVMe Card:* Температура накопителя, % активности чтения/записи, бейдж накопителя.
        - *Chassis & Motherboard Card:* Обороты корпусных вентиляторов, температура VRM, статус системы.
    - Соблюдение инварианта `Stealth Focus` (`Qt.NoFocus` на всех элементах).
  - Комплексный набор модульных тестов: `tests/unit/test_hardware_monitor.py`, `test_telemetry_model.py`, `test_telemetry_worker.py`, `test_telemetry_history.py`, `test_sparkline.py`, `test_sensors_view.py` (общее покрытие тестами расширено с 42 до 79 тестов, 100% pass).

## [0.1.4] - 2026-11-14

### Added
- **Спринт 4: Полнофункциональный медиахаб YouTube на iGPU**:
  - `core/web_profile.py`:
    - Синглтон `WebProfileManager` постоянного изолированного профиля `DuckDock_WebProfile`.
    - Директории профиля в `%LOCALAPPDATA%/DuckDock/web_profile/storage` и `.../cache`.
    - Принудительная фиксация cookies авторизации Google (`ForcePersistentCookies`).
    - Ограничение дискового кэша до 256 МБ (`DiskHttpCache`).
    - Подмена User-Agent на актуальный Desktop Chrome (Windows x64) для исключения ошибки авторизации *"This browser or app may not be secure"*.
    - Автоматическая инжекция скриптов тач-темы и блокировщика рекламы через `QWebEngineScript` (`DocumentReady`, `MainWorld`).
  - `core/web_interceptor.py`:
    - Сетевой перехватчик `AdBlockInterceptor` (`QWebEngineUrlRequestInterceptor`).
    - Отсечение запросов к баннерным, рекламным и аналитическим доменам (`googlesyndication.com`, `doubleclick.net`, `googleadservices.com`, `google-analytics.com`, `adservice.google.com`, `/api/stats/ads`, `play.google.com/log`).
  - `resources/css/ytm_touch_theme.css`:
    - Скрытие верхней панели навигации `ytmusic-nav-bar` для оптимизации вертикального пространства 600px.
    - Увеличение нижней панели плеера до 84px с темным фоном `#0f1117`.
    - Крупные сенсорные кнопки (Play/Pause 64x64px, Prev/Next 48x48px).
    - Расширенная полоса прогресса (14px) с ползунком 24x24px.
    - Подавление диалогов неактивности (`ytmusic-you-there-renderer`) и промо-баннеров Premium.
  - `resources/js/ytm_touch_adblock.js`:
    - Авто-скип видеорекламы (`video.currentTime = video.duration`, `playbackRate = 16.0`, `muted = true`).
    - Автоклик по кнопкам пропуска `.ytp-ad-skip-button`.
    - Мост снятия названия трека/исполнителя `window.__duckdock_get_media_state()`.
    - Мост внешнего управления воспроизведением `window.__duckdock_media_action(action)`.
  - `ui/sidebar.py`:
    - Сквозной сенсорный `MiniMediaBar` (ширина 64px) в нижней части сайдбара.
    - Бегущая строка названия трека `MarqueeLabel` с кинетическим авто-скроллом.
    - Сенсорные кнопки управления ⏮ ⏯ ⏭ с инвариантом `Qt.NoFocus`.
    - Быстрый переход на вкладку плеера (вкладка 0) по тапу на мини-бар.
  - `ui/modules/youtube_view.py`:
    - Интеграция `WebProfileManager` и `QWebEnginePage`.
    - Кнопки быстрой навигации: YouTube Music, YouTube, Twitch и кнопка перезагрузки страницы (все `Qt.NoFocus`).
    - Таймер опроса JS-моста (1000 мс) и диспетчеризация сигналов `bus.media_state_changed` и `bus.media_action_requested`.
  - `core/event_bus.py`:
    - Сигналы `media_state_changed(dict)` и `media_action_requested(str)`.
  - Модульные тесты `tests/unit/test_web_profile.py` и `tests/unit/test_youtube_view.py` (все 42 теста успешно проходят).

## [0.1.3] - 2026-11-13

### Added
- **Спринт 3: Модуль сенсорного аудиомикшера (PyCaw Windows Core Audio Mixer)**:
  - `core/audio_manager.py`:
    - Потокобезопасный фасад Windows Core Audio API (`pycaw`, `comtypes`).
    - Модель данных сессии `AudioSessionInfo` (Pydantic v2).
    - Управление общей громкостью Master Volume (`get_master_volume`, `set_master_volume`, `toggle_master_mute`).
    - Сканирование, группировка сессий по PID, фильтрация завершенных (expired) сессий и поддержка системных звуков (PID 0).
    - Разрешение путей `.exe` процессов через кэш `psutil` для извлечения иконок приложений.
    - Управление индивидуальной громкостью и отключением звука (`set_session_volume`, `toggle_session_mute`).
  - `ui/modules/audio_view.py`:
    - Тач-слайдер `TouchSlider` (мгновенный прыжок значения по тачу в любую точку трека `QStyle.sliderValueFromPosition`, `Qt.NoFocus`).
    - Карточка общей громкости Master Volume с крупным сенсорным слайдером и кнопкой Mute (min 48×48px).
    - Интерактивный список активных аудиосессий с иконками приложений (`QFileIconProvider`), ползунками громкости и кнопками быстрого отключения звука.
    - Кинетическая прокрутка списка жестом пальца через `QScroller.grabGesture`.
    - Бесшовное обновление данных раз в 1.5 сек без перерисовки активных виджетов и с защитой от сброса при перетаскивании ползунка.
  - Интеграция в `ui/main_window.py` (вкладка 3 рабочего пространства) и шину событий `core/event_bus.py`.
  - Модульные и компонентные тесты `tests/unit/test_audio_manager.py` и `tests/unit/test_audio_view.py` (34 теста, 100% pass).

## [0.1.0] - 2026-11-13

### Added
- Первичная архитектурная инициализация проекта по стандарту `PROJECT_BOOTSTRAP.md` (Архетип `desktop_gui`).
- Конфигурации среды разработки VS Code (`settings.json`, `launch.json`, `extensions.json`).
- Архитектурные правила и законы кодовой базы в `GEMINI.md`.
- Пакетные файлы автоматизации Windows: `run.bat`, `dev.bat`, `build.bat`, `build_exe.py`.
- Фундаментальные модули ядра:
  - `core/dpi.py` — Per-Monitor DPI Awareness V2.
  - `core/config.py` — Типизированная конфигурация `config.json`.
  - `core/event_bus.py` — Централизованная шина событий и сигналов.
  - `core/window_manager.py` — WinAPI менеджер окон (поиск HWND, удаление заголовков/рамок, тайлинг в 720×600).
  - `core/focus_guardian.py` — Stealth-фокус, `WS_EX_NOACTIVATE`, хук событий переключения и возврат курсора мыши.
  - `core/mouse_barrier.py` — Ограничитель курсора мыши между мониторами.
  - `core/aida_reader.py` — Парсер Shared Memory AIDA64 через `mmap`.
- Графический интерфейс PySide6:
  - `ui/main_window.py` — Главный контейнер 800×600 (Frameless, `WS_EX_NOACTIVATE`).
  - `ui/sidebar.py` — Сайдбар 80×600 с крупными кнопками 64×64 под сенсорные касания.
  - `ui/dimmer_overlay.py` — Полноэкранный сквозной слой регулировки яркости.
  - `ui/showcase_view.py` — Диагностическая панель состояния подсистем.
  - `ui/modules/sensors_view.py` — Карточки аппаратных датчиков.
  - `ui/modules/youtube_view.py` — Тач-оптимизированный медиа-контейнер.
- Набор модульных тестов в `tests/` с покрытием конфигурации, DPI и менеджера окон.
