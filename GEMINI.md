# Архитектурные правила и инварианты проекта DuckDock / TouchWM

> **Статус:** Активный закон кодовой базы  
> **Архетип:** `desktop_gui` (PySide6 / Qt, WinAPI Ctypes, PyWin32)  
> **Целевая среда:** Windows 10/11 x64, двухмониторная система (27" Primary dGPU + 7" Secondary 800x600 iGPU Touchscreen).

---

## 1. Архитектурные инварианты (Core Invariants)

1. **Zero-Bespoke Invariant & Platform-First:**
   * Все системные Win32 манипуляции (стили окон, хуки, фокус, DPI) изолируются в глубоких модулях слоя `core/` (`core.dpi`, `core.window_manager`, `core.focus_guardian`).
   * UI-модули не вызывают сырые WinAPI методы напрямую, а используют методы фасадов ядра.

2. **Per-Monitor DPI Awareness V2:**
   * В самом начале точки входа (`main.py`) до любых импортов PySide6 и инициализации `QApplication` должен быть выполнен вызов `core.dpi.init_dpi_awareness()`.
   * Никакие пересчеты координат не должны искажаться системным масштабированием (125%/150%) основного монитора.

3. **Stealth Focus & Anti-Cursor Warp:**
   * Корневое окно DuckDock обязано использовать расширенный стиль `WS_EX_NOACTIVATE` и атрибут `Qt.WA_ShowWithoutActivating`.
   * Все кнопки сайдбара и элементы управления по умолчанию получают `Qt.NoFocus`.
   * При фиксации тач-событий на втором мониторе фокус не должен отбираться у игры/IDE на основном 27" экране, а координаты системного курсора должны восстанавливаться на основной монитор через `core.focus_guardian`.

4. **iGPU Isolation (CASO Mitigation):**
   * Все параметры `QTWEBENGINE_CHROMIUM_FLAGS` инициализируются в окружении процесса до старта `QApplication`.
   * Рендеринг и декодирование видео изолируются на iGPU (AMD Radeon Graphics), исключая нагрузку на dGPU.

5. **Hotplug & Display Topology Resilience:**
   * Обработка событий `WM_DISPLAYCHANGE` обязательна для восстановления привязки к сетке 800×600 при выходе из спящего режима.

---

## 2. Структура проекта

```text
duckdock/
├── main.py                     # Точка входа, DPI Awareness, запуск QApplication
├── config.json                 # Пользовательские настройки (координаты, тайминги)
├── pyproject.toml              # Конфигурация инструментов (ruff, pytest)
├── requirements.txt            # Зафиксированные зависимости
├── core/                       # Архитектурный фундамент (Platform Primitives)
│   ├── config.py               # Загрузка и валидация настроек
│   ├── dpi.py                  # Инициализация DPI Awareness V2
│   ├── event_bus.py            # Централизованная шина сигналов / событий
│   ├── window_manager.py       # Поиск HWND, удаление рамок, тайлинг 720x600
│   ├── focus_guardian.py       # WS_EX_NOACTIVATE, возврат фокуса и курсора
│   ├── mouse_barrier.py        # Блокировка вылета курсора мыши
│   └── aida_reader.py          # Чтение Shared Memory (mmap) AIDA64
├── ui/                         # Представление (PySide6)
│   ├── main_window.py          # Главное окно 800x600 (Frameless)
│   ├── sidebar.py              # Сайдбар 80x600 (тач-кнопки 64x64)
│   ├── dimmer_overlay.py       # Сквозной слой затемнения экрана
│   ├── showcase_view.py        # Витрина состояния модулей
│   └── modules/
│       ├── sensors_view.py     # Монитор датчиков и телеметрии
│       └── youtube_view.py     # Медиаплеер / YouTube
└── tests/                      # Модульные и интеграционные тесты
```

---

## 3. Реестр ролей AI-агентов

* `@deep-researcher` — Архитектурный аудит и планирование (STRICT READ-ONLY).
* `@fullstack-builder` — Сквозная разработка модулей ядра и компонентов UI.
* `@code-review` — Pre-flight аудит изменений и инвариантов (STRICT READ-ONLY).
* `@bug-hunter` — Локализация и исправление дефектов, написание TDD-тестов.
* `@git-release-master` — Подготовка релизов и соблюдение Conventional Commits.
