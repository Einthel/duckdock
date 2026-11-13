# Changelog: DuckDock / TouchWM

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
