# План архитектурной стабилизации и устранения дефектов редактора кнопок DuckDeck

> **Статус:** План актуализирован и расширен архитектурной группой (`@deep-researcher` & `@fullstack-builder`), готов к исполнению  
> **Целевые файлы:**  
> - `modules/deck/presets.py`  
> - `modules/deck/editor/actions_registry.py`  
> - `modules/deck/editor/widgets/button_property_form.py`  
> - `modules/deck/editor/adapter.py`  
> - `modules/deck/editor/window.py`  
> - `modules/deck/editor/widgets/action_drawer.py`  
> - `locales/ru.json`, `locales/en.json`  
> - `tests/unit/test_deck_editor_adapter.py`, `tests/unit/test_deck_property_form.py`, `tests/unit/test_deck_presets_and_executors.py`, `tests/unit/test_deck_editor_action_drawer.py`, `tests/unit/test_i18n_linter.py`  
> **Дизайн-система и инварианты:** Dark Obsidian v2, PySide6, WS_EX_NOACTIVATE, Bilingual Localization-First (RU/EN), Zero-Bespoke Invariant.

---

## 1. Архитектурный контекст и первопричины дефектов (RCA)

В ходе глубокого исследования подсистемы кнопочного редактора (`modules/deck/editor`), реестров действий и диспетчеризации параметров выявлены 5 фундаментальных причин нестабильного поведения («кнопки работают в разнобой», «атрибуты сбиваются при выборе заготовок», «каталоги рассинхронизированы»):

1. **Раздвоение каталогов (Dual Catalog Split & Lack of SSOT):**  
   В проекте сосуществуют два независимых реестра:
   - `modules/deck/presets.py` (`ActionPresetsRegistry`): 8 категорий таксономии, 26+ декларативных пресетов (`ActionPresetDefinition`) с полноценными `base_action`, преднастроенными иконками, цветами акцента и источниками живого статуса (`status_source`). Используется в шторке `ActionLibraryDrawer` и в меню «⚡ Шаблоны...».
   - `modules/deck/editor/actions_registry.py` (`get_default_action_catalog`): устаревший реестр из 6 категорий с плоскими `ActionItemDTO` без `base_action` и без параметров. В нем содержатся фантомные действия без серверной поддержки (`create_folder`, `brightness`, `switch_profile`, `page_indicator`, `macro_sequence`).
   *Следствие:* При drag-and-drop или программном вызове срабатывают fallback-ветки, создающие пустые DTO без параметров и иконок. Отсутствует Единый Источник Правды (Single Source of Truth).

2. **Разрыв таксономии типов и маршрутизации подформ (Type Mismatch & Subform Routing Failure):**  
   В ядре (`modules/deck/models.py`) зафиксировано **8 канонических примитивов** `ActionType` (`hotkey`, `launch`, `audio`, `media`, `text`, `system`, `deck_nav`, `macro`).  
   Однако в форме `ButtonPropertyForm` подформы параметров искусственно расщеплены на **13 специализированных виджетов**:
   - `audio` расщеплен на `volume_control` (индекс 5), `audio_device` (индекс 7), `soundboard` (индекс 10);
   - `system` расщеплен на `system` (индекс 9) и `screenshot` (индекс 8);
   - `hotkey` расщеплен на `hotkey` (индекс 0) и `hotkey_switch` (индекс 1);
   - `launch` объединяет `open_app`, `open_path`, `website` внутри `PathUrlSubform` (индекс 2).  
   *Следствие:* При перетаскивании кнопки скриншота (`action_type="system"`, `command="screenshot"`) форма переключается на `SystemSubform` (индекс 9), где вообще нет команды скриншота, и параметры заготовки затираются дефолтным диммером. При выборе заготовок переключения устройств (`action_type="audio"`) комбобокс ищет `"audio"`, которого нет среди видимых пунктов, сбивая отображение.

3. **Коллизия `dto.hotkey` vs `dto.action_type` в `DeckConfigAdapter`:**  
   В методе `DeckConfigAdapter.dto_to_slot` приоритет отдан условию `if dto.hotkey and dto.hotkey.strip():`. Если у кнопки ранее был настроен любой хоткей, смена действия пользователем на Запуск программы, Звук или Системную команду игнорируется: кнопка при сохранении насильно откатывается обратно в `hotkey`.

