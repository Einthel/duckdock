# DuckDock / TouchWM

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20Qt6-green.svg)](https://wiki.qt.io/Qt_for_Python)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-lightgrey.svg)](https://microsoft.com/windows)
[![Tests](https://img.shields.io/badge/tests-135%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Легковесный сенсорный оконный менеджер и панель управления (**Touch Dashboard & Macro Deck**) для вспомогательного 7-дюймового IPS-дисплея (1024×600 JRP7813S) под управлением Windows 10/11 x64.

Специально спроектирован для двухмониторных рабочих станций: **27" 2560×1440 Primary (dGPU)** + **7" 1024×600 Secondary Touchscreen (iGPU AMD Radeon Graphics, Ryzen 7 7700)**.

---

## 🎯 Ключевые возможности

### 1. 🛡 Stealth Touch & Anti-Cursor Warp (Win32 Foundation)
* **Stealth-фокус без перехвата**: Корневое окно использует стиль `WS_EX_NOACTIVATE` и `Qt.WA_ShowWithoutActivating`. Все виджеты имеют `Qt.NoFocus`. Касание второго экрана не сворачивает полноэкранные игры и не отбирает фокус у IDE на основном мониторе.
* **Anti-Cursor Warp**: Системный курсор мыши мгновенно возвращается на основной монитор после касания сенсорного экрана (`core.focus_guardian`).
* **Mouse Barrier**: Предотвращает случайный вылет физической мыши за границы основного 27" монитора (`core.mouse_barrier` ClipCursor).
* **Touch Gesture Engine**: Двухпальцевый вертикальный свайп для быстрого циклического переключения экранов (`core.touch_filter`).
* **Per-Monitor DPI Awareness V2**: Честная попиксельная координатная сетка 1024×600 без искажений масштабирования Windows.

### 2. 🎛 DuckDeck — Сенсорная макро-панель и системный контроллер
* **Сетка кнопок с профилями**: 3×5 (174×168 px) или 4×6 (145×124 px) с поддержкой страниц профилей (`Default`, `Dev / Tools`, `Gaming`).
* **Асинхронный диспетчер (`QThreadPool`)**: Защита от дребезга нажатий (cooldown 250 мс) и сторожевой таймер от зависания (Watchdog 5000 мс).
* **Аппаратные хоткеи (`hotkey_sender`)**: Отправка скан-кодов через `SendInput` (`KEYEVENTF_SCANCODE`) с автоматическим предварительным восстановлением фокуса целевого окна.
* **Переключение аудиовыхода (`audio_device_switcher`)**: Нативное переключение конечных точек Windows по умолчанию через COM `IPolicyConfigClient` (Console, Multimedia, Communications).
* **Скриншотер (`screen_capture`)**: Чистый захват основного экрана 2560×1440 через `BitBlt` / `QScreen` напрямую в буфер обмена.
* **Процессы и REST API**: Изолированный detached-запуск приложений (`process_launcher`) и фоновые HTTP-запросы к локальным сервисам (`http_client` — OpenRGB, Home Assistant, OBS).
* **Live Tiles**: Реактивное обновление иконок и статусов аудиовыхода (`🎧`/`🔊`) и микрофона (`🎙`/`🔇`) через шину `EventBus`.

### 3. 🔊 Touch Audio Mixer — Сенсорный аудиомикшер
* **Посессионное управление**: Полный контроль над громкостью и режимом Mute отдельных приложений Windows через Windows Core Audio (PyCaw / WASAPI).
* **Master Volume & Mute**: Крупный сенсорный ползунок Master с тактильной регулировкой.
* **Быстрое переключение вывода**: Кнопка в шапке микшера для циклического переключения между целевыми устройствами воспроизведения (например, наушники и колонки).
* **Сенсорные слайдеры**: `TouchSlider` с кинетическим скроллом сессий.

### 4. 📊 Hardware Telemetry NOC — Мониторинг датчиков Ring 0
* **Драйвер Ring 0**: Прямой опрос `LibreHardwareMonitorLib.dll` (pythonnet) с автоматическим fallback на `psutil` и Shared Memory AIDA64 (`mmap`).
* **Полная сводка датчиков**: Температуры, загрузка и частоты CPU/GPU/RAM/VRAM, активность дисков и пинг сети (ICMP Win32).
* **Аппаратные графики Sparkline**: Отрисовка истории метрик на Bezier-кривых в `QPainter` с динамической цветовой адаптацией под нагрузку.
* **NOC Dashboard 944×600**: Высокая плотность данных и контрастный мониторинг системы.

### 5. 🎬 Media Player / YouTube & Mini Media Bar
* **Аппаратная изоляция на iGPU**: Рендеринг Chromium изолирован на встроенной графике (`QTWEBENGINE_CHROMIUM_FLAGS`), исключая просадки FPS на дискретной видеокарте.
* **Сетевой перехватчик `AdBlockInterceptor`**: Блокировка рекламы, аналитики и трекеров на уровне URL-запросов Chromium.
* **Персистентный профиль**: Сохранение сессии в `%LOCALAPPDATA%/DuckDock/web_profile`.
* **Mini Media Bar**: Компактный плеер в сайдбаре с бегущей строкой `MarqueeLabel` и базовым управлением воспроизведением.

### 6. 🌙 Software Dimmer Overlay
* **Плавное затемнение**: Сквозной слой поверх экрана с регулировкой непрозрачности (0.0 .. 0.95).
* **Кинетическая анимация**: Плавное включение/отключение диммера (QVariantAnimation, OutCubic, 200 мс).

---

## 🏛 Архитектура проекта (Feature-First)

Проект строго следует 5 законам модульности (**Modularity Laws**):
1. **The Dependency Rule**: Зависимости направлены сверху вниз: `ui (Shell) -> modules (Features) -> core (Foundation)`. Слой `core/` изолирован и не импортирует `modules` или `ui`.
2. **Sibling Isolation**: Модули независимы друг от друга; взаимодействие осуществляется через шину `core.event_bus.bus` и DTO.
3. **Decoupled Audio & Deck**: COM-драйверы и модели конечных точек изолированы в подсистеме аудио.
4. **Stealth Focus Invariant**: Все экранные модули наследуются от `core.ui_base.TouchModuleView` с `Qt.NoFocus`.
5. **Re-export Shims**: Прозрачные фасады обратной совместимости в `core/` и `ui/modules/` гарантируют работу существующих тестов и интеграций.

```text
duckdock/
├── main.py                     # Точка входа: DPI Awareness V2, Chromium Flags, запуск
├── config.json                 # Пользовательские настройки (дисплей, тайминги, детекция)
├── pyproject.toml              # Метаданные проекта, зависимости, настройки pytest и ruff
├── requirements.txt            # Зафиксированные версии библиотек
│
├── core/                       # Архитектурный фундамент (Platform Primitives)
│   ├── dpi.py                  # Инициализация Per-Monitor DPI Awareness V2
│   ├── event_bus.py            # Централизованная шина сигналов PySide6
│   ├── window_manager.py       # Поиск HWND, удаление рамок окон сторонних приложений
│   ├── focus_guardian.py       # WS_EX_NOACTIVATE и хуки возврата фокуса/курсора
│   ├── mouse_barrier.py        # Блокировка вылета курсора мыши (ClipCursor)
│   ├── touch_filter.py         # Детекция касаний и распознавание 2-пальцевого свайпа
│   └── ui_base.py              # TouchModuleView (базовый класс с Qt.NoFocus и cleanup)
│
├── modules/                    # Автономные функциональные подсистемы (Feature-First)
│   ├── audio/                  # Сенсорный микшер, PyCaw, COM IPolicyConfigClient
│   │   ├── service.py          # AudioManager (управление сессиями и устройствами)
│   │   ├── models.py           # DTO: AudioSessionInfo, AudioDeviceInfo
│   │   ├── platform/           # COM-драйвер IPolicyConfigClient
│   │   └── view.py             # AudioMixerView (944x600)
│   ├── telemetry/              # Аппаратный мониторинг Ring 0 и NOC-дашборд
│   │   ├── hardware_monitor.py # LibreHardwareMonitor (Ring 0) + psutil fallback
│   │   ├── worker.py           # TelemetryWorker (фоновый поток QThread)
│   │   ├── history.py          # RingBuffer и история метрик
│   │   ├── models.py           # DTO TelemetrySnapshot
│   │   └── view.py             # SensorsView (NOC дашборд)
│   ├── media/                  # Мультимедиа и YouTube
│   │   ├── web_profile.py      # Профиль Chromium и кэш
│   │   ├── interceptor.py      # AdBlockInterceptor
│   │   ├── widgets/            # MiniMediaBar
│   │   └── view.py             # YouTubeView
│   ├── deck/                   # Сенсорная макро-панель DuckDeck
│   │   ├── action_dispatcher.py# Асинхронный диспетчер задач в QThreadPool
│   │   ├── models.py           # Pydantic V2 модели конфигурации кнопок и профилей
│   │   ├── actions/            # Драйверы: hotkey, audio_switcher, process, http, screen
│   │   ├── widgets/            # DeckButtonWidget, DotPagingWidget
│   │   └── view.py             # DeckView (матрица тайлов 944x600)
│   └── settings/               # Конфигурация и валидация
│       ├── config.py           # Pydantic-модели конфигурации приложения
│       └── view.py             # Экран настроек
│
├── ui/                         # Каркас оболочки (Shell)
│   ├── main_window.py          # Главное окно 1024x600 (Frameless, WS_EX_NOACTIVATE)
│   ├── sidebar.py              # Сайдбар 80x600 (сенсорные кнопки 64x64 + MiniMediaBar)
│   ├── dimmer_overlay.py       # Сквозной слой плавного затемнения
│   ├── showcase_view.py        # Витрина подсистем
│   └── widgets/                # Переиспользуемые UI-компоненты
│       ├── sparkline.py        # Аппаратный график на Bezier-кривых
│       ├── touch_slider.py     # Сенсорный ползунок с тактильным откликом
│       └── marquee_label.py    # Бегущая строка для медиаданных
│
└── tests/                      # Набор тестов (135 тестов: модульные и интеграционные)
    ├── unit/                   # Модульные тесты компонентов ядра и модулей
    └── integration/            # Сквозные интеграционные тесты
```

---

## 🚀 Быстрый старт

### Требования
* **ОС**: Windows 10/11 x64 (сборка 19041 или новее).
* **Python**: 3.11 или 3.12 (64-bit).
* **Права Администратора**: Рекомендуются для доступа Ring 0 к датчикам материнской платы через `LibreHardwareMonitorLib.dll`. При запуске без прав администратора монитор автоматически переключается на безопасный fallback (`psutil`).

### Установка зависимостей
```powershell
# Клонирование репозитория
git clone https://github.com/Einthel/duckdock.git
cd duckdock

# Создание и активация виртуального окружения
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Установка зависимостей
pip install -r requirements.txt
```

### Запуск приложения

```bat
# Режим разработки
dev.bat

# Стандартный запуск
run.bat
```

### Сборка автономного исполняемого файла (PyInstaller)

Сборка компилирует оптимизированную автономную директорию `--onedir` (`dist/DuckDock/`) со временем холодного старта менее 300 мс:

```bat
build.bat
```

---

## 🧪 Тестирование

Полный набор автоматических тестов включает 135 модульных и интеграционных тестов:

```powershell
pytest tests/
```

Запуск конкретных категорий тестов:
```powershell
# Только модульные тесты
pytest tests/unit/

# Только интеграционные тесты
pytest tests/integration/
```

---

## 📄 Лицензия

Проект распространяется под лицензией [MIT](LICENSE).
