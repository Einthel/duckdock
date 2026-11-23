# Actionable Roadmap: План реализации архитектурных рекомендаций Спринта 6 (Hardening & Memory Hygiene)

> **Статус:** Готов к исполнению  
> **Область:** `modules/deck/editor/` (Управление памятью QUndoStack и отказоустойчивость Drag-and-Drop)  
> **Цель:** Полное исключение утечек истории отмены при пагинации, защита от некорректных DND-пакетов и укрепление тестового покрытия.

---

## Матрица ответственности (RACI)

| Этап / Задача | Ответственный (R) | Контроль (A) | Консультация (C) | Информирование (I) |
| :--- | :--- | :--- | :--- | :--- |
| **Этап 1: Очистка QUndoStack при пагинации** | `@fullstack-builder` | `@bug-hunter` | `@code-review` | `@git-release-master` |
| **Этап 2: Защитная валидация Drag-and-Drop** | `@fullstack-builder` | `@bug-hunter` | `@code-review` | `@git-release-master` |
| **Этап 3: Регрессионный сьют и Pre-Flight** | `@bug-hunter` | `@code-review` | `@fullstack-builder` | `@git-release-master` |

---

## Этап 1. Гигиена памяти и жизненный цикл QUndoStack

### Цель этапа:
Исключить накопление истории команд от предыдущих страниц, предотвратить применение отката изменений к неактивной странице и устранить скрытые утечки памяти при долгой сессии редактирования.

### Шаги реализации:

* [x] **1.1. Очистка стека отмены при локальной смене страницы:**
  * Файл: `modules/deck/editor/window.py`
  * Метод: `DeckEditorWindow._on_pagination_page_changed()`
  * Действие: после сохранения изменений текущей страницы и перед загрузкой целевой страницы вызывать `self._undo_stack.clear()`.
  * Критерий: `self._undo_stack.count() == 0`, `self._undo_stack.canUndo() is False`.

* [x] **1.2. Очистка стека отмены при удаленной синхронизации через EventBus:**
  * Файл: `modules/deck/editor/window.py`
  * Метод: `DeckEditorWindow._on_bus_deck_page_changed()`
  * Действие: при переключении страницы со стороны физического тачскрина вызывать `self._undo_stack.clear()`.
  * Критерий: команды локального редактирования не сохраняются между удаленными переключениями страниц.

* [x] **1.3. Сброс истории в `load_configuration()` и `_on_pagination_clear_page_requested()`:**
  * Файл: `modules/deck/editor/window.py`
  * Действие: замена `self._undo_stack.setClean()` на `self._undo_stack.clear()` при полной перезагрузке страницы из файла; вызов `clear()` при контекстной очистке страницы пользователем.
  * Критерий: чистый стек при любой повторной загрузке страницы.

* [x] **1.4. TDD-тесты жизненного цикла истории команд:**
  * Файл: `tests/unit/test_deck_editor_undo.py`
  * Тесты:
    - `test_undo_stack_cleared_on_page_change`: проверка очистки стека и недоступности `undo()` после перехода на другую страницу.
    - `test_undo_stack_cleared_on_remote_bus_sync`: проверка сброса стека при эмиссии `bus.deck_page_changed`.
  * Критерий: 100% прохождение тестов без блокировок и зависаний.

#### Запуск шагов [1.1 — 1.4]:
```text
@fullstack-builder реализуй шаги 1.1 - 1.4 из .md/deck/sprint6_hardening_plan.md:
1. Добавь вызовы self._undo_stack.clear() в _on_pagination_page_changed, _on_bus_deck_page_changed, load_configuration и _on_pagination_clear_page_requested в modules/deck/editor/window.py.
2. Реализуй тесты test_undo_stack_cleared_on_page_change и test_undo_stack_cleared_on_remote_bus_sync в tests/unit/test_deck_editor_undo.py.
3. Критерий: pytest tests/unit/test_deck_editor_undo.py завершается со статусом 100% PASS.
```

#### Pre-Flight проверка этапа 1:
```text
@code-review проведи аудит реализации шагов [1.1 — 1.4]:
[Проверка сброса флагов canUndo/canRedo, чистота связывания с _is_dirty, отсутствие остаточных ссылок]
```

---

## Этап 2. Защитное программирование (Defensive Programming) в Drag-and-Drop

### Цель этапа:
Защитить ячейки холста `EditorGridCell` от некорректных, битых или враждебных MIME-сообщений, исключить `AttributeError` и сброс слота на самого себя.

