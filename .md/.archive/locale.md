# Движок локализации DuckDock (i18n/l10n): Техническое задание и Actionable Roadmap

> **Статус документа:** Активное техническое задание и пошаговый Actionable Roadmap  
> **Версия подсистемы:** Core Localization Engine v0.1.0  
> **Целевая среда:** Windows 10/11 x64, Desktop GUI (PySide6 / Qt6, Python 3.12+)  
> **Дисплейное окружение:** Сенсорный экран 7" (1024×600 JRP7813S iGPU) + основной монитор (27" 2560×1440 dGPU)  
> **Базовый стандарт:** `GEMINI.md` (Zero-Bespoke Invariant, Platform-First, Feature-First Modularity, Weak Coupling через EventBus, Stealth Focus Invariant)  
> **Целевой модуль в кодовой базе:** `core.i18n`, `locales/ru.json`, `locales/en.json`, `core.ui_base.TouchModuleView`  

---

## 1. Концепция и цели подсистемы локализации

Подсистема локализации DuckDock предназначена для обеспечения полноценной двуязычной поддержки интерфейса:
- **Основной (первичный) язык:** Русский (`ru`).
- **Синхронный зеркальный язык:** Английский (`en`), наполняемый параллельно со 100% паритетом ключей.
- **Архитектурный стандарт:** Иерархический точечный стандарт семантических ключей (`dot.notation`), сериализуемый в легковесные структурированные файлы JSON без внешних шагов компиляции (Zero-Build).
- **Интерактивность:** Мгновенная динамическая смена языка «на лету» (Hot-Reload) через центральную шину событий `core.event_bus.bus` без перезапуска приложения и без потери пользовательского состояния (активный медиаплеер, открытая страница колодки, запущенные сенсоры).

```mermaid
flowchart TD
    subgraph ConfigStorage [Конфигурация и Хранилище]
        ConfigFile["config.json<br/>language: 'ru' | 'en'"]
        AppCfg["AppConfig (Pydantic)"]
        ConfigFile <--> AppCfg
    end

    subgraph I18nEngine [Слой core/i18n/]
        RuJSON["locales/ru.json<br/>(100% паритет)"]
        EnJSON["locales/en.json<br/>(100% паритет)"]
        I18nMgr["I18nManager (Singleton)<br/>• Fast In-Memory Dict Cache<br/>• Dot-Notation Resolver<br/>• Pluralization Engine (RU/EN)<br/>• Fallback ru -> en -> raw_key"]
        RuJSON --> I18nMgr
        EnJSON --> I18nMgr
    end

    subgraph EventSystem [Слабосвязанная шина событий]
        Bus["core.event_bus.bus<br/>language_changed(str)"]
    end

    subgraph UIShell [Пользовательский интерфейс (1024x600)]
        BaseView["core.ui_base.TouchModuleView<br/>retranslate_ui()"]
        Sidebar["SidebarDock<br/>(Сайдбар 80x600)"]
        SettingsView["SettingsView<br/>(Селектор языка RU/EN)"]
        AudioView["AudioView (Микшер)"]
        DeckView["DeckView (Колодка)"]
        SensorsView["SensorsView (Датчики)"]
    end

    AppCfg --> I18nMgr
    SettingsView -->|set_language| I18nMgr
    I18nMgr -->|emit| Bus
    Bus --> BaseView
    BaseView --> AudioView
    BaseView --> DeckView
    BaseView --> SensorsView
    Bus --> Sidebar
    Bus --> SettingsView
```

---

## 2. Архитектурные требования и инварианты

### 2.1. Инвариант нулевой сборки и двусторонний In-Memory кэш (Zero-Build Invariant)
В отличие от тяжеловесных форматов Qt Linguist (`.ts` $\to$ `.qm`) или GNU gettext (`.po` $\to$ `.mo`), движок локализации DuckDock не должен требовать внешних утилит компиляции ни в runtime, ни при сборке тестов в CI/CD.
* Словари хранятся в кодировке **UTF-8** в директории `locales/` в корне проекта: `locales/ru.json` и `locales/en.json`.
* **In-Memory Preloaded Cache:** При инициализации `I18nManager` оба словаря (`ru` и `en`) разворачиваются (flatten) в память один раз. Переключение языка `set_language()` сводится к атомарной смене ссылки на активный словарь за $O(1)$ без дискового ввода-вывода и на 100% безопасно для фоновых потоков (например, воркеров колодки DuckDeck).
* Время первичной загрузки обоих словарей при старте процесса не превышает **5 мс**.
* Доступ к строке по ключу `t("audio.master_volume")` выполняется за время $O(1)$ благодаря плоской хэш-таблице (Flattened In-Memory Lookup Table).

### 2.2. Иерархический точечный стандарт ключей (Dot-Notation)
Все идентификаторы локализации имеют строгую семантическую структуру:
`<пространство_имен>.<подсистема_или_компонент>.<элемент_или_действие>`

*Примеры:*
* `common.actions.save` — кнопка «Сохранить»
* `sidebar.tabs.audio` — таб «Микшер» в сайдбаре
* `audio.device.mute` — статус/действие «Заглушить»
* `deck.touchbar.clock` — подпись секции часов в тачбаре
* `settings.stealth.title` — заголовок блока Stealth Focus

### 2.3. Симметричный Fallback и защита от сбоев (Graceful Degradation)
При запросе несуществующего или пропущенного ключа движок отрабатывает по строгому симметричному каскаду:
1. Поиск ключа в активном словаре (например, `ru.json` при активном русском).
2. При отсутствии: поиск ключа в резервном словаре противоположного языка (`en.json` для русского, `ru.json` для английского).
3. При отсутствии в обоих: логирование предупреждения `logger.warning(...)` и возврат самого ключа (например, `"audio.unknown_key"`), исключая аварийный краш приложения (`KeyError`).

### 2.4. Плюрализация (Множественные числа для RU и EN)
Русский язык требует 3 грамматические формы числительных, английский — 2 формы:
* **RU:**
  - `one` (1, 21, 31... устройство) $\to$ `n % 10 == 1 && n % 100 != 11`
  - `few` (2-4, 22-24... устройства) $\to$ `2 <= n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)`
  - `many` (5-20, 25-30, 0... устройств) $\to$ остальные случаи
* **EN:**
  - `one` (1 device) $\to$ `abs(n) == 1`
  - `other` (0, 2, 5... devices) $\to$ остальные случаи

