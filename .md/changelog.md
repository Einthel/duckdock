# Changelog: DuckDock / TouchWM

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