4. **Взаимное загрязнение словаря `action_params` (Cross-Contamination):**  
   Метод `ButtonPropertyForm.load_slot_data` транслирует один и тот же сырой словарь `mapped_params` во все 13 подформ подряд. Поля `target="master"` из аудио попадают в `launch` (где `target` обязан быть путем к `.exe` или URL), либо параметры звука перетекают в `system`, приводя к исключениям валидации Pydantic и непреднамеренному выполнению чужих команд.

5. **Циклический импорт `presets.py <-> editor`:**  
   Файл `modules/deck/presets.py` на верхнем уровне импортирует `from modules.deck.editor.dto import ActionCategoryDTO, ActionItemDTO`. Пакет `modules.deck.editor` в своем `__init__.py` импортирует `demo_data.py`, который импортирует `ActionPresetsRegistry` из `presets.py`. Это приводит к сбою сборки тестов `ImportError: cannot import name 'ActionPresetsRegistry' from partially initialized module`.

---

## 2. Матрица ответственности (RACI)

| Фаза / Задача | Responsible (R) | Accountable (A) | Consulted (C) | Informed (I) |
| :--- | :--- | :--- | :--- | :--- |
| **Фаза 1: Разрыв циклического импорта и устранение коллизии hotkey** | `@bug-hunter` | `@fullstack-builder` | `@deep-researcher` | `@code-review` |
| **Фаза 2: Унификация каталогов в SSOT и чистка фантомных действий** | `@fullstack-builder` | `@fullstack-builder` | `@deep-researcher` | `@code-review` |
| **Фаза 3: Детерминированная маршрутизация подформ и мапинг атрибутов** | `@fullstack-builder` | `@fullstack-builder` | `@deep-researcher` | `@code-review` |
| **Фаза 4: Изоляция параметров подформ и защита адаптера от слияния** | `@fullstack-builder` | `@fullstack-builder` | `@deep-researcher` | `@code-review` |
| **Фаза 5: Локализация (RU/EN), документация и регрессионный аудит** | `@code-review` | `@git-release-master` | `@deep-researcher` | Команда |

---

## 3. Детальный план реализации по фазам

```
  ┌─────────────────────────────────────────────────────────────┐
  │ Фаза 1: Разрыв циклического импорта и фикс коллизии hotkey │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Фаза 2: Унификация каталогов в единый SSOT и чистка действий│
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Фаза 3: Детерминированная маршрутизация подформ инспектора │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Фаза 4: Изоляция action_params и защита адаптера от слияния │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ Фаза 5: Локализация (RU/EN), тесты и релизный чек-лист DoD  │
  └─────────────────────────────────────────────────────────────┘
```

---

### Фаза 1. Разрыв циклического импорта и стабилизация типов действий

#### Шаг 1.1. Устранение циклической зависимости между `presets.py` и `editor`
* **Файл:** `modules/deck/presets.py`, `modules/deck/editor/__init__.py`
* **Суть изменений:**
  1. В `modules/deck/presets.py` перенести импорт `from modules.deck.editor.dto import ActionCategoryDTO, ActionItemDTO` внутрь метода `get_categories_dto()` (Lazy Import), либо использовать прямое инстанциирование DTO без цикличности.
  2. В `modules/deck/editor/__init__.py` исключить eager-импорт `demo_data.py`, переведя демонстрационные вспомогательные функции на ленивый экспорт по требованию.
  3. Проверить мгновенный импорт `python -c "from modules.deck.presets import ActionPresetsRegistry"`.

#### Шаг 1.2. Принудительный сброс `hotkey` в форме при выборе другого типа
* **Файл:** `modules/deck/editor/widgets/button_property_form.py`
* **Метод:** `_on_action_type_changed(self, index: int)`
* **Суть изменений:**
  При смене типа действия на любой, отличный от `"hotkey"`:
  1. Вызывать `self.subform_hotkey.set_hotkey("")` для визуальной очистки кнопки захвата клавиш.
  2. Эмитить сигнал изменения свойства: `self.property_changed.emit("hotkey", "")`.
  3. Для типа `"hotkey"` восстанавливать значение только при явном вводе пользователем или загрузке пресета типа `hotkey`.