В словарях плюральные ключи оформляются вложенным объектом:
```json
// RU (3 категории: one, few, many)
"devices_count": {
  "one": "{count} активное устройство",
  "few": "{count} активных устройства",
  "many": "{count} активных устройств"
}

// EN (2 категории: one, other)
"devices_count": {
  "one": "{count} active device",
  "other": "{count} active devices"
}
```
Диспетчер плюрализации выбирает точную категорию языка, а при ее отсутствии в словаре использует универсальный каскад отката: `category -> other -> many -> few -> one -> любой доступный шаблон`.

### 2.5. Инвариант Stealth Focus и аппаратные ограничения (1024×600)
1. **Отсутствие модальных диалогов:** Переключение языка через UI не должно открывать блокирующих всплывающих окон (`QMessageBox`), забирающих фокус с основного 27" монитора (сохранение `WS_EX_NOACTIVATE`).
2. **Text Expansion & Текстовая эластичность:** Русский текст длиннее английского на 20–40%. Все элементы с ограниченной геометрией (кнопки сайдбара 64×64, ячейки сетки DuckDeck, бейджи):
   - Обязаны использовать лаконичные термины.
   - Поддерживать обрезку по многоточию (`QFontMetrics.elidedText`).
   - Использовать `MarqueeLabel` для длинных названий треков и сенсоров.

---

## 3. Таксономия пространств имен словарей

Словари `locales/ru.json` и `locales/en.json` делятся на следующие функциональные разделы:

| Пространство имен | Назначение | Примеры ключей |
| :--- | :--- | :--- |
| **`common`** | Общесистемные действия, статусы и лейблы | `common.actions.save`, `common.status.loading`, `common.state.on`, `common.state.off` |
| **`sidebar`** | Кнопки сайдбара и mini media bar | `sidebar.tabs.media`, `sidebar.tabs.sensors`, `sidebar.tabs.audio`, `sidebar.tabs.deck`, `sidebar.tabs.settings` |
| **`audio`** | Аудиомикшер, ползунки, сессии и устройства | `audio.master_volume`, `audio.devices.output_empty`, `audio.sessions.system_sounds`, `audio.device.mute` |
| **`deck`** | Макро-колодка DuckDeck, сетка 2×5, тачбар, тикер | `deck.grid.page_indicator`, `deck.actions.hotkey`, `deck.touchbar.sensors`, `deck.feedback.switched` |
| **`telemetry`** | Датчики железа, графики, всплывающие подсказки | `telemetry.cpu.temp`, `telemetry.gpu.usage`, `telemetry.ram.used`, `telemetry.tooltips.sparkline` |
| **`media`** | YouTube Music плеер и управление | `media.player.prev`, `media.player.play`, `media.player.pause`, `media.player.next`, `media.status.not_playing` |
| **`settings`** | Экран настроек, дисплей, стелс-фокус, язык | `settings.title`, `settings.language.title`, `settings.language.ru`, `settings.language.en`, `settings.stealth.anti_warp` |
| **`showcase`** | Витрина модулей и системный монитор | `showcase.title`, `showcase.sections.display`, `showcase.sections.audio` |

---

## 4. Спецификация API ядра (`core.i18n`)

### 4.1. Публичный фасад `core/i18n/__init__.py`
```python
from core.i18n.manager import I18nManager, t, tp

__all__ = ["I18nManager", "t", "tp"]
```

### 4.2. Метод интерполяции `t(key: str, **kwargs) -> str`
```python
# Базовый перевод:
title = t("sidebar.tabs.audio") # -> "Микшер" (ru) / "Mixer" (en)

# Перевод с переменными:
msg = t("deck.actions.hotkey_info", keys="Ctrl+Shift+Esc") # -> "Хоткей: Ctrl+Shift+Esc"
```

### 4.3. Метод плюрализации `tp(key: str, count: int, **kwargs) -> str`
```python
# Плюральный перевод с автоматической подстановкой {count}:
status = tp("audio.devices_count", count=3) # -> "3 активных устройства" (ru) / "3 active devices" (en)
```

### 4.4. Интеграция с `TouchModuleView` в `core/ui_base.py`
```python
class TouchModuleView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)
        # Автоматическая реактивная подписка на смену языка
        bus.language_changed.connect(self._handle_language_changed)

    def _handle_language_changed(self, lang_code: str) -> None:
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Переопределяется каждым модулем для обновления текстов элементов.
        Служит единым источником правды для всех текстовых меток."""
        pass

    def cleanup(self) -> None:
        try:
            bus.language_changed.disconnect(self._handle_language_changed)
        except (RuntimeError, TypeError):
            pass

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)
```

---

## 5. Матрица ответственности (RACI)

| Участник / Роль | Фаза 0: Аудит | Фаза 1: Движок | Фаза 2: Базовый UI | Фаза 3: Настройки | Фаза 4: Миграция |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`@deep-researcher`** | **A** (Audit) | C | C | C | I |
| **`@fullstack-builder`** | **R** (Dicts) | **A** / **R** | **A** / **R** | **A** / **R** | **A** / **R** |
| **`@code-review`** | **A** (Review) | **A** (Review) | **A** (Review) | **A** (Review) | **A** (Review) |
| **`@bug-hunter`** | I | **R** (Tests) | **R** (Tests) | **R** (Tests) | **R** (TDD) |

* **R (Responsible):** Исполнитель шага  
* **A (Accountable):** Утверждающий результаты  
* **C (Consulted):** Консультант по архитектурным инвариантам  
* **I (Informed):** Информируемый участник  

---

## 6. Пошаговый Actionable Roadmap реализации

### Фаза 0: Инвентаризация строк и базовые словари (RU/EN)

- [x] **Шаг 0.1: Глубокая инвентаризация UI-строк и шаблонов**
  - [x] **Шаг 0.1.1:** Сканирование кодовой базы `ui/` и `modules/` на UI-вызовы отображения (`setText()`, `setToolTip()`, `setTitle()`, фабрики `_create_nav_button(...)`, карточки `SessionCardWidget`, тикер `NotificationMessage`, всплывающие подсказки).
  - [x] **Шаг 0.1.2:** Сепарация контента: исключение логов `logger.*`, `print()`, исключений `raise ...`, строковых констант WinAPI и метаданных Pydantic `Field(description=...)`.
  - [x] **Шаг 0.1.3:** Унификация шаблонов с динамической интерполяцией в именованные плейсхолдеры `{param}` (например, `{percent}`, `{name}`, `{page}`, `{count}`).