### Шаги реализации:

* [x] **2.1. Строгая валидация структуры данных `action_dropped`:**
  * Файл: `modules/deck/editor/widgets/grid_cell.py`
  * Метод: `EditorGridCell.dropEvent()`
  * Действие:
    - Проверять тип десериализованного объекта: `isinstance(action_data, dict)`.
    - Проверять наличие обязательного строкового идентификатора: `bool(action_data.get("id"))`.
    - При непрохождении проверки: `logger.warning("Invalid action payload structure: %s", action_data)`, `event.ignore()`, отмена обработки.
  * Критерий: сброс произвольного JSON-примитива (число, строка, пустой словарь) не приводит к падению приложения.

* [x] **2.2. Защита диапазона слотов и блокировка Self-Drop:**
  * Файл: `modules/deck/editor/widgets/grid_cell.py`
  * Метод: `EditorGridCell.dropEvent()`
  * Действие:
    - Проверять диапазон индекса источника: `0 <= src_slot < 10`.
    - Блокировать сброс на самого себя прямо в ячейке: `if src_slot == self.slot_index: event.ignore(); return`.
  * Критерий: отсутствие пустых циклов `SwapButtonsCommand` и защита от выхода за границы индексов `[0..9]`.

* [x] **2.3. Дополнительные защитные тесты DND:**
  * Файл: `tests/unit/test_deck_editor_dnd.py`
  * Тесты:
    - `test_grid_cell_drop_action_malformed_payload_rejected`: отправка `int`, `str`, `{}` без `"id"`.
    - `test_grid_cell_drop_slot_self_drop_ignored`: сброс слота `3` на ячейку `3` не эмитирует `slot_dropped`.
    - `test_grid_cell_drop_slot_invalid_range_ignored`: сброс слота `-1` или `99` отклоняется.
  * Критерий: 100% покрытие граничных случаев DND.

#### Запуск шагов [2.1 — 2.3]:
```text
@fullstack-builder реализуй шаги 2.1 - 2.3 из .md/deck/sprint6_hardening_plan.md:
1. Усили валидацию payload в dropEvent файла modules/deck/editor/widgets/grid_cell.py (isinstance dict, наличие id, диапазон 0 <= src_slot < 10, исключение self-drop).
2. Напиши тесты test_grid_cell_drop_action_malformed_payload_rejected, test_grid_cell_drop_slot_self_drop_ignored, test_grid_cell_drop_slot_invalid_range_ignored в tests/unit/test_deck_editor_dnd.py.
3. Критерий: pytest tests/unit/test_deck_editor_dnd.py завершается со статусом 100% PASS.
```

#### Pre-Flight проверка этапа 2:
```text
@code-review проведи аудит реализации шагов [2.1 — 2.3]:
[Проверка надежности валидаторов, отсутствие необработанных исключений, сброс drag_hover в любых ветках]
```

---

## Этап 3. Регрессионный сьют и чеклист готовности (Definition of Done)

### Цель этапа:
Подтвердить стабильность всей системы DuckDeck после ужесточения логики управления памятью и DND.

### Шаги реализации:

* [x] **3.1. Запуск комплексных модульных и интеграционных тестов DuckDeck:**
  * Команда: `pytest tests/unit/test_deck_*.py tests/integration/test_deck_*.py -v`
  * Критерий: все тесты редактора (215+ тестов) зеленые.

* [x] **3.2. Запуск i18n-линтера:**
  * Команда: `pytest tests/core/test_i18n_linter.py -v`
  * Критерий: 6 из 6 тестов `PASS`, 100% паритет ключей, 0 нелокализованных строк.

* [x] **3.3. Запуск полного тестового набора репозитория:**
  * Команда: `pytest tests/`
  * Критерий: 449+ тестов `PASS`, 0 `FAILED`.

#### Запуск шагов [3.1 — 3.3]:
```text
@bug-hunter выполни верификацию шагов 3.1 - 3.3:
1. Запусти полный набор тестов редактора: pytest tests/unit -k "deck"
2. Запусти i18n-линтер: pytest tests/core/test_i18n_linter.py
3. Запусти сквозной сьют проекта: pytest tests/
4. Критерий: 100% PASS всех тестов, отсутствие зависаний и регрессий.
```

#### Итоговый аудит:
```text
@code-review проведи итоговый аудит выполнения спринта Hardening:
[Проверка Definition of Done, чистоты diff, соответствия архитектурным законам GEMINI.md]
```