#### Шаг 1.3. Рефакторинг ветвления приоритетов в `DeckConfigAdapter.dto_to_slot`
* **Файл:** `modules/deck/editor/adapter.py`
* **Метод:** `dto_to_slot(cls, dto: ButtonSlotDTO, original_config: Optional[DeckButtonConfig] = None)`
* **Суть изменений:**
  Инвертировать логику разрешения действия:
  ```python
  norm_type = cls._normalize_action_type(dto.action_type) if dto.action_type else "system"

  if norm_type == "hotkey":
      # Только если тип явно hotkey, читаем dto.hotkey
      parsed_keys = cls._parse_hotkey_string(dto.hotkey) if dto.hotkey else []
      action = DeckActionConfig(action_type="hotkey", params={"keys": parsed_keys})
      category = "shortcut"
  else:
      # Для всех остальных типов dto.hotkey игнорируется
      if orig and norm_type == orig.action.action_type:
          action = orig.action.model_copy(deep=True)
          category = orig.category
      else:
          action, category = cls._create_default_action(norm_type)
      if dto.action_params:
          action.params.update(dto.action_params)
  ```
  Аналогичное исправление применить к ветке создания нового слота без `original_config` (строки 268–280).

#### Шаг 1.4. Синхронизация логики при очистке слота и Drag-and-Drop
* **Файл:** `modules/deck/editor/window.py`
* **Методы:** `_on_canvas_action_dropped`, `_on_inspector_slot_cleared`
* **Суть изменений:**
  Гарантировать, что при сбросе любого действия из библиотеки, не являющегося `"hotkey"`, в `new_dto.hotkey` явно записывается пустая строка `""`.

#### Шаг 1.5. Модульное TDD-тестирование
* **Файлы:** `tests/unit/test_deck_presets_and_executors.py`, `tests/unit/test_deck_editor_adapter.py`
* **Тесты:**
  - `test_presets_import_without_circular_error`: отсутствие ошибки импорта `ActionPresetsRegistry`.
  - `test_dto_to_slot_switches_from_hotkey_to_launch_without_reversion`: проверка, что кнопка с существующим хоткеем при установке `dto.action_type = "launch"` сохраняется как `launch`, а не `hotkey`.
  - `test_dto_to_slot_clears_hotkey_on_audio_action`: проверка сохранения аудио-действия без отката в хоткей.

---

#### Запуск Фазы 1:
```text
@bug-hunter реализуй Фазу 1 из .md/deck/edit_atrib1.md:
1. В modules/deck/presets.py и modules/deck/editor/__init__.py устрани циклический импорт ActionPresetsRegistry <-> demo_data.
2. В modules/deck/editor/widgets/button_property_form.py (_on_action_type_changed) добавь сброс hotkey в пустую строку при смене действия на не-hotkey.
3. В modules/deck/editor/adapter.py (dto_to_slot) измени приоритет ветвления: norm_type == "hotkey" определяет обработку hotkey, иначе создается или обновляется действие целевого action_type.
4. В modules/deck/editor/window.py (_on_canvas_action_dropped) подтверди сброс hotkey = "" для не-hotkey действий.
5. Запусти pytest tests/unit/test_deck_presets_and_executors.py tests/unit/test_deck_editor_adapter.py.
```

#### Pre-Flight проверка Фазы 1:
```text
@code-review проведи аудит реализации Фазы 1:
1. Проверь отсутствие циклических импортов при прямом вызове python -c "from modules.deck.presets import ActionPresetsRegistry".
2. Проверь отсутствие регрессий при сохранении существующих hotkey-кнопок.
3. Убедись, что смена типа действия не оставляет мусорный hotkey в DTO.
```

---

### Фаза 2. Унификация каталогов в единый SSOT и чистка фантомных действий

#### Шаг 2.1. Объявление `ActionPresetsRegistry` единственным источником правды (SSOT)
* **Файл:** `modules/deck/editor/actions_registry.py`
* **Суть изменений:**
  1. Прекратить отдельное дублирующее ведение статического списка категорий в `actions_registry.py`.
  2. Переписать функцию `get_default_action_catalog() -> list[ActionCategoryDTO]`, сделав ее тонким фасадом над `ActionPresetsRegistry.get_categories_dto()`.
  3. Это гарантирует, что в любых тестах, окнах и виджетах каталог кнопок будет на 100% идентичен, согласован и всегда содержать валидные карточки пресетов с `base_action`.