- [x] **Шаг 0.2: Проектирование таксономии и генерация `locales/ru.json`**
  - [x] **Шаг 0.2.1:** Иерархическая группировка по 8 пространствам имен: `common`, `sidebar`, `audio`, `deck`, `telemetry`, `media`, `settings`, `showcase`. Базовый каркас (`common`, `sidebar`, `settings`, `showcase`) наполняется сразу для запуска Фаз 1-3; секции модулей (`audio`, `deck`, `telemetry`, `media`) подготавливаются со стартовыми ключами и окончательно обогащаются в Фазе 4.
  - [x] **Шаг 0.2.2:** Формирование трехформенных объектов плюрализации для русского языка (`one`, `few`, `many`).
  - [x] **Шаг 0.2.3:** Сборка мастер-словаря в `locales/ru.json` в кодировке UTF-8 с валидацией JSON-структуры.
- [x] **Шаг 0.3: Формирование зеркального словаря `locales/en.json` (100% паритет)**
  - [x] **Шаг 0.3.1:** Синхронный английский перевод с лаконичными терминами под физические ограничения 1024×600 (сайдбар 80px, кнопки 64×64, ячейки колодки 160×110).
  - [x] **Шаг 0.3.2:** Полное совпадение контрактов именованных плейсхолдеров (`{var}`) между RU и EN.
  - [x] **Шаг 0.3.3:** Реализация двухформенных объектов плюрализации для английского языка (`one`, `other`) и сохранение в `locales/en.json`.
- [x] **Шаг 0.4: Автоматизированная валидация паритета и синтаксиса**
  - [x] **Шаг 0.4.1:** Проверка синтаксической валидности `locales/ru.json` и `locales/en.json` через `json.loads()`.
  - [x] **Шаг 0.4.2:** Проверка равенства множеств ключей (`set(ru_keys) ^ set(en_keys) == set()`).
  - [x] **Шаг 0.4.3:** Проверка консистентности наборов плейсхолдеров (`{var}`) для каждого ключа между языками.

#### Маппинг пространств имен по модулям кодовой базы:

| Файл кодовой базы | Тип UI-элементов | Пространство имен | Примеры ключей |
| :--- | :--- | :--- | :--- |
| `ui/sidebar.py` | Тултипы табов, кнопка Stealth Lock | `sidebar` | `sidebar.tabs.media`, `sidebar.tabs.deck`, `sidebar.lock.enabled` |
| `modules/audio/view.py` | Заголовки, кнопки Mute/Refresh, устройства | `audio`, `common` | `audio.master.title`, `audio.devices.headphones`, `common.actions.refresh` |
| `modules/deck/view.py` | Статусы свайпа, тикер, страницы | `deck` | `deck.page.switched`, `deck.page.not_found`, `deck.status.ready` |
| `modules/deck/action_dispatcher.py` | Уведомления о выполнении команд | `deck` | `deck.notify.mic_muted`, `deck.notify.pc_locked`, `deck.notify.audio_switched` |
| `modules/telemetry/view.py` | Заголовки графиков, карточки сенсоров | `telemetry` | `telemetry.cpu.temp`, `telemetry.gpu.usage`, `telemetry.ram.used` |
| `modules/media/view.py` | Кнопки входа, подсказки плеера | `media` | `media.auth.login`, `media.auth.hint`, `media.player.volume` |
| `modules/settings/view.py` | Заголовки групп настроек, тумблеры | `settings`, `common` | `settings.display.title`, `settings.stealth.delay`, `common.state.enabled` |
| `ui/showcase_view.py` | Диагностика хуков, диммер | `showcase` | `showcase.title`, `showcase.dimmer.off_btn`, `showcase.dimmer.active` |

#### Запуск Фазы 0 (Инвентаризация и мастер-словари):
```text
@fullstack-builder выполни реализацию Фазы 0 по шагам 0.1-0.4:
1. Проведи инвентаризацию UI-строк в ui/ и modules/, исключив логирование (logger.*) и метаданные Pydantic.
2. Сформируй мастер-словарь locales/ru.json со структурированными пространствами имен (common, sidebar, audio, deck, telemetry, media, settings, showcase) и блоками плюрализации (one/few/many).
3. Сформируй зеркальный словарь locales/en.json со 100% паритетом ключей и идентичными плейсхолдерами ({var}).
4. Напиши проверочный скрипт/тест на валидацию JSON, сверку множеств ключей (diff == 0) и валидацию плейсхолдеров.
Критерий приемки: Валидные locales/ru.json и locales/en.json со 100% совпадением ключей; pytest tests/ проходит со 100% PASS (181 существующий тест не затронут).
```

#### Pre-Flight проверка Фазы 0:
```text
@code-review проведи аудит результатов Фазы 0:
1. Проверь отсутствие технических логов и исключений в JSON-словарях.
2. Проверь лаконичность русских переводов для экранов с жесткой геометрией (80x600 сайдбар, 160x110 кнопки DuckDeck).
3. Подтверди 100% паритет ключей и идентичность именованных параметров ({var}).
```

---

### Фаза 1: Фундамент движка `core/i18n` и валидация

- [x] **Шаг 1.1: Процессор плюрализации (`core/i18n/plural.py`)**
  - [x] **Шаг 1.1.1:** Реализовать алгоритм русской плюрализации `get_plural_category_ru(count: int | float) -> str` с тремя категориями:
    - `one`: `n % 10 == 1 and n % 100 != 11` (1, 21, 31, 101 устройство);
    - `few`: `2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14)` (2, 3, 4, 22, 104 устройства);
    - `many`: все остальные случаи (0, 5–20, 25–30, 111–114 устройств).
  - [x] **Шаг 1.1.2:** Реализовать алгоритм английской плюрализации `get_plural_category_en(count: int | float) -> str` с двумя категориями:
    - `one`: `abs(int(count)) == 1` (1 device);
    - `other`: все остальные случаи (0, 2, 5 devices).
  - [x] **Шаг 1.1.3:** Реализовать единый фасад-диспетчер `resolve_plural_category(lang: str, count: int | float) -> str` с валидацией и приведением отрицательных/дробных чисел через `abs(int(count))`.

