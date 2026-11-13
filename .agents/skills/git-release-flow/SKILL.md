---
name: git-release-flow
description: "Стандарты управления ветками Git, подготовка релизов, Conventional Commits, чеклист Definition of Done перед слиянием и интеграция с GitHub Issues/PRs"
---

# Git & GitHub Release Workflow Standard

Этот навык регламентирует процессы ветвления, коммитов, слияний, контроля версий, синхронизации памяти и взаимодействия с GitHub в рабочих проектах.

---

## 1. Стратегия ветвления (Branching Strategy)

В проекте используется адаптированный **Trunk-Based / Feature-Branch Workflow**:

* **`main`**:
  * Защищённая стабильная ветка.
  * Код в `main` всегда обязан проходить все тесты (`pytest`) и компилироваться / запускаться без ошибок.
  * Прямые коммиты в `main` без предварительного тестирования **запрещены**.
* **`feature/<name>`** (например, `feature/audio-mixer`, `feature/sensors-monitor`):
  * Разработка изолированного крупного функционала.
  * Время жизни: от нескольких часов до нескольких дней.
  * Завершается обязательным слиянием в `main` после выполнения чеклиста готовности.
* **`bugfix/<name>`** или **`hotfix/<name>`** (например, `bugfix/cursor-leak`):
  * Исправление дефектов ядра или интерфейса.
  * Для критических багов создается напрямую от `main`.

---

## 2. Стандарт семантических коммитов (Conventional Commits)

Формат сообщения коммита:
```
<type>(<scope>): <краткое описание в настоящем времени>

[опциональное подробное тело коммита]

[опциональный футер: Closes #12, Refs #45]
```

### Допустимые типы (`<type>`):
* **`feat`**: новая функциональность (например, `feat(audio): add Core Audio mixer and touch UI`).
* **`fix`**: исправление ошибки или бага (например, `fix(cursor): restore position on primary monitor`).
* **`refactor`**: изменение кода без изменения функционала (например, `refactor(window): optimize HWND search`).
* **`docs`**: обновление документации, чанджлога, планов (например, `docs: update changelog for v0.1.3`).
* **`test`**: добавление или правка тестов (например, `test(audio): add TouchSlider interaction tests`).
* **`chore`**: рутинные задачи, обновление зависимостей, версий.

### Допустимые области (`<scope>`):
`core`, `ui`, `audio`, `sensors`, `window`, `focus`, `mouse`, `config`, `tests`.

---

## 3. Чеклист перед слиянием в `main` (Definition of Done)

Перед вызовом `git merge` агент обязан последовательно проверить:

- [ ] **1. Чистота рабочего дерева**:
  - `git status` не содержит незафиксированных временных файлов, баз данных (`*.db-wal`, `*.db-shm`), дампов или кэшей (`__pycache__`, `.pytest_cache`).
- [ ] **2. Запуск автоматических тестов**:
  - Выполнить `pytest` (или `pytest tests/`).
  - Все тесты (100%) обязаны иметь статус `PASS`. Никаких пропущенных регрессий.
- [ ] **3. Централизация версии**:
  - Версия синхронизирована в `pyproject.toml` (поле `version = "X.Y.Z"`) и/или `__version__` в корневом пакете.
- [ ] **4. Журнал изменений (Changelog)**:
  - В `.md/changelog.md` добавлена секция `## [X.Y.Z] — YYYY-MM-DD` со списками Added / Changed / Fixed по стандарту Keep a Changelog.
- [ ] **5. Синхронизация архитектуры и памяти (Backend Spec, Serena, Memory Bank)**:
  - В `.md/backend.md` обновлены архитектурная Mermaid-схема, список модулей и открытые контракты.
  - В MCP Serena обновлена память `architecture` (`serena:write_memory`), а также специфические контексты подсистем при их изменении.
  - В MCP Memory Bank обновлены `activeContext.md` (текущий статус, ключевые решения) и `progress.md` (закрытые спринты, метрики тестов).
- [ ] **6. Отсутствие конфликтов**:
  - Ветка `main` синхронизирована с удалённым репозиторием `origin/main`.
  - Слияние выполняется предпочтительно через Fast-Forward:
    ```bash
    git checkout main
    git pull origin main
    git merge feature/<name>
    git push origin main
    ```

---

## 4. Интеграция с GitHub (Issues, PRs, Releases)

При наличии доступа к GitHub MCP (`@modelcontextprotocol/server-github`):

1. **Отслеживание багов (Issues)**:
   - При обнаружении системного дефекта создается тикет:
     - Заголовок: `[Bug]: <краткое описание проблемы>`.
     - Описание: шаги воспроизведения, ожидаемое поведение, системный лог.
     - Метки (Labels): `bug`, `backend` или `frontend`.
   - В коммите с фиксом указывать `Fixes #<номер>`.
2. **Pull Requests (PR)**:
   - Создание PR из рабочей ветки в `main` с перечислением пунктов Definition of Done.
   - Проверка статуса CI/CD (если настроены GitHub Actions).
   - Выполнение слияния (`merge_pull_request`).
3. **Релизные теги (Tags)**:
   - Фиксация релиза в Git:
     ```bash
     git tag -a v0.1.3 -m "Release v0.1.3: PyCaw Core Audio mixer and touch UI"
     git push origin v0.1.3
     ```