#### Шаг 2.2. Удаление фантомных действий (`create_folder`, `brightness`, `page_indicator`)
* **Файлы:**
  - `modules/deck/presets.py`
  - `modules/deck/editor/widgets/button_property_form.py`
  - `modules/deck/editor/adapter.py`
* **Суть изменений:**
  1. Из `presets.py` удалить пресет `create_folder` (строки 533–545). В категории `navigation` остаются строго рабочие навигационные действия: `nav_next_page` и `nav_prev_page`.
  2. В `button_property_form.py` из `DeckNavSubform` удалить неиспользуемую опцию `folder_open`.
  3. Удалить устаревшие нормализации `brightness`, `page_indicator`, `create_folder` из `DeckConfigAdapter._normalize_action_type`.

#### Шаг 2.3. Заглушка профилей (`switch_profile`) под будущие авто-профили
* **Файлы:** `modules/deck/presets.py`, `modules/deck/editor/widgets/button_property_form.py`, `locales/ru.json`, `locales/en.json`
* **Суть изменений:**
  1. В `ActionPresetsRegistry` пресет `switch_profile` не добавлять в активные шаблоны либо пометить флагом `is_enabled=False`.
  2. В `button_property_form.py` пункт «Сменить профиль» в комбобоксе отображать неактивным (`setEnabled(False)`).
  3. В коде зафиксировать архитектурный контракт:
     ```python
     # FUTURE ARCHITECTURE:
     # 'switch_profile' зарезервирован для автоматического переключения профилей DuckDeck
     # по событиям фокуса Windows (EVENT_SYSTEM_FOREGROUND / WinEventProc).
     ```

#### Шаг 2.4. Блокировка и маркировка WIP для макро-цепочек (`macro_sequence`)
* **Файлы:** `modules/deck/presets.py`, `modules/deck/editor/widgets/action_drawer.py`, `locales/ru.json`, `locales/en.json`
* **Суть изменений:**
  1. В `presets.py` для `macro_sequence` установить атрибут `is_wip = True`. В заголовке отображать суффикс `(В разработке)` / `(In Dev)`.
  2. В `ActionLibraryDrawer` карточки с `is_wip=True` отображать с пониженной прозрачностью (opacity 0.5) и тултипом о ведущейся разработке конструктора цепочек, блокируя случайное назначение пустого макроса на кнопку.
  3. Ядерный исполнитель `MacroExecutor` в `modules/deck/executors.py` полностью сохраняется.

---

#### Запуск Фазы 2:
```text
@fullstack-builder реализуй Фазу 2 из .md/deck/edit_atrib1.md:
1. В modules/deck/editor/actions_registry.py сделай get_default_action_catalog() фасадом над ActionPresetsRegistry.get_categories_dto().
2. В modules/deck/presets.py удали пресет create_folder. Оставь только nav_next_page и nav_prev_page.
3. В modules/deck/editor/widgets/button_property_form.py удали folder_open из DeckNavSubform.
4. Пометь macro_sequence флагом is_wip=True и заблокируй перетаскивание незавершенных макросов.
5. Актуализируй тесты в tests/unit/test_deck_editor_action_drawer.py и tests/unit/test_deck_presets_and_executors.py.
```

#### Pre-Flight проверка Фазы 2:
```text
@code-review проведи аудит реализации Фазы 2:
1. Убедись, что get_default_action_catalog() возвращает единый каталог из ActionPresetsRegistry.
2. Проверь отсутствие фантомных кнопок create_folder, brightness, page_indicator.
3. Проверь 100% прохождение тестов каталога.
```

---

### Фаза 3. Детерминированная маршрутизация подформ и синхронизация атрибутов заготовок