- [x] **Шаг 1.2: Менеджер локализации (`core/i18n/manager.py`)**
  - [x] **Шаг 1.2.1: Архитектура Singleton и инициализация каталогов:**
    - Реализовать класс `I18nManager` (Singleton) с потокобезопасным созданием экземпляра.
    - Обеспечить настраиваемый путь к каталогу словарей `locales_dir: Optional[Path] = None` (по умолчанию `root/locales`) для изолированного модульного тестирования.
  - [x] **Шаг 1.2.2: Двусторонний предзагруженный кэш (_flatten_dict и In-Memory Preload):**
    - Преобразование вложенных структур JSON в плоскую хэш-таблицу dot-notation при предзагрузке для достижения времени поиска $O(1)$ и старта $< 5$ мс.
    - Одновременная предзагрузка обоих словарей в память (`self._catalogs = {"ru": ..., "en": ...}`).
    - Конечные объекты плюрализации (`{"one": "...", "few": "...", "many": "..."}` для RU и `{"one": "...", "other": "..."}` для EN) сохраняются в плоском словаре как единый `dict` под составным ключом родителя.
  - [x] **Шаг 1.2.3: Безопасный форматтер (SafeFormatter):**
    - Реализовать `SafeFormatter(string.Formatter)`, предотвращающий фатальные падения (`KeyError`, `IndexError`) при вызове `t()` с неполным набором аргументов (непереданные плейсхолдеры остаются в виде `{param}`).
  - [x] **Шаг 1.2.4: Публичные функции перевода `t()` и `tp()`:**
    - `t(key: str, **kwargs) -> str`: поиск в активном словаре $\to$ симметричный fallback на резервный язык (ru $\leftrightarrow$ en) $\to$ возврат `raw_key` с `logger.warning` при отсутствии $\to$ безопасная интерполяция через `SafeFormatter`.
    - `tp(key: str, count: int, **kwargs) -> str`: вычисление категории числа через `resolve_plural_category(lang, count)` $\to$ выбор шаблона с универсальным каскадом (`cat` $\to$ `other` $\to$ `many` $\to$ `few` $\to$ `one`) $\to$ автоматическая подстановка `{count}`.
  - [x] **Шаг 1.2.5: Метод переключения языка `set_language()`:**
    - Валидация входного кода локали (`lang_code in ("ru", "en")`, при ошибке `ValueError`).
    - Идемпотентность: пропуск повторного переключения, если язык уже активен.
    - Атомарная смена ссылки на активный словарь `self._active_catalog = self._catalogs[lang_code]` (время выполнения $O(1)$, потокобезопасно для воркеров без блокировок).
    - Эмиссия сигнала `core.event_bus.bus.language_changed.emit(lang_code)` при `emit_signal=True`.

- [x] **Шаг 1.3: Публичный фасад ядра (`core/i18n/__init__.py`)**
  - [x] **Шаг 1.3.1:** Экспорт `I18nManager`, функций быстрого доступа `t`, `tp` и вспомогательной функции `resolve_plural_category`.
  - [x] **Шаг 1.3.2:** Проверка чистоты импортов: `core.i18n` не содержит ссылок на `modules` или `ui` (строгое соблюдение The Dependency Rule).

- [x] **Шаг 1.4: Регистрация сигнала в шине событий (`core/event_bus.py`)**
  - [x] **Шаг 1.4.1:** Добавить строго типизированный сигнал `language_changed = Signal(str)` в класс `EventBus`.
  - [x] **Шаг 1.4.2:** Проверить обратную совместимость: интерфейс шины не ломает существующие подписки.

- [x] **Шаг 1.5: Интеграция конфигурации (`modules/settings/config.py` и `config.json`)**
  - [x] **Шаг 1.5.1:** Добавить типизированное поле `language: Literal["ru", "en"] = Field(default="ru", description="Язык интерфейса ('ru' | 'en')")` в модель `AppConfig`.
  - [x] **Шаг 1.5.2:** Добавить значение `"language": "ru"` в корневой файл конфигурации `config.json`.
  - [x] **Шаг 1.5.3:** Обновить функцию `load_config()` для безопасной загрузки с дефолтным откатом при повреждении поля.

- [x] **Шаг 1.6: Пакет модульных тестов ядра (`tests/unit/test_i18n.py`)**
  - [x] **Шаг 1.6.1:** `test_i18n_singleton`: валидация паттерна Singleton и состояния инстанса.
  - [x] **Шаг 1.6.2:** `test_i18n_flattening_and_lookup`: развертывание вложенных JSON и скорость $O(1)$.
  - [x] **Шаг 1.6.3:** `test_i18n_safe_formatter`: устойчивость к неполным аргументам форматирования без `KeyError`.
  - [x] **Шаг 1.6.4:** `test_i18n_pluralization_ru`: детальная проверка чисел 1, 2, 4, 5, 11-14, 21, 24, 112 на корректную форму (`one`/`few`/`many`).
  - [x] **Шаг 1.6.5:** `test_i18n_pluralization_en`: проверка чисел 1, 0, 2, 100 на формы `one` и `other`.
  - [x] **Шаг 1.6.6:** `test_i18n_fallback_cascade`: возврат английского перевода при пропуске ключа в русском словаре и возврат `raw_key` при отсутствии в обоих.
  - [x] **Шаг 1.6.7:** `test_i18n_set_language_signals`: валидация эмиссии `bus.language_changed` при смене языка.
  - [x] **Шаг 1.6.8:** `test_i18n_parity_guard`: проверка 100% паритета ключей между `locales/ru.json` и `locales/en.json` (`set(ru) ^ set(en) == set()`).
  - [x] **Шаг 1.6.9:** `test_app_config_language_validation`: отклонение невалидных локалей в Pydantic (`ValidationError`).

#### Запуск Фазы 1:
```text
@fullstack-builder реализуй Фазу 1 (Фундамент движка core/i18n) по шагам 1.1-1.6 из .md/locale.md:
1. Создай core/i18n/plural.py с категориями RU (one/few/many) и EN (one/other).
2. Создай core/i18n/manager.py: Singleton I18nManager, _flatten_dict, SafeFormatter, функции t() и tp(), fallback-каскад и set_language().
3. Оформи фасад core/i18n/__init__.py.
4. Добавь сигнал language_changed = Signal(str) в core/event_bus.py.
5. Добавь language: Literal["ru", "en"] = Field(default="ru") в AppConfig в modules/settings/config.py и обнови config.json.
6. Напиши исчерпывающие тесты tests/unit/test_i18n.py (плюрализация, интерполяция, fallback, dot-notation, сигналы, валидация конфигурации).
Критерий приемки: pytest tests/unit/test_i18n.py выполняется со 100% PASS; общий регрессионный прогон pytest tests/ подтверждает 100% PASS (все 181+ тестов зеленые).
```

