# Архитектурные правила и инварианты проекта DuckDock / TouchWM

> **Статус:** Активный закон кодовой базы  
> **Архетип:** `desktop_gui` (PySide6 / Qt, WinAPI Ctypes, PyWin32)  
> **Целевая среда:** Windows 10/11 x64, двухмониторная система (27" Primary 2560×1440 dGPU + 7" Secondary 1024×600 JRP7813S iGPU Touchscreen).

---

## 1. Архитектурные инварианты (Core Invariants)

1. **Zero-Bespoke Invariant & Platform-First:**
   * Все системные Win32 манипуляции (стили окон, хуки, фокус, DPI, барьер курсора) изолируются в глубоких модулях слоя `core/` (`core.dpi`, `core.window_manager`, `core.focus_guardian`, `core.mouse_barrier`, `core.audio_manager`).
   * UI-модули не вызывают сырые WinAPI методы напрямую, а используют методы фасадов ядра.

2. **Per-Monitor DPI Awareness V2:**
   * В самом начале точки входа (`main.py`) до любых импортов PySide6 и инициализации `QApplication` должен быть выполнен вызов `core.dpi.init_dpi_awareness()`.
   * Никакие пересчеты координат не должны искажаться системным масштабированием (125%/150%) основного монитора.

3. **Stealth Focus & Anti-Cursor Warp:**
   * Корневое окно DuckDock обязано использовать расширенный стиль `WS_EX_NOACTIVATE` и атрибут `Qt.WA_ShowWithoutActivating`.
   * Все кнопки сайдбара, слайдеры и элементы управления получают `Qt.NoFocus`.
   * При фиксации тач-событий на втором мониторе фокус не должен отбираться у игры/IDE на основном 27" экране, а координаты системного курсора должны восстанавливаться на основной монитор через `core.focus_guardian` и `core.mouse_barrier`.

4. **iGPU Isolation (CASO Mitigation):**
   * Все параметры `QTWEBENGINE_CHROMIUM_FLAGS` инициализируются в окружении процесса до старта `QApplication`.
   * Рендеринг и декодирование видео изолируются на iGPU (AMD Radeon Graphics), исключая нагрузку на dGPU.

5. **Hotplug & Display Topology Resilience:**
   * Обработка событий `WM_DISPLAYCHANGE` обязательна для восстановления привязки к координатной сетке 1024×600 при выходе из спящего режима.

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
│   ├── window_manager.py       # Поиск HWND, удаление рамок, тайлинг 944x600
│   ├── focus_guardian.py       # WS_EX_NOACTIVATE, возврат фокуса и курсора
│   ├── mouse_barrier.py        # Блокировка вылета курсора мыши
│   ├── touch_filter.py         # Детекция и фильтрация тач-сообщений
│   ├── audio_manager.py        # Windows Core Audio API (PyCaw) фасад
│   └── aida_reader.py          # Чтение Shared Memory (mmap) AIDA64
├── ui/                         # Представление (PySide6)
│   ├── main_window.py          # Главное окно 1024x600 (Frameless)
│   ├── sidebar.py              # Сайдбар 80x600 (тач-кнопки 64x64)
│   ├── dimmer_overlay.py       # Сквозной слой затемнения экрана
│   ├── showcase_view.py        # Витрина состояния модулей
│   └── modules/
│       ├── sensors_view.py     # Монитор датчиков и телеметрии
│       ├── youtube_view.py     # Медиаплеер / YouTube
│       └── audio_view.py       # Сенсорный аудиомикшер PyCaw (TouchSlider)
└── tests/                      # Модульные и интеграционные тесты
```

---

## 3. Реестр ролей AI-агентов

* `@deep-researcher` — Архитектурный аудит и планирование (STRICT READ-ONLY).
* `@fullstack-builder` — Сквозная разработка модулей ядра и компонентов UI.
* `@code-review` — Pre-flight аудит изменений и инвариантов (STRICT READ-ONLY).
* `@bug-hunter` — Локализация и исправление дефектов, написание TDD-тестов.
* `@git-release-master` — Подготовка релизов и соблюдение Conventional Commits.

---

## 4. Релизный чеклист и синхронизация памяти (Definition of Done)

Перед каждым релизом новой версии или слиянием фиче-ветки в `main` агент обязан выполнить полный протокол:

1. **Автоматическое тестирование:**
   * Запуск `pytest tests/` — 100% тестов должны иметь статус `PASS`. При наличии `FAILED` коммит и слияние блокируются.
2. **Версионирование:**
   * Синхронизация версии в `pyproject.toml` (поле `version = "X.Y.Z"`).
3. **Журнал изменений (Changelog):**
   * В `.md/changelog.md` добавлена секция `## [X.Y.Z] — YYYY-MM-DD` со списками Added / Changed / Fixed по стандарту Keep a Changelog.
4. **Спецификация модулей (Backend Spec):**
   * В `.md/backend.md` обновлены архитектурная Mermaid-схема, открытые контракты ядра и сигналы `EventBus`.
5. **Семантическая память Serena:**
   * В MCP Serena обновлен слепок `architecture` через `serena:write_memory(memory_name="architecture", content=...)`.
   * При изменении инвариантов фокуса или аудиостека — актуализировать `focus_invariants` и `audio_subsystem`.
6. **Memory Bank проекта:**
   * В MCP Memory Bank обновлены файлы проекта `duckdock`:
     - `activeContext.md` — текущий статус, затронутые модули, ключевые решения.
     - `progress.md` — статус спринтов, закрытые задачи бэклога и метрики тестов.

---

## 5. Стандарт оформления планов и декомпозиции (Actionable Roadmap)

Любой план реализации (включая `*_plan.md`, RFC и чек-листы задач) должен быть интерактивным и готовым к немедленному исполнению AI-агентами.

### Требования к этапам и шагам:

1. **Actionable Prompts (Промпты запуска):**
   К каждому этапу (или логической группе связанных шагов) ОБЯЗАТЕЛЬНО прикладывается блок готовых команд для прямого запуска агентов.
   - Промпт должен начинаться с вызова конкретного агента по роли: `@fullstack-builder`, `@frontend-ui-designer`, `@bug-hunter` и др.
   - Должен содержать точные номера пунктов плана, пути к файлам и конкретную цель шага.
   
2. **Шаблон блока промптов к этапу:**
   ```text
   #### Запуск шагов [X.Y]:
   @<agent-name> реализуй шаг X.Y из <file_plan.md>:
   1. [Конкретное действие / контракт / файлы]
   2. [Критерий завершения]

   #### Pre-Flight проверка:
   @code-review проведи аудит реализации шага X.Y:
   [Инварианты, отсутствие утечек, чистота diff]
   ```

3. **Синхронизация с RACI:**
   Агент в промпте должен строго соответствовать матрице ответственности (RACI), зафиксированной в плане.