#### Шаг 3.1. Создание матрицы маршрутизации подформ (Subform Routing Matrix)
* **Файл:** `modules/deck/editor/widgets/button_property_form.py`
* **Суть изменений:**
  Создать статический или вспомогательный метод класса формы:
  `resolve_subform_route(action_type: str, params: dict) -> tuple[int, str, dict]`
  Регламент маршрутизации:
  1. `norm_type == "launch"`:
     - Если `params.get("kind") == "url"` или `target.startswith(("http://", "https://"))`:
       $\rightarrow$ Стек индекс **2** (`PathUrlSubform`), режим `"website"`.
     - Если `params.get("kind") == "file"` или путь ведет к файлу/папке:
       $\rightarrow$ Стек индекс **2** (`PathUrlSubform`), режим `"open_path"`.
     - Иначе:
       $\rightarrow$ Стек индекс **2** (`PathUrlSubform`), режим `"open_app"`.
  2. `norm_type == "audio"`:
     - Если `target == "device"` или `command == "toggle_device"` или `"devices"` в params:
       $\rightarrow$ Стек индекс **7** (`AudioDeviceSubform`).
     - Если `target == "soundboard"` или `command in ("play_sound", "stop_sound")`:
       $\rightarrow$ Стек индекс **10** (`SoundboardSubform`).
     - Если `target in ("master", "mic", "focus_app")` или `command in ("toggle_mute", "step", "set_level")`:
       $\rightarrow$ Стек индекс **5** (`VolumeSubform`).
  3. `norm_type == "system"`:
     - Если `command == "screenshot"`:
       $\rightarrow$ Стек индекс **8** (`ScreenshotSubform`).
     - Если `command in ("dimmer", "toggle_dimmer", "lock_pc", "lock_workstation", "sleep_display")`:
       $\rightarrow$ Стек индекс **9** (`SystemSubform`).
     - Если `command == "close_window"`:
       $\rightarrow$ Стек индекс **6** (`NoParamsSubform`).
  4. `norm_type == "hotkey"`:
     - Если `mode == "toggle"` или `params.get("toggle_keys")`:
       $\rightarrow$ Стек индекс **1** (`HotkeySwitchSubform`).
     - Иначе:
       $\rightarrow$ Стек индекс **0** (`HotkeySubform`).
  5. `norm_type == "media"` $\rightarrow$ Стек индекс **3** (`MultimediaSubform`).
  6. `norm_type == "text"` $\rightarrow$ Стек индекс **4** (`TextMacroSubform`).
  7. `norm_type == "deck_nav"` $\rightarrow$ Стек индекс **11** (`DeckNavSubform`).
  8. `norm_type == "macro"` $\rightarrow$ Стек индекс **6** (`NoParamsSubform`).

#### Шаг 3.2. Нормализация системных команд (`dimmer` $\leftrightarrow$ `toggle_dimmer`, `lock_pc` $\leftrightarrow$ `lock_workstation`)
* **Файлы:**
  - `modules/deck/editor/widgets/button_property_form.py`
  - `modules/deck/presets.py`
  - `modules/deck/models.py`
* **Суть изменений:**
  1. Синхронизировать строковые литералы команд:
     - В `SystemSubform` поддерживать и `dimmer`, и `toggle_dimmer` (выбирая соответствующий пункт в `combo_cmd`).
     - В `SystemSubform` поддерживать и `lock_pc`, и `lock_workstation`.
  2. В `presets.py` убедиться, что пресеты `toggle_dimmer` и `lock_workstation` используют канонические команды, совпадающие со списком в `SystemSubform`.

#### Шаг 3.3. Рефакторинг `apply_preset` и `load_slot_data`
* **Файл:** `modules/deck/editor/widgets/button_property_form.py`
* **Методы:** `apply_preset(self, preset_id: str)`, `load_slot_data(self, dto: ButtonSlotDTO)`
* **Суть изменений:**
  1. В `apply_preset` использовать единый `resolve_subform_route`.
  2. Переключать `combo_actions` на соответствующий базовый примитив (для `audio` выбирать `"audio"`, для `system` — `"system"`).
  3. Переключать `params_stack` на точный вычисленный индекс подформы.
  4. Передавать параметры пресета **только** в целевую подформу через ее нативный метод `set_params(params)`.
  5. В `load_slot_data` устранить цепочки костыльных условий `raw_action in (...)` и перевести на `resolve_subform_route`.

---

#### Запуск Фазы 3:
```text
@fullstack-builder реализуй Фазу 3 из .md/deck/edit_atrib1.md:
1. В modules/deck/editor/widgets/button_property_form.py реализуй централизованный resolve_subform_route.
2. Обеспечь корректное переключение подформы ScreenshotSubform для пресетов screenshot_primary.
3. Обеспечь разделение аудио-подформ (VolumeSubform vs AudioDeviceSubform vs SoundboardSubform) по параметрам target/command.
4. Синхронизируй ключи команд в SystemSubform и пресетах (dimmer/toggle_dimmer, lock_pc/lock_workstation).
5. Напиши тесты корректности маршрутизации пресетов в tests/unit/test_deck_property_form_subforms.py.
```