#### Pre-Flight проверка Фазы 1:
```text
@code-review проведи аудит реализации Фазы 1 (Фундамент core/i18n):
1. Проверь строгое соблюдение The Dependency Rule: core.i18n не должен импортировать модули из modules/ или ui/.
2. Проверь безопасность форматирования: отсутствие риска необработанных исключений KeyError/IndexError при вызове t() с неполными аргументами.
3. Проверь корректность алгоритмов плюрализации для чисел 11-14 в русском языке.
4. Подтверди отсутствие регрессий в существующих 181 тестах.
```

---

### Фаза 2: Интеграция в базовый UI-каркас и горячее переключение

- [x] **Шаг 2.1: Реактивный базовый класс `TouchModuleView` (`core/ui_base.py`)**
  - [x] **Шаг 2.1.1:** Добавить автоматическую подписку `bus.language_changed.connect(self._handle_language_changed)` в `TouchModuleView.__init__`.
  - [x] **Шаг 2.1.2:** Исключить вызов `self.retranslate_ui()` из конструктора `TouchModuleView.__init__` для предотвращения `AttributeError` у еще не созданных дочерних виджетов (Initialization Invariant). Закрепить стандарт: наследники создают виджеты в `_init_ui()` и в конце вызывают `self.retranslate_ui()`, делая его единственным источником правды для текстов.
  - [x] **Шаг 2.1.3:** Реализовать виртуальный метод `retranslate_ui(self) -> None`, переопределяемый дочерними модулями.
  - [x] **Шаг 2.1.4:** Предотвратить утечки памяти и сбои C++ объектов: реализовать отписку в методе `cleanup()` и вызов `cleanup()` в `closeEvent()`, с безопасным подавлением ошибок `try...except (RuntimeError, TypeError): pass` (исключая нестабильный хук на `self.destroyed`).

- [x] **Шаг 2.2: Локализация сайдбара и сквозных виджетов (`ui/sidebar.py`)**
  - [x] **Шаг 2.2.1:** Интегрировать подписку на `bus.language_changed` в `SidebarDock` и реализовать метод `retranslate_ui()`.
  - [x] **Шаг 2.2.2:** Обновить подсказки кнопок навигации без изменения геометрии сайдбара (фиксированная ширина 80px):
    - `btn_yt.setToolTip(t("sidebar.tabs.media"))`
    - `btn_sensors.setToolTip(t("sidebar.tabs.sensors"))`
    - `btn_deck.setToolTip(t("sidebar.tabs.deck"))`
    - `btn_audio.setToolTip(t("sidebar.tabs.audio"))`
    - `btn_showcase.setToolTip(t("sidebar.tabs.showcase"))`
  - [x] **Шаг 2.2.3:** Реализовать динамическую подсказку кнопки блокировки ввода `btn_lock` в зависимости от состояния `self._input_locked` (`sidebar.lock.input_mode` / `sidebar.lock.stealth_mode`).
  - [x] **Шаг 2.2.4:** Интегрировать `retranslate_ui()` в `MiniMediaBar` (`modules/media/widgets/mini_media_bar.py`): локализация подсказок кнопок воспроизведения `btn_prev`, `btn_play`, `btn_next` и статуса отсутствия трека.
  - [x] **Шаг 2.2.5:** Обеспечить безопасную отписку от `bus.language_changed` при разрушении сайдбара в `_on_destroyed()`.

- [x] **Шаг 2.3: Интеграция в главное окно приложения (`ui/main_window.py`)**
  - [x] **Шаг 2.3.1:** При холодном старте в `MainWindow.__init__` инициализировать язык интерфейса вызовом `I18nManager().set_language(self.config.language, emit_signal=False)` без паразитных сигналов перерисовки.
  - [x] **Шаг 2.3.2:** Выполнить первичный вызов `self.sidebar.retranslate_ui()` после построения дерева виджетов в `_init_ui()`.
  - [x] **Шаг 2.3.3:** Обеспечить обновление заголовка окна при смене языка через `setWindowTitle(f"DuckDock - {t('common.app_subtitle')}")`.

- [x] **Шаг 2.4: Набор модульных тестов UI-реактивности (`tests/unit/test_i18n_ui.py`)**
  - [x] **Шаг 2.4.1:** `test_touch_module_view_auto_subscription`: валидация вызова `retranslate_ui()` у наследников при сигнале `language_changed`.
  - [x] **Шаг 2.4.2:** `test_touch_module_view_cleanup_prevents_leaks`: проверка гарантированного разрыва подписки при вызове `cleanup()` и разрушении виджета.
  - [x] **Шаг 2.4.3:** `test_sidebar_tooltips_retranslation`: проверка мгновенной смены подсказок кнопок сайдбара при переключении RU $\leftrightarrow$ EN без изменения размеров элементов.
  - [x] **Шаг 2.4.4:** `test_sidebar_lock_button_tooltip_states`: валидация подсказки кнопки блокировки ввода в обоих режимах на обоих языках.
  - [x] **Шаг 2.4.5:** `test_main_window_language_initialization`: проверка применения `config.language` при создании главного окна без паразитных сигналов.

#### Запуск Фазы 2:
```text
@fullstack-builder интегрируй локализацию в UI-каркас (Фаза 2 из .md/locale.md) по шагам 2.1-2.4:
1. Обнови core/ui_base.py: добавь в TouchModuleView подписку на bus.language_changed, метод retranslate_ui() и безопасную отписку в cleanup() / destroyed.
2. Обнови ui/sidebar.py: реализуй retranslate_ui() для SidebarDock, обнови подсказки кнопок навигации и кнопки lock через t("sidebar.tabs.*") и t("sidebar.lock.*").
3. Обнови modules/media/widgets/mini_media_bar.py: добавь метод retranslate_ui() с подсказками кнопок плеера.
4. Обнови ui/main_window.py: инициализируй I18nManager().set_language(self.config.language, emit_signal=False) при старте и вызови первичный retranslate_ui() сайдбара.
5. Напиши комплексные тесты tests/unit/test_i18n_ui.py (автоподписка TouchModuleView, корректность отписки в cleanup, динамическое обновление тултипов сайдбара).
Критерий приемки: pytest tests/unit/test_i18n_ui.py выполняется со 100% PASS; общий регрессионный прогон pytest tests/ подтверждает 100% PASS (все существующие 181+ тестов зеленые).
```

#### Pre-Flight проверка Фазы 2:
```text
@code-review проведи аудит реализации Фазы 2 (Интеграция в базовый UI-каркас):
1. Проверь отсутствие утечек памяти: подтверди, что TouchModuleView и SidebarDock корректно отписываются от шины bus.language_changed при разрушении виджета.
2. Проверь соблюдение инварианта Stealth Focus: подтверди, что вызовы retranslate_ui() не перехватывают фокус (сохранен Qt.NoFocus).
3. Проверь целостность геометрии: подтверди, что ширина сайдбара остается строго 80px, а Text Expansion не деформирует кнопки.
4. Подтверди отсутствие циклических импортов между core.ui_base, core.event_bus и ui.sidebar.
```

---

### Фаза 3: Сенсорный селектор языка в модуле настроек

- [x] **Шаг 3.1: Контракт сохранения конфигурации (`modules/settings/config.py`)**
  - [x] **Шаг 3.1.1:** Реализовать функцию безопасной атомарной записи `save_config(config: AppConfig, config_path: Optional[Path | str] = None) -> bool` с записью во временный `.tmp` файл и заменой (`replace`), предотвращая повреждение при сбоях.
  - [x] **Шаг 3.1.2:** Обеспечить разрешение пути сохранения с поддержкой скомпилированного режима `sys.frozen` / `_MEIPASS` и дефолтного `config.json` в корне проекта.
  - [x] **Шаг 3.1.3:** Экспортировать `save_config` в публичный интерфейс модуля `modules/settings/__init__.py`.

- [x] **Шаг 3.2: Сенсорная карточка выбора языка (`modules/settings/view.py`)**
  - [x] **Шаг 3.2.1:** Создать карточку `_create_language_card()` со стилем `settings-card` и разместить в сетке `grid.addWidget(card_language, 2, 0, 1, 2)`.
  - [x] **Шаг 3.2.2:** Создать две сенсорные кнопки выбора: `btn_lang_ru` («Русский») и `btn_lang_en` («English») с классом `settings-lang-btn`.
  - [x] **Шаг 3.2.3:** Обеспечить инвариант Stealth Focus: принудительно задать `setFocusPolicy(Qt.NoFocus)` для обеих кнопок.
  - [x] **Шаг 3.2.4:** Задать сенсорные габариты кнопок (минимальная высота 44px, отступы под палец) и подсветку активного состояния `[active="true"]` цветом `#2563eb` в `SETTINGS_QSS`.

- [x] **Шаг 3.3: Обработчик клика и синхронизация состояния (`modules/settings/view.py`)**
  - [x] **Шаг 3.3.1:** Реализовать метод `_on_language_selected(lang_code: str)` с проверкой на идемпотентность (no-op при повторном клике).
  - [x] **Шаг 3.3.2:** Связать клик с сохранением `self.config.language = lang_code` на диск через `save_config(self.config, self.config_path)`.
  - [x] **Шаг 3.3.3:** Вызвать `I18nManager().set_language(lang_code, emit_signal=True)` для оповещения всех модулей через `bus.language_changed`.
  - [x] **Шаг 3.3.4:** Реализовать метод `_update_language_buttons()`, обновляющий свойства `active="true"/"false"` и вызывающий `unpolish`/`polish` стилей.

- [x] **Шаг 3.4: Прямая трансляция и метод `retranslate_ui()` (`modules/settings/view.py`)**
  - [x] **Шаг 3.4.1:** Исключить промежуточные громоздкие реестры кортежей `(widget, key)` в пользу прямого, чистого метода `retranslate_ui()`.
  - [x] **Шаг 3.4.2:** Сохранить ссылки на ключевые метки заголовков и карточек в атрибутах класса (`self.lbl_title`, `self.lbl_display_header`, `self.lbl_stealth_header` и др.).
  - [x] **Шаг 3.4.3:** Реализовать метод `retranslate_ui()`: прямое обновление текстов заголовков через `t("settings.*")` и вызов `_update_ui_values()` для динамических значений.
  - [x] **Шаг 3.4.4:** Обновить метод `_update_ui_values()`: заменить строковые литералы статусов и единиц измерения на вызовы `t("common.state.enabled")`, `t("common.state.disabled")`, `t("common.units.*")`.

- [x] **Шаг 3.5: Модульные тесты селектора языка (`tests/unit/test_settings_language.py`)**
  - [x] **Шаг 3.5.1:** `test_settings_view_language_buttons_render_and_focus`: проверка отображения кнопок и наличия флага `Qt.NoFocus`.
  - [x] **Шаг 3.5.2:** `test_settings_view_initial_active_state`: проверка подсветки кнопки текущего языка из `AppConfig`.
  - [x] **Шаг 3.5.3:** `test_language_switch_saves_config`: проверка записи изменений в `config.json` на диске.
  - [x] **Шаг 3.5.4:** `test_language_switch_emits_eventbus_signal`: проверка эмиссии сигнала `bus.language_changed`.
  - [x] **Шаг 3.5.5:** `test_settings_view_retranslate_ui_full_update`: проверка обновления заголовков и параметров на обоих языках.
  - [x] **Шаг 3.5.6:** `test_language_switch_idempotency`: проверка отсутствия повторных записей на диск при клике по активной кнопке.

#### Запуск Фазы 3:
```text
@fullstack-builder реализуй сенсорный селектор языка в настройках (Фаза 3 из .md/locale.md) по шагам 3.1-3.5:
1. В modules/settings/config.py реализуй функцию save_config(config, config_path) с атомарной записью.
2. В modules/settings/view.py добавь сенсорную карточку языка с кнопками [ Русский | English ] (Qt.NoFocus, min-height 44px).
3. Реализуй прямой метод retranslate_ui() для всех карточек и статусов без создания избыточных списков-реестров.
4. Свяжи выбор языка с вызовом save_config(), I18nManager().set_language() и обновлением активных стилей.
5. Напиши полный сьют тестов tests/unit/test_settings_language.py (рендеринг, NoFocus, сохранение в JSON, сигналы шины, retranslate_ui, идемпотентность).
Критерий приемки: pytest tests/unit/test_settings_language.py проходит со 100% PASS; полный регрессионный сьют pytest tests/ подтверждает 100% PASS.
```