#### Pre-Flight проверка Фазы 3:
```text
@code-review проведи аудит реализации Фазы 3:
1. Проверь, что применение любого пресета из ActionPresetsRegistry открывает ровно предназначенную ему подформу.
2. Проверь сохранение параметров скриншота и аудиоустройств без затирания дефолтными значениями.
```

---

### Фаза 4. Изоляция параметров подформ и защита от взаимного загрязнения

#### Шаг 4.1. Очистка и дефолтная инициализация `action_params` при смене типа в интерфейсе
* **Файл:** `modules/deck/editor/widgets/button_property_form.py`
* **Метод:** `_on_action_type_changed(self, index: int)`
* **Суть изменений:**
  1. При смене действия комбобокса генерировать чистый эталонный словарь дефолтных параметров для выбранного типа (например, `target="master", command="toggle_mute"` для `audio`, `target="", kind="app"` для `launch`).
  2. Эмитить сигнал сброса параметров: `self.property_changed.emit("action_params", default_params)`.
  3. Для неактивных подформ вызывать сброс состояния (`reset()` или `set_params({})`), исключая срабатывание сигналов от чужих элементов ввода.

#### Шаг 4.2. Селективная загрузка параметров в активную подформу
* **Файл:** `modules/deck/editor/widgets/button_property_form.py`
* **Метод:** `load_slot_data(self, dto: ButtonSlotDTO)`
* **Суть изменений:**
  1. Вычислять активную подформу через `resolve_subform_route`.
  2. Вызывать `set_params` **исключительно** у активной подформы.
  3. Для остальных 12 подформ сбрасывать внутренние поля во избежание генерации ложных сигналов `params_changed`.

#### Шаг 4.3. Защита от мусорного слияния параметров в `DeckConfigAdapter.dto_to_slot`
* **Файл:** `modules/deck/editor/adapter.py`
* **Метод:** `dto_to_slot`
* **Суть изменений:**
  Запретить неконтролируемый `.update()` чужих словарей:
  ```python
  if norm_type != orig.action.action_type:
      # Смена типа: создаем чистые дефолтные параметры для нового типа
      action, category = cls._create_default_action(norm_type)
      if dto.action_params and cls._is_params_valid_for_type(norm_type, dto.action_params):
          action.params.update(dto.action_params)
  else:
      # Тип совпадает: обновляем существующие параметры
      action = orig.action.model_copy(deep=True)
      if dto.action_params:
          action.params.update(dto.action_params)
  ```

#### Шаг 4.4. Модульное тестирование изоляции подформ
* **Файл:** `tests/unit/test_deck_property_form_subforms.py`
* **Тесты:**
  - `test_subform_params_not_leaked_on_type_switch`: переключение с `audio` (master mute) на `system` (dimmer) не должно сохранять ключи `target` и `step_percent` в итоговом объекте.
  - `test_launch_params_not_corrupted_by_audio_target`: проверка, что `target="master"` из аудио не становится путем запуска программы в `launch`.

---

#### Запуск Фазы 4:
```text
@fullstack-builder реализуй Фазу 4 из .md/deck/edit_atrib1.md:
1. В modules/deck/editor/widgets/button_property_form.py (_on_action_type_changed и load_slot_data) обеспечь селективную передачу параметров только в активную подформу.
2. В modules/deck/editor/adapter.py (dto_to_slot) исключи слияние устаревших параметров предыдущего типа действия в новое действие при смене типов.
3. Прогони pytest tests/unit/test_deck_property_form*.py tests/unit/test_deck_editor_adapter.py.
```

#### Pre-Flight проверка Фазы 4:
```text
@code-review проведи аудит реализации Фазы 4:
1. Проверь чистоту словарей action_params при многократной смене типов в инспекторе.
2. Убедись в отсутствии необработанных исключений KeyError и ValidationError.
```

---

### Фаза 5. Двуязычная локализация (RU/EN), документация и чек-лист DoD