#### Pre-Flight проверка Фазы 3:
```text
@code-review проведи аудит реализации Фазы 3:
1. Проверь инвариант Stealth Focus: подтверди, что все новые кнопки имеют Qt.NoFocus и не перехватывают системный фокус.
2. Проверь надежность файловых операций: атомарность save_config() и корректное закрытие дескрипторов.
3. Проверь отсутствие хардкода: отсутствие кириллических строк в _update_ui_values() вне вызовов t().
4. Подтверди отсутствие регрессий во всех 181+ существующих тестах.
```

---

### Фаза 4: Помодульная миграция экранов и верификация (Batch Migration)

#### Шаг 4.1: Модуль звука (`modules/audio`)
- [x] **Шаг 4.1.1: Вынос строк и контракты словарей (`locales/*.json`)**
  - Добавить ключи заголовков: `audio.header.title`, `audio.master.section_title`, `audio.sessions.section_title`.
  - Добавить ключи действий: `audio.actions.refresh`, `audio.device.default_output`, `audio.master.mute_active`, `audio.master.mute_inactive`.
  - Добавить блок плюрализации аудиосессий `audio.sessions.count`:
    - RU: `"one": "{count} активный процесс"`, `"few": "{count} активных процесса"`, `"many": "{count} активных процессов"`.
    - EN: `"one": "{count} active process"`, `"other": "{count} active processes"`.
- [x] **Шаг 4.1.2: Рефакторинг `AudioMixerView` (`modules/audio/view.py`)**
  - Заменить жестко закодированные строки в `_init_ui()`, `_refresh_master()`, `_format_device_button_text()`.
  - Реализовать метод `retranslate_ui()`:
    - Обновление текстовых меток `lbl_title`, `lbl_m_title`, `lbl_apps`, кнопки `btn_refresh`.
    - Переформатирование надписи кнопки аудиовыхода `btn_switch_device` через `_format_device_button_text()`.
    - Обновление текста и QSS-состояния мастер-кнопки `btn_master_mute`.
    - Каскадный вызов `card.retranslate_ui()` для всех существующих карточек сессий `_session_cards.values()`.
- [x] **Шаг 4.1.3: Модульные тесты аудио (`tests/unit/test_audio_i18n.py`)**
  - `test_audio_view_retranslate_ui`: проверка смены текстов заголовков и кнопок без сброса позиции слайдеров.
  - `test_audio_sessions_pluralization`: валидация плюральных форм числа сессий (1, 2, 5, 21).

#### Шаг 4.2: Модуль DuckDeck (`modules/deck`)
- [x] **Шаг 4.2.1: Вынос уведомлений диспетчера (`modules/deck/action_dispatcher.py`)**
  - Заменить строковые литералы на вызовы `t()` в фоновом воркере `ActionTask.run()`:
    - `deck.notify.hotkey_success` (`keys`), `deck.notify.hotkey_error`
    - `deck.notify.mic_muted`, `deck.notify.mic_unmuted`
    - `deck.notify.audio_muted`, `deck.notify.audio_unmuted`
    - `deck.notify.pc_locked`, `deck.notify.dimmer_toggled`
    - `deck.notify.page_navigated` (`page`), `deck.notify.unknown_cmd` (`cmd`), `deck.notify.generic_error` (`error`)
- [x] **Шаг 4.2.2: Локализация интерактивной панели (`modules/deck/widgets/interactive_panel.py`)**
  - В `DeckLeftSection`: локализовать статус ожидания плеера `deck.interactive.media_waiting`.
  - В `DeckRightSection`: локализовать статус тикера по умолчанию `deck.interactive.ready` и нотификацию шестеренки `deck.interactive.settings_in_dev`.
  - В `DeckCenterSection`: внедрить двуязычное форматирование даты (дни недели и месяцы) при тике часов с использованием `QLocale` или словарных массивов `common.calendar.*` (без небезопасного изменения глобальной C-локали `locale.setlocale`).
  - Реализовать метод `retranslate_ui()` в `DeckInteractivePanel` с каскадным обновлением всех трех секций.
- [x] **Шаг 4.2.3: Интеграция в `DeckView` (`modules/deck/view.py`)**
  - Реализовать `DeckView.retranslate_ui()`, вызывающий `interactive_panel.retranslate_ui()` и обновляющий тултипы/подписи навигации `header_bar`.
- [x] **Шаг 4.2.4: Модульные тесты колоды (`tests/unit/test_deck_i18n.py`)**
  - `test_deck_interactive_panel_retranslate`: проверка смены подписей тикера и медиа-пульса.
  - `test_deck_action_dispatcher_localized_messages`: валидация возврата локализованных сообщений по шине сигналов.

#### Шаг 4.3: NOC-дашборд телеметрии (`modules/telemetry`)
- [x] **Шаг 4.3.1: Вынос строк и контракты словарей (`locales/*.json`)**
  - Шапка: `telemetry.header.lhm_active`, `telemetry.header.lhm_fallback`, `telemetry.header.uac_admin`, `telemetry.header.uac_user`, `telemetry.header.uptime`.
  - Секции: `telemetry.cards.cpu_master`, `telemetry.cards.gpu_master`, `telemetry.cards.ram`, `telemetry.cards.network`, `telemetry.cards.storage`, `telemetry.cards.chassis`.
  - Метки чипов: `telemetry.labels.load`, `telemetry.labels.clock`, `telemetry.labels.cooler`, `telemetry.labels.pump`, `telemetry.labels.hotspot`, `telemetry.labels.vram`, `telemetry.labels.down`, `telemetry.labels.up`, `telemetry.labels.ping`.
- [x] **Шаг 4.3.2: Реализация `SensorsView.retranslate_ui()` (`modules/telemetry/view.py`)**
  - Обновить статические текстовые метки карточек и сетки чипов метрик.
  - Сохранить непрерывность работы `TelemetryWorker` и историю `TelemetryHistory` без перезапуска фонового потока.
- [x] **Шаг 4.3.3: Модульные тесты телеметрии (`tests/unit/test_telemetry_i18n.py`)**
  - `test_sensors_view_retranslate_ui`: проверка обновления заголовков и чипов без прерывания потока спарклайнов.

#### Шаг 4.4: Мультимедиа плеер (`modules/media`)
- [x] **Шаг 4.4.1: Вынос строк веб-контейнера и fallback-плеера**
  - Добавить ключи: `media.player.reload_tooltip`, `media.fallback.title`, `media.fallback.subtitle`, `media.fallback.volume_label`.
- [x] **Шаг 4.4.2: Реализация `YouTubeView.retranslate_ui()` (`modules/media/view.py`)**
  - Обновить подсказку кнопки перезагрузки `btn_reload.setToolTip(t("media.player.reload_tooltip"))`.
  - Обновить метки `lbl_fallback_title`, `sub_info`, `lbl_vol` в fallback-плеере.
- [x] **Шаг 4.4.3: Модульные тесты медиа (`tests/unit/test_media_i18n.py`)**
  - `test_youtube_view_retranslate_ui`: проверка смены тултипов и подписей fallback-плеера.

#### Шаг 4.5: Рефакторинг и локализация витрины диагностики (`ui/showcase_view.py`)
- [x] **Шаг 4.5.1: Приведение к инварианту №4 (Переход на `TouchModuleView`)**
  - Изменить объявление класса: `class ShowcaseView(TouchModuleView):`.
  - Исключить ручную подписку на `bus.language_changed` (наследуется автоматически из базового класса).
- [x] **Шаг 4.5.2: Вынос строк и реестр карточек диагностики**
  - Добавить ключи: `showcase.title`, `showcase.cards.display`, `showcase.cards.stealth`, `showcase.cards.integration`.
  - Добавить ключи параметров: `showcase.display.*`, `showcase.stealth.*`, `showcase.integration.*`, `showcase.dimmer.*`.
  - Реализовать метод `retranslate_ui()`: циклическое обновление заголовков, меток диагностических параметров и динамической кнопки диммера (`btn_test_dimmer`).
- [x] **Шаг 4.5.3: Модульные тесты витрины (`tests/unit/test_showcase_i18n.py`)**
  - `test_showcase_view_stealth_focus_and_touch_module_view`: проверка наследования от `TouchModuleView` и `Qt.NoFocus`.
  - `test_showcase_view_retranslate_ui`: проверка обновления диагностических карточек при горячей смене языка.

#### Шаг 4.6: Автоматизированный аудит чистоты строк и сквозная верификация
- [x] **Шаг 4.6.1: Тест линтера чистоты строк (`tests/unit/test_i18n_completeness.py`)**
  - Проверка 100% паритета ключей между `locales/ru.json` и `locales/en.json` (`diff == 0`).
  - Проверка консистентности именованных параметров интерполяции `{...}` между обоими словарями.
  - AST/Regex сканирование исходных кодов `ui/` и `modules/`: подтверждение отсутствия прямых кириллических строковых литералов в вызовах методов отображения (`setText`, `setToolTip`, `setTitle`) вне словарей `locales/`.
- [x] **Шаг 4.6.2: Интеграционный тест сквозного переключения (`tests/integration/test_i18n_hot_reload.py`)**
  - Инициализация `MainWindow` $\to$ переключение языка `ru` $\to$ `en` $\to$ `ru`.
  - Проверка одновременного обновления текстов во всех вкладках (Audio, Deck, Sensors, YouTube, Settings, Showcase).
  - Проверка сохранения фокуса и отсутствия утечек памяти.
- [x] **Шаг 4.6.3: Полный регрессионный прогон**
  - Выполнение `pytest tests/` со 100% статусом `PASS` (все 181+ существующих тестов + новые тесты Фазы 4).

---

#### Запуск Фазы 4 (Помодульная миграция экранов):
```text
@fullstack-builder выполни сквозную помодульную миграцию экранов (Фаза 4 из .md/locale.md) по шагам 4.1-4.6:
1. Модуль Audio: переведи AudioMixerView и SessionCardWidget на t() и tp(), реализуй retranslate_ui(), напиши tests/unit/test_audio_i18n.py.
2. Модуль Deck: локализуй сообщения DeckActionDispatcher, интерактивную панель DeckInteractivePanel и DeckView, напиши tests/unit/test_deck_i18n.py.
3. Модуль Telemetry: переведи SensorsView на t(), реализуй retranslate_ui() без перезапуска воркера, напиши tests/unit/test_telemetry_i18n.py.
4. Модуль Media: локализуй YouTubeView и fallback-плеер, напиши tests/unit/test_media_i18n.py.
5. Модуль Showcase: переведи ShowcaseView на наследование от TouchModuleView, реализуй retranslate_ui(), напиши tests/unit/test_showcase_i18n.py.
6. Верификация: создай линтер tests/unit/test_i18n_completeness.py и интеграционный тест tests/integration/test_i18n_hot_reload.py.
Критерий приемки: pytest tests/ выполняется со 100% PASS; горячая смена языка в настройках на лету обновляет все экраны интерфейса.
```

#### Pre-Flight проверка Фазы 4:
```text
@code-review проведи аудит реализации Фазы 4:
1. Проверь строгое соблюдение Stealth Focus: все новые и обновленные виджеты обязаны сохранять Qt.NoFocus.
2. Проверь инвариант UI TouchModuleView: подтверди, что ShowcaseView теперь унаследован от TouchModuleView.
3. Проверь чистоту diff: отсутствие прямого хардкода кириллических строк в UI коде вне файлов locales/.
4. Проверь 100% паритет ключей словарей ru.json и en.json.
5. Подтверди отсутствие регрессий во всех 181+ тестах кодовой базы.
```

---

## 7. Чек-лист Definition of Done для подсистемы локализации

- [x] Файлы `locales/ru.json` и `locales/en.json` содержат идентичный набор ключей (100% паритет, проверено тестом).
- [x] Движок `core/i18n` не имеет циклических зависимостей и изолирован в слое Foundation.
- [x] Горячая смена языка в настройках мгновенно переводит все вкладки без перезапуска приложения и без потери фокуса активного окна на основном мониторе.
- [x] Все тесты `pytest tests/` имеют статус `PASS` (181+ тестов).
- [x] Обновлены спецификации в `.md/backend.md` и сделана запись в `.md/changelog.md`.