#### Шаг 5.1. Актуализация локалей (Bilingual Localization-First)
* **Файлы:** `locales/ru.json`, `locales/en.json`
* **Суть изменений:**
  1. Обеспечить 100% паритет ключей и идентичность аргументов интерполяции `{var}`:
     - `deck.editor.presets.switch_profile_wip_badge`: `" (Скоро)"` / `" (Soon)"`
     - `deck.editor.presets.macro_wip_badge`: `" (В разработке)"` / `" (In Development)"`
     - `deck.editor.tooltips.wip_feature`: `"Функция находится в разработке"` / `"Feature is under development"`
  2. Удалить устаревшие неиспользуемые ключи удаленных элементов (`create_folder`, `brightness`, `page_indicator`).
  3. Прогнать линтер локализации `pytest tests/unit/test_i18n_linter.py` (100% PASS).

#### Шаг 5.2. Актуализация тестов каталога и шторки
* **Файлы:**
  - `tests/unit/test_deck_editor_action_drawer.py`
  - `tests/unit/test_deck_editor_adapter.py`
  - `tests/unit/test_deck_presets_and_executors.py`
* **Суть изменений:**
  1. Обновить тестовые фикстуры, проверяющие согласованность категорий и пресетов в `ActionPresetsRegistry`.
  2. Проверить, что шторка `ActionLibraryDrawer` успешно ищет по RU и EN тегам.

#### Шаг 5.3. Актуализация системной документации и памяти
* **Файлы:** `.md/backend.md`, `.md/changelog.md`
* **Суть изменений:**
  1. В `.md/backend.md` обновить описание подсистемы `modules/deck` с фиксацией `ActionPresetsRegistry` как единственного каталога пресетов и матрицы маршрутизации подформ.
  2. В `.md/changelog.md` внести запись о стабилизации редактора деки, устранении коллизий хоткеев и унификации каталогов.
  3. Обновить слепки архитектуры в семантической памяти Serena (`write_memory(memory_name="architecture", ...)`).

---

#### Запуск Фазы 5:
```text
@fullstack-builder реализуй Фазу 5 из .md/deck/edit_atrib1.md:
1. Синхронизируй ключи в locales/ru.json и locales/en.json с соблюдением 100% паритета.
2. Запусти линтер локализации pytest tests/unit/test_i18n_linter.py.
3. Обнови тесты шторки и адаптера под единый каталог пресетов.
4. Обнови .md/backend.md и .md/changelog.md.
```

#### Pre-Flight проверка Фазы 5:
```text
@code-review проведи итоговый аудит релиза Фазы 5:
1. Запусти полный прогон тестов pytest tests/.
2. Проверь прохождение линтера локализации test_i18n_linter.py.
3. Проверь чистоту git diff и отсутствие хардкода строковых литералов.
```

---

## 4. Чек-лист Definition of Done (DoD)

- [ ] **1. Отсутствие циклических импортов:** `python -c "from modules.deck.presets import ActionPresetsRegistry"` выполняется мгновенно и без ошибок; тест `test_deck_presets_and_executors.py` успешно собирается.
- [ ] **2. Единый источник правды (SSOT):** `ActionPresetsRegistry` является единственным каталогом пресетов системы; `get_default_action_catalog()` возвращает идентичные данные через фасад.
- [ ] **3. Сохранение действий без отката в хоткей:** Кнопка с ранее настроенным хоткеем при выборе запуска программы, сайта или звука сохраняет выбранное действие и не откатывается в `hotkey`.
- [ ] **4. Детерминированная маршрутизация подформ:** Пресеты скриншотов открывают `ScreenshotSubform`, аудиоустройств — `AudioDeviceSubform`, саундборда — `SoundboardSubform`, веб-ссылок — `PathUrlSubform` в режиме URL. Атрибуты заготовок не теряются.
- [ ] **5. Изоляция параметров:** При переключении между подформами параметры предыдущего действия не попадают в словарь нового действия.
- [ ] **6. Чистота каталога:** `create_folder`, `brightness` и `page_indicator` полностью удалены; `switch_profile` заблокирован с пояснением в коде; `macro_sequence` помечен как WIP.
- [ ] **7. Локализация:** 100% паритет ключей в `locales/ru.json` и `locales/en.json`, отсутствие хардкода строк в UI, прохождение `test_i18n_linter.py`.
- [ ] **8. Полный тестовый прогон:** `pytest tests/` возвращает 100% PASS (все 543+ тестов зеленые).
