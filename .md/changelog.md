# Changelog: DuckDock / TouchWM

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.8] - 2026-11-24

### Added
- **Контекстное меню кнопок в редакторе DuckDeck (`EditorGridCell`)**:
  - Вызов по нажатию правой кнопки мыши (ПКМ) или клавише вызова меню на любой из 10 ячеек сетки.
  - Автоматическая подсветка и фокусировка ячейки в `KeyPropertyInspector` при клике ПКМ.
  - Действие «Удалить» (`deck.editor.canvas.context_menu.delete`) для быстрой очистки данных кнопки со слота.
  - Заготовки под будущие операции: «Копировать» (`copy`), «Вырезать» (`cut`), «Вставить» (`paste`), «Дублировать» (`duplicate`) в состоянии `disabled`.
  - Стилизация меню в соответствии с дизайн-системой Dark Obsidian v2 (`SURFACE_1_PANEL`, неоновый фокус, скругление 8px, разделители).
  - 100% двуязычная локализация RU/EN (`deck.editor.canvas.context_menu.*`) с паритетом ключей.

### Fixed
- **Сквозная интеграция очистки слота холста (`ClearSlotCommand` в UndoStack)**:
  - В `EditorGridCell` реализован сигнал `clear_requested(slot_index)`.
  - В `DeckCanvasWidget` добавлен сигнал `slot_clear_requested(slot_index)`.
  - В `DeckEditorWindow` сигнал подключен к обработчику `_on_inspector_slot_cleared`, активирующему команду `ClearSlotCommand` в `_undo_stack`. Очистка слота поддерживает отмену по Ctrl+Z (Undo) и повтор по Ctrl+Y (Redo), сбрасывая инспектор к плейсхолдеру и синхронизируя модель `ButtonSlotDTO`.
- **Автоматическое тестирование**:
  - Написаны модульные и интеграционные тесты для контекстного меню ячейки, сигналов очистки и отмены Undo: 543 теста со статусом **100% PASS** (543 passed, 0 failed, 29 warnings).

## [0.5.7] - 2026-11-23

### Added
- **Предустановки URL и приложений в реестре (`ActionPresetsRegistry`)**:
  - Карточка `open_url` (`id="open_url"`, иконка 🔗, `target="https://"`, тип действия `launch` с `kind="url"`).
  - Карточка `launch_app` (`id="launch_app"`, иконка 🚀, тип действия `launch` с `kind="app"`).
  - Полная двуязычная локализация для новых пресетов в `locales/ru.json` и `locales/en.json` (100% паритет ключей).

### Fixed
- **Безопасный Drag-and-Drop в библиотеке действий редактора (`Pure DND Invariant`)**:
  - Устранено случайное автоматическое назначение карточки действия на первый свободный слот или замена выделенной кнопки при обычном клике на карточку в правой панели `ActionLibraryDrawer`.
  - Метод `_on_action_drawer_action_picked` нейтрализован (No-Op): клик по карточке в шторке не перезаписывает кнопки холста. Назначение шаблонов осуществляется строго через Drag & Drop в ячейку.
  - В `ActionItemWidget` удалена преждевременная эмиссия сигнала `item_clicked` в `mousePressEvent` (перенесено в `mouseReleaseEvent` при отсутствии драга с вычислением через `event.position().toPoint()`).
  - При успешном Drop карточки на холст (`_on_canvas_action_dropped`) целевой слот автоматически выделяется в `KeyPropertyInspector` для мгновенной настройки.
- **Интеграция полной матрицы пресетов в шторку действий редактора**:
  - Правая панель `ActionLibraryDrawer` переведена с абстрактного каталога сырых типов на полный реестр готовых карточек-шаблонов `ActionPresetsRegistry.get_categories_dto()` (33 преднастроенных шаблона по 8 категориям).
- **Относительная навигация по страницам деки (`DeckView` & `DeckNavExecutor`)**:
  - Исправлена маршрутизация переходов `next_page`, `prev_page` и `folder_back` в `DeckNavExecutor` и `DeckView`: относительные переходы вызывают `self.next_page()` и `self.prev_page()` без ложных попыток резолва несуществующей страницы `default`.
  - В `DeckView.set_active_page` добавлен безопасный фолбэк на первую доступную страницу (`display_pages[0]`) при отсутствии явной страницы `default` без вывода предупреждений в логи.
- **Стабильность EventFilter холста редактора (`DeckCanvasWidget`)**:
  - Безопасный доступ к `grid_container` через `getattr(self, "grid_container", None)` в `eventFilter` до завершения инициализации дочерних компонентов.
- **Качество и автоматическое тестирование**:
  - Все 539 тестов репозитория имеют статус **100% PASS** (539 passed, 0 failed, 28 warnings).
  - Полное соответствие и 100% паритет словарей локализации (`pytest tests/core/test_i18n_linter.py` -> 6/6 PASS).

## [0.5.6] - 2026-11-23

### Added
- **Реорганизация действий DuckDeck и эталонная матрица пресетов (Этапы 1–4, `.md/deck/deck_action.md`)**:
  - **8 базовых примитивов (`modules/deck/models.py`)**: Сокращение пространства действий до 8 ортогональных примитивов: `hotkey`, `launch`, `audio`, `media`, `text`, `system`, `deck_nav`, `macro` со строгой Pydantic v2 валидацией параметров без `Any`.
  - **Реестр пресетов `ActionPresetsRegistry` (`modules/deck/presets/`)**: Каталог из 6 категорий (`system_tools`, `audio_comm`, `media_control`, `apps_launch`, `navigation`, `macros`) и 20+ преднастроенных карточек с предзаполненными иконками, цветами акцента, статусами и параметрами.
  - **Прозрачный нормализатор `DeckActionNormalizer`**: Автоматическая бесшовная миграция всех 18+ устаревших типов конфигураций (`website`, `volume_control`, `audio_device`, `play_audio`, `stop_audio`, `open_path` и др.) в 8 базовых примитивов при загрузке.
  - **Инвариант чистого первого запуска (Factory Default)**: `DeckConfigLoader.get_default_config()` возвращает ровно одну пустую страницу сетки без демо-данных.
  - **Диспетчер действий `ActionDispatcher`**: Полный рефакторинг на чистый `match-case` по 8 базовым примитивам, изоляция COM-аудио через `EventBus`, подавление дребезга (cooldown 250 мс) и сторожевой таймер.
  - **Компактный инспектор `ButtonPropertyForm` и выпадающее меню пресетов**: Выпадающий список пресетов «⚡ Шаблоны...», компактные подформы параметров высотой $\le 28$ px (`DeckNavSubform`, `UnconfiguredSubform`, `AudioSubform`, `LaunchSubform` и др.), бюджет высоты инспектора строго укладывается в 220 px.
  - **Шторка библиотеки пресетов `ActionLibraryDrawer`**: Интеграция 6 категорий пресетов с живым поиском по двуязычным тегам и кнопкой быстрого назначения на свободный слот.
  - **Связующий слой адаптера и холста (`DeckConfigAdapter`, `window.py`, `grid_cell.py`, `deck_canvas.py`)**: Поддержка сохранения и обновления цветов акцентов (`color_accent`), Drag-and-Drop пресетов на ячейки холста с полной инициализацией параметров слота, поддержка истории Undo/Redo при смене пресетов.
  - **Сквозное E2E тестирование (`tests/integration/test_deck_editor_e2e.py`)**: Сценарии полного цикла (выбор слота, применение пресета, кастомизация, атомарное сохранение, Drag & Drop и Undo/Redo) и верификация обратной совместимости legacy-конфигов.
  - **Качество и локализация**: 100% паритет ключей `locales/ru.json` и `locales/en.json`, проверенный AST-линтером, 538 тестов со статусом 100% PASS (0 failed, 36 deprecation warnings).

## [0.5.5] - 2026-11-22

### Added
- **Кастомизация типографики и всплывающее меню шрифтов (Спринт 7.1, `FontCustomizationPopover`)**:
  - Создан компонент `FontCustomizationPopover(QWidget)` с флагами `Qt.Popup | Qt.FramelessWindowHint`, `Qt.WA_ShowWithoutActivating` и `Qt.NoFocus`, строго сохраняющий инвариант Stealth Focus без отбора активности у основного 27" монитора.
  - Настройка размера шрифта заголовка (9, 11, 13, 15 px), выравнивания (снизу, по центру, сверху), цветовых чипов (5 фирменных свотчей + Reset) и опции скрытия заголовка (`hide_title`).
  - Расширение моделей `DeckButtonConfig` и `ButtonSlotDTO` полями `font_size`, `font_color`, `text_alignment`, `hide_title` с двусторонним мапингом в `DeckConfigAdapter`.
  - Реактивное отображение типографики на ячейках холста редактора `EditorGridCell` и на 7" сенсорных плитках `DeckButtonWidget`.
- **Саундборд и кастомизация звука клика кнопки (Спринт 7.2, `DeckSoundEngine` & `SoundboardSubform`)**:
  - Расширение звукового движка `DeckSoundEngine` методами `play_soundboard(file_path, volume, stop_others)`, `stop_soundboard()`, `preview_sound()` и `stop_preview()`.
  - Реализован пул воспроизведения дорожек саундборда до 8 параллельных эффектов с авто-очисткой завершенных.
  - Поддержка действий каталога `play_audio` и `stop_audio`, модель параметров `SoundboardParams` и компактная подформа инспектора `SoundboardSubform` (28 px).
  - Потокобезопасная маршрутизация аудио через сигналы `play_sound_requested` и `stop_sound_requested` из `ActionRunnable` в GUI-поток `DeckActionDispatcher`.
  - Настройка индивидуального звука клика кнопки (`sound_override`: по умолчанию, без звука / muted, кастомный аудиофайл).
- **Живые динамические тайлы Live Status Tiles (Спринт 7.3, `Live Tiles Engine`)**:
  - Комбобокс `combo_status_source` в форме инспектора с источниками: `none`, `mic_mute`, `audio_device`, `dimmer`, `cpu_temp`, `gpu_temp`.
  - Динамические бейджи статуса в `EditorGridCell` и `DeckButtonWidget.update_status()` с поддержкой цветового акцента `badge_color`.
  - Подписка `DeckView` на шину событий `bus.sensors_updated` с цветовой градацией телеметрии: `<60°C` (изумрудный `#10b981`), `60-74°C` (янтарный `#f59e0b`), `>=75°C` (рубиновый `#ef4444` + значок тревоги `⚠️`).
  - Гарантированная отписка от шины `bus.sensors_updated` при вызове `DeckView.cleanup()`.
- **Локализация и автоматическое тестирование**:
  - 100% паритет словарей локализации `locales/ru.json` и `locales/en.json` без хардкода строковых литералов в UI.
  - Новые тестовые наборы: `test_deck_font_popover.py`, `test_deck_soundboard.py`, `test_deck_live_tiles.py`.
  - Все 479 тестов репозитория имеют статус **100% PASS** (473 passed, 6 skipped).

## [0.5.4] - 2026-11-22

### Added
- **DuckDeck Editor Undo/Redo Engine & Safe UX (`modules/deck/editor/commands.py`, `window.py`)**:
  - Атомарные команды `QUndoCommand`: `AssignActionCommand` (назначение действия из каталога), `ClearSlotCommand` (очистка корзиной), `SwapButtonsCommand` (обмен и копирование с зажатым `Ctrl`), `UpdatePropertyCommand` (реактивное изменение свойств).
  - Стек истории `QUndoStack` с привязкой к хоткеям `Ctrl+Z`, `Ctrl+Y`, `Ctrl+Shift+Z`.
  - Отслеживание несохраненных изменений (`Dirty State`): индикация звездочкой `*` в заголовке окна и сброс при сохранении.
  - Интерактивный диалог подтверждения `closeEvent` (Сохранить / Не сохранять / Отмена) с флагом `_skip_close_dialog` для безопасного запуска в тестовых окружениях.
  - Архитектурная гигиена памяти: автоматический сброс стека `_undo_stack.clear()` при смене страниц (локально или через `bus.deck_page_changed`), сбросе страницы и перезагрузке конфигурации.
- **Нативный Drag-and-Drop на холсте конфигуратора (`widgets/grid_cell.py`, `widgets/action_item.py`, `widgets/deck_canvas.py`)**:
  - Перенос действий из библиотеки на ячейки сетки через MIME-тип `"application/x-duckdeck-action"`.
  - Перемещение и обмен слотов между ячейками и копирование слота с зажатым `Ctrl` через MIME-тип `"application/x-duckdeck-slot"`.
  - Защитная валидация payload (Defensive Programming): строгая проверка типов (`isinstance(dict)`), обязательного ключа `id`, диапазона слотов `0 <= src_slot < 10` и предотвращение сброса на самого себя (`Self-Drop`).
  - Визуальный отклик `drag_hover` с гарантированным снятием подсветки.
- **Инфраструктурные исправления и тестовый раннер**:
  - Устранена блокировка модального Event Loop Qt в `DeckEditorWindow.closeEvent()` при автоматическом прогоне тестов.
  - Корректный сброс выделения активной ячейки холста при очистке слота.
  - 100% покрытие новыми модульными тестами (`test_deck_editor_undo.py`, `test_deck_editor_dnd.py`).
  - Все 455 тестов репозитория имеют статус **100% PASS** (0 failed, 6 skipped).
  - 100% паритет словарей локализации RU/EN, подтвержденный AST-линтером.

## [0.5.3] - 2026-11-22

### Added
- **DuckDeck Editor Ergonomics & Live Autosave (Доработки редактора и верстки)**:
  - **Автосохранение при смене страниц (`modules/deck/editor/window.py`)**:
    - Интеллектуальное автосохранение `save_configuration()` при перелистывании страниц в пагинаторе, клике на кнопку `+` и удаленной смене страниц с сенсорной панели DuckDeck (срабатывает только при наличии несохраненных изменений `_is_dirty`).
    - Автоматическая синхронизация активной страницы `self.active_page_id` при открытии редактора и загрузке конфигурации.
  - **Расширение геометрии редактируемой зоны инспектора (`modules/deck/editor/styles.py`, `button_property_form.py`)**:
    - Увеличение высоты инспектора `INSPECTOR_HEIGHT` и `INSPECTOR_SLOT_HEIGHT` с 220 px до 260 px.
    - Переработан `ColorAccentPicker`: высота увеличена с 20 до 28 px, диаметр свотчей с 18 до 20 px, скругление 10 px, отступы (0, 2, 0, 2), что полностью устранило обрезание нижнего края кнопок палитры.
    - Оптимизированы внутренние отступы `ButtonPropertyForm` (вертикальный спейсинг 8 px) для комфортного отображения всех полей и подформ параметров.
  - **Крупные и контрастные иконки кнопок (`styles.py`, `grid_cell.py`, `deck_button.py`, `key_preview_tile.py`)**:
    - В ячейках сетки холста редактора `EditorGridCell` размер шрифта `CellIconLabel` увеличен с 26 px до 40 px (~+54% полезной площади).
    - В `EditorGridCell` добавлена поддержка масштабирования и отрисовки растровых/векторных файлов иконок (`QPixmap`) с сглаживанием `SmoothTransformation` (48x48 px).
    - На сенсорной панели деки `DeckButtonWidget` размер шрифта иконки увеличен с 38 до 52 px (сетка 2x5) и с 28 до 42 px (сетка 4x6).
    - В плитке предварительного просмотра `KeyPreviewTile` размер шрифта увеличен с 32 до 40 px.
- **DuckDeck Editor Extended Actions, Dynamic Inspector & Full E2E Journey (Спринты 4 и 5 из `.md/deck/edit_func.md`)**:
  - **Расширенный каталог действий (12 новых действий в `actions_registry.py`)**:
    - `website`: открытие URL в веб-браузере по умолчанию с автоподстановкой `https://`.
    - `hotkey_switch`: двухпозиционный переключатель хоткеев с независимыми состояниями State 1 и State 2 (заголовок, иконка, клавиши).
    - `open_path`: запуск/открытие папок или документов через `os.startfile`.
    - `open_app`: изолированный запуск бинарников через `subprocess.Popen(shell=False)` с аргументами и рабочей папкой.
    - `close_window`: мягкое закрытие активного окна Windows через сообщение `WM_CLOSE` (`PostMessageW`).
    - `text_macro`: быстрая вставка текста с поддержкой Unicode/кириллицы через буфер обмена и опциональным Enter.
    - `multimedia`: мультимедийные клавиши Windows через фасады `keybd_event` (Play/Pause, Next, Prev, Stop, Mute, Vol Up/Down).
    - `volume_control`: неблокирующее управление звуком (фокусный процесс, мастер-громкость, микрофон) через Core Audio.
  - **Дискриминированные Pydantic v2 модели параметров (`modules/deck/models.py`)**:
    - Добавлены модели `WebsiteParams`, `HotkeySwitchState`, `HotkeySwitchParams`, `OpenPathParams`, `OpenAppParams`, `CloseWindowParams`, `TextMacroParams`, `MultimediaParams`, `VolumeControlParams` с расширением `ActionType` и фабрикой `DeckActionConfig.get_typed_params()`.
  - **Динамический стек подформ инспектора свойств (`button_property_form.py`)**:
    - Архитектура `QStackedLayout` для бесшовного переключения подформ параметров без вертикального скроллбара (строгое соблюдение бюджета высоты 220 px).
    - `ColorAccentPicker`: горизонтальная панель выбора 5 фирменных неоновых акцентов кнопки (Cyan `#38bdf8`, Emerald `#10b981`, Amber `#f59e0b`, Rose `#f43f5e`, Violet `#a855f7`).
  - **Комплексный сквозной интеграционный сценарий полного цикла E2E (`tests/integration/test_deck_editor_e2e.py`)**:
    - Фазы A..E: Тап ⚙ на 7" экране -> открытие `DeckEditorWindow` на 27" -> настройка Website -> выбор иконки и неонового акцента -> сохранение конфигурации (атомарная запись `.tmp` -> `.bak`) -> реактивный Hot Reload в `DeckView` с сохранением инварианта Stealth Focus (`Qt.NoFocus`).
  - **Полный пакет модульного тестирования ядра и компонентов**:
    - `test_deck_config_adapter.py`: сохранение расширенных полей, изоляция многостраничности, атомарность I/O, восстановление из `.bak`.
    - `test_deck_actions_extended.py`: безопасность Pydantic валидации, мокирование WinAPI, мультимедиа-коды, запуск процессов.
    - `test_deck_property_form_subforms.py`: переключение подформ, выбор цвета акцента, in-place retranslate без потери введенных данных.
    - `test_deck_icon_dialog.py`: модальность, живой поиск, зум 24..64 px, выбор, переключение языка.
  - **Bilingual Localization-First**:
    - 100% паритет RU/EN в `locales/ru.json` и `locales/en.json`, подтвержденный AST-сканером `test_i18n_linter.py`.
  - **Релизные метрики качества**:
    - 418 тестов со статусом **100% PASS** (0 failures, 0 regressions).
- **DuckDeck Editor Icon Ecosystem (Спринт 3 из `.md/deck/edit_func.md`)**:
  - **Контекстное меню быстрого доступа кнопки 'v' (`modules/deck/editor/widgets/key_preview_tile.py`)**:
    - Интерактивное меню `QMenu` в стиле Dark Obsidian v2 под микро-кнопкой `btn_menu`.
    - Пункты: неактивный заголовок `🎨 Иконка кнопки`, `📁 Выбрать из файла...` (системный `QFileDialog`, копирование в `resources/deck/custom_icons/` с генерацией безопасного пути), `📚 Открыть библиотеку иконок...` (`open_library_requested`), `📂 Открыть папку пользовательских иконок` (`os.startfile`), `🗑️ Сбросить иконку`.
    - Новые сигналы `icon_selected = Signal(str)` и `open_library_requested = Signal()`.
  - **Каталог иконок и кэш пиксмапов (`modules/deck/editor/icon_catalog.py`)**:
    - Синглтон `IconCatalog` и потокобезопасный in-memory кэш `IconCache` с предмасштабированием `SmoothTransformation` (устранение задержек GUI при скроллинге).
    - Встроенная библиотека иконок: категории `system`, `apps`, `media`, `glyphs` с рендерингом эмодзи/глифов через `QPainter` на прозрачном фоне.
    - Автосканирование и безопасное копирование пользовательских иконок `resources/deck/custom_icons/` (`.png`, `.svg`, `.ico`, `.jpg`, `.webp`) с разрешением коллизий имен.
    - Двуязычный полнотекстовый поиск (без учета регистра) по ключевым словам `keywords_ru` и `keywords_en`.
  - **Модальный диалог библиотеки иконок (`modules/deck/editor/widgets/icon_library_dialog.py`)**:
    - Диалог `IconLibraryDialog(QDialog)` (580×640 px, модальность `Qt.ApplicationModal`, центрирование на 27" экране).
    - Шапка `HeaderBar` с локализованным заголовком, бейджем счетчика найденных иконок и кнопкой `✕`.
    - Поле живого поиска `SearchBar` с кнопкой мгновенной очистки.
    - Лента категорий (Pills Strip): кнопки-чипы со счетчиками для мгновенной фильтрации.
    - Сетка карточек `IconTileWidget`: подсветка Surface 3 при наведении, неоновый контур `#38bdf8`, одинарный клик для выбора, двойной клик для немедленного подтверждения (`accept()`).
    - Подвал `FooterBar`: переключатель зума сетки (`[-]` 36 px, `[=]` 48 px, `[+]` 60 px), кнопка добавления своих иконок, кнопки «Отмена» и «Выбрать».
  - **Сквозная интеграция событий выбора иконки (`button_property_form.py`, `window.py`, `deck_canvas.py`)**:
    - Вызов библиотеки из инспектора через кнопку `+` и меню `v`, трансляция выбранной иконки в форму, в DTO активного слота и моментальное обновление ячейки на холсте через `canvas.update_cell_icon()`.
  - **Bilingual Localization-First (`locales/ru.json`, `locales/en.json`)**:
    - Пространства `deck.editor.menu.icon` и `deck.editor.dialog.icon_library` со 100% паритетом RU/EN ключей и параметров.
  - **Тестовое покрытие каталога и диалога (`tests/unit/test_deck_icon_catalog.py`, `test_deck_icon_dialog.py`)**:
    - 12 новых тестов на синглтон, категории, двуязычный поиск, кэширование пиксмапов, сканирование папки, геометрию диалога, фильтрацию, зум, выбор и сигналы превью-плитки.
    - Общий объём тестового набора увеличился до **376 passed (100% PASS)**.

## [0.5.2] - 2026-11-22

### Added
- **DuckDeck Editor Core & I/O Integration (Спринт 2 из `.md/deck/edit_func.md`)**:
  - **Singleton-менеджер жизненного цикла (`modules/deck/editor/manager.py`)**:
    - Класс `DeckEditorManager` (потокобезопасный синглтон с методами `open_editor()`, `get_instance()`, `close_editor()`).
    - Автоматическое центрирование окна конфигуратора (1080×740) в рабочей области `primaryScreen` (27" dGPU).
    - Сохранение архитектурного инварианта Stealth Focus: окно создается без родителя (`parent=None`, `isWindow() == True`), не передает клавиатурный фокус на 7" тачскрин.
  - **Интеграция кнопки настроек ⚙ (`modules/deck/widgets/interactive_panel.py`)**:
    - Замена плейсхолдера в `_on_settings_clicked()` на вызов `DeckEditorManager.open_editor(page_id=...)` с отложенным импортом.
    - Тактильная нотификация в бегущей строке: `"Запуск редактора на основном экране..."` / `"Opening editor on primary display..."`.
  - **Двусторонний адаптер данных `DeckConfigAdapter` (`modules/deck/editor/adapter.py`)**:
    - Конвертация `slot_to_dto()` и `dto_to_slot()` со 100% сохранением расширенных полей Pydantic v2 (`status_source`, `color_accent`, `sound_override`, `toggle_action`).
    - Изоляция многостраничной структуры: `load_page_slots()` и `apply_slots_to_page()` предотвращают взаимную утечку данных между страницами (Pages 1..N).
    - Атомарное сохранение `save_deck_config_atomic()`: безопасная запись через временный файл `.tmp` со сбросом системных буферов (`os.fsync`), создание бэкапа `.bak` и атомарная замена `os.replace()`. Защита от повреждения файла при сбоях ввода-вывода.
  - **Кнопка сохранения и хоткей Ctrl+S (`widgets/header_bar.py`, `window.py`)**:
    - Кнопка «💾 Сохранить» в `EditorHeaderBar` со стилями Dark Obsidian v2.
    - Динамическая тактильная индикация успеха сохранения (`"✓ Сохранено!"`, изумрудный цвет, таймер отката 2000 мс).
    - Привязка системного хоткея `QShortcut("Ctrl+S")` в `DeckEditorWindow` с вызовом адаптера и генерацией события шины.
  - **Реактивный Hot Reload макро-панели (`core/event_bus.py`, `modules/deck/view.py`)**:
    - Регистрация глобального сигнала `bus.deck_config_updated`.
    - Подписка `DeckView` с бесшовным in-place обновлением существующих тайлов 2×5 без пересоздания виджетов и мерцания холста.
    - Вывод статуса `"Конфигурация DuckDeck успешно обновлена"` в тикер интерактивной панели.
    - Гарантированная отписка от шины при `cleanup()` без утечек памяти.
  - **Тестовое покрытие I/O и регрессионный сьют (`tests/unit/test_deck_editor_io.py`)**:
    - 10 комплексных тестов на жизненный цикл Singleton, инварианты Stealth Focus, 100% fidelity DTO/Config, изоляцию страниц, атомарность I/O и реактивность шины.
    - Общий объём тестового набора увеличен до **364 passed (100% PASS)**.

## [0.5.1] - 2026-11-22

### Added
- **Dark Obsidian v2 Design System & Editor Polish (Спринт 1 из `.md/deck/edit_func.md`)**:
  - **4-уровневая система поверхностей и палитра Slate (`modules/deck/editor/styles.py`)**:
    - Внедрены токены поверхностей `SURFACE_0_CANVAS` (`#0b0d13`), `SURFACE_1_PANEL` (`#0f141f`), `SURFACE_2_CARD` (`#141924`), `SURFACE_3_HOVER` (`#1c2940`).
    - Внедрена типографика Slate: `TEXT_SLOT_INDEX` (`#475569`), `TEXT_PRIMARY_HIGH` (`#f8fafc`), `TEXT_SECONDARY_MED` (`#94a3b8`), `TEXT_MUTED_SUBTLE` (`#64748b`).
    - Обеспечена 100% обратная совместимость через Re-export Shims (`BG_WINDOW`, `BG_PANEL`, `BG_CARD`, `BG_CELL`, `BORDER_SUBTLE` и др.).
  - **Рефакторинг ячеек сетки `EditorGridCell` (`modules/deck/editor/widgets/grid_cell.py`)**:
    - Устранены все инлайн-стили вызовами `setStyleSheet()`.
    - Добавлены селекторы классов `.CellIndexLabel`, `.CellIconLabel`, `.CellTitleLabel` для точной стилизации в `EDITOR_MAIN_QSS`.
    - Добавлен инвариант `setFocusPolicy(Qt.NoFocus)` для соблюдения Stealth Focus.
  - **Стилизация подложки холста и тачбара (`widgets/touchbar_strip.py`, `touchbar_section.py`)**:
    - Динамический селектор состояния выбора `TouchbarSectionWidget[selected="true"]` с акцентной неоновой окантовкой 2 px (`#38bdf8`).
    - Плавное фоновое выделение при наведении `:hover` (`SURFACE_3_HOVER` `#1c2940`).
  - **Инспектор свойств и превью-плитка (`widgets/key_preview_tile.py`, `button_property_form.py`)**:
    - Плитка `KeyPreviewTile` 84×84 px на базе `SURFACE_2_CARD` с микро-кнопками опций иконки 20×20 px.
    - Контрастный глубокий фон полей ввода `QLineEdit.InspectorLineEdit` (`#101522`) и алый акцент кнопки удаления `InspectorDeleteButton` (`#ef4444`).
  - **Каталог действий и строка поиска (`widgets/action_drawer.py`, `search_bar.py`, `action_category.py`, `action_item.py`)**:
    - Стилизация разделителя панели `QSplitter` с неоновым ховером.
    - Карточки действий `ActionItemCard` и подложки иконок `ActionItemIconBox`.
  - **Модульные тесты стилей и целостности QSS (`tests/unit/test_deck_editor_styles.py`)**:
    - Полная валидация токенов поверхностей, палитры Slate, HEX-форматов и shims.
    - Тесты переключения динамического свойства `selected` ячейки `EditorGridCell` и секции `TouchbarSectionWidget`.
    - Тестовый набор расширен до **329 passed (100% PASS)**.

## [0.5.0] - 2026-11-21

### Added
- **DuckDeck Button & Touchbar Editor (WYSIWYG Configurator, Фазы 1–6 из `.md/deck/edit_but.md`)**:
  - **Каркас окна и стилизация (`modules/deck/editor/window.py`, `styles.py`)**:
    - Класс `DeckEditorWindow` (1080×740, min 960×640) с двухпанельной компоновкой `QSplitter` (соотношение 70/30: рабочая область 756 px / библиотека действий 324 px, `childrenCollapsible=False`).
    - Дизайн-система Dark Obsidian (`#0f0f11`, `#18181b`, `#222227`, `#27272a`, акценты `#38bdf8` / `#0078d4`, типографика Segoe UI, скругления 6 px, тонкие скроллбары 6 px).
    - Безопасная стилизация заголовка окна Win32 DWM `apply_immersive_dark_titlebar()` с изоляцией `OSError`.
    - Реактивный протокол Localization-First (`retranslate_ui()` и подписка на `bus.language_changed`).
  - **Верхняя панель устройств и профилей (`widgets/header_bar.py`)**:
    - Компонент `EditorHeaderBar` (высота 52 px) с кастомными селекторами `DeviceComboBox` и `ProfileComboBox`.
    - Сохранение стабильных `userData` и обновление текста при смене языка без сброса активного выбранного индекса.
    - Перехват пункта `+ New Profile...` с эмиссией сигнала `create_profile_requested`.
    - Сервисные кнопки тулбара (Notifications, Plugins, Settings, Profile) со всплывающими подсказками `QToolTip` в стиле Dark Obsidian.
  - **Интерактивный холст кнопок и тачбара (`widgets/deck_canvas.py`, `grid_cell.py`, `touchbar_section.py`, `pagination_bar.py`)**:
    - Сетка макро-кнопок 2×5: 10 ячеек `GridCellWidget` (80×80 px, отступы 10 px) с визуализацией иконки, заголовка, категории и состояния пустого слота (`+`).
    - Полоса тачбара (3-й ряд) с 3 интерактивными секциями: Media (обложка, трек, плеер), Clock (HH:mm, день недели, дата), Telemetry (CPU/GPU бейджи, график).
    - Подсветка активного выбора акцентной синей рамкой 2 px (`#38bdf8`) и сброс выделения по клику в нейтральный фон или по клавише `Escape`.
    - Панель пагинации `PageNavigationBar` с кнопками переключения страниц и точечными индикаторами (`● ○ ○`).
  - **Инспектор свойств (`widgets/property_inspector.py`, `inspector_widgets.py`)**:
    - Двухрежимный `KeyPropertyInspector` на базе `QStackedWidget`:
      - Режим 0: Плейсхолдер с центрированной подсказкой (`deck.editor.inspector.placeholder_no_selection`).
      - Режим 1: Форма параметров кнопки `ButtonPropertyForm` (превью `KeyPreviewTile`, поле `Title`, селектор `Action`, кнопка захвата хоткея `HotkeyCaptureButton` с интерактивным режимом перехвата и очисткой Backspace/Delete, кнопка удаления `🗑️`).
      - Режимы 2–4: Специализированные формы настройки секций тачбара (`TouchbarMediaForm`, `TouchbarClockForm`, `TouchbarTelemetryForm`).
  - **Библиотека действий и двуязычный поиск (`widgets/action_drawer.py`, `search_bar.py`, `action_category.py`, `action_item.py`, `actions_registry.py`)**:
    - Панель `ActionLibraryDrawer` со строкой поиска `ActionSearchBar` (микро-кнопка очистки `✕`, кнопка вида `☰`).
    - Аккордеон категорий `ActionCategorySection` с независимым сворачиванием секций (шевроны `›` / `⌄`).
    - Карточки действий `ActionItemWidget` с подложками иконок и каскадным переводом названий.
    - Мгновенная двуязычная фильтрация поиска по названию и ключевым тегам `keywords` на русском и английском языках (например, "хоткей" / "hotkey", "папка" / "folder").
    - Плейсхолдер пустого результата поиска с интерполяцией запроса (`deck.editor.drawer.no_results`).
    - Прямое назначение выбранного действия из каталога на выделенный слот холста.
  - **Демо-данные, лончер и CLI интеграция (`demo_data.py`, `demo_launcher.py`, `main.py`)**:
    - Фабрика эталонного датасета `get_demo_editor_profile()` по референсной раскладке.
    - Автономный запуск через `python -m modules.deck.editor.demo_launcher` с предварительной инициализацией Per-Monitor DPI Awareness V2.
    - Интеграция CLI флага `--editor` / `--deck-editor` в главную точку входа `main.py`.
  - **Автоматизированное тестирование (326 тестов, 100% PASS)**:
    - Модульные тесты каркаса окна (`test_deck_editor_window.py`).
    - Модульные тесты верхней панели (`test_deck_editor_header_bar.py`).
    - Модульные тесты холста, ячеек и тачбара (`test_deck_editor_canvas.py`).
    - Модульные тесты инспектора свойств и виджетов форм (`test_deck_editor_inspector.py`, `test_deck_editor_inspector_widgets.py`).
    - Модульные тесты строки поиска и библиотеки действий (`test_deck_editor_search_bar.py`, `test_deck_editor_action_drawer.py`).
    - Модульные тесты CLI флагов `main.py` (`test_main_cli.py`).
    - Сквозной E2E интеграционный тест полного пользовательского пути и Hot Reload (`tests/integration/test_deck_editor_e2e.py`).
    - Общий тестовый набор увеличен с 227 до **326 тестов (100% PASS)**.

## [0.4.2] - 2026-11-20

### Added
- **Подсистема интернационализации (I18n) и сквозная локализация интерфейса (Фазы 1–4)**:
  - **Ядро `core/i18n` (Foundation Layer)**:
    - `I18nManager` (Singleton) с потокобезопасным кэшем, развертыванием словарей в плоскую структуру dot-notation ($O(1)$ поиск) и предзагрузкой `locales/ru.json` и `locales/en.json`.
    - Безопасный форматтер `SafeFormatter` (отсутствие `KeyError`/`IndexError` при неполных аргументах).
    - Симметричный каскад fallback: активный язык $\to$ резервный язык $\to$ raw_key с `logger.warning`.
    - Плюрализация `tp()`: поддержка 3 грамматических форм в русском (`one`, `few`, `many`) и 2 форм в английском (`one`, `other`).
    - Публичный интерфейс ядра: экспорт функций `t()`, `tp()`, `resolve_plural_category()`.
  - **Реактивность UI-каркаса (`core.ui_base.TouchModuleView`)**:
    - Базовый класс экранов автоматически подписывается на сигнал `bus.language_changed`.
    - Виртуальный метод `retranslate_ui()` вызывается при смене языка и в конце сборки виджетов.
    - Гарантированная отписка в `cleanup()` без утечек памяти C++ объектов.
  - **Сквозная миграция всех модулей и экранов интерфейса**:
    - **Audio (`modules/audio`)**: локализация `AudioMixerView` и `SessionCardWidget`, плюрализация количества активных сессий процесса (`audio.sessions.count`), переключение аудиовыхода и Mute.
    - **Deck (`modules/deck`)**: локализация фоновых нотификаций `DeckActionDispatcher`, трех секций интерактивной панели `DeckInteractivePanel` (медиа-пульт, часы/календарь с двуязычным форматированием даты, тикер), `header_bar` и реактивных динамических тайлов (микрофон, аудиовыход, ночной режим).
    - **Telemetry (`modules/telemetry`)**: локализация NOC-дашборда `SensorsView` (шапка, Hero-карточки CPU/GPU, сетка чипов RAM/Net/SSD/Chassis, тултипы спарклайнов) с сохранением непрерывной работы `TelemetryWorker` без перезапуска потока.
    - **Media (`modules/media`)**: локализация навигации `YouTubeView` и элементов управления fallback-плеера.
    - **Showcase (`ui/showcase_view.py`)**: рефакторинг с переходом на наследование от `TouchModuleView`, регистрация карточек диагностики, полная локализация параметров и интеграция сенсорной карточки выбора языка интерфейса (`_create_language_card()`) с кнопками `[ 🇷🇺 Русский ]` и `[ 🇬🇧 English ]`, подсветкой активного состояния, сохранением в `config.json` и мгновенным хот-релоадом локали на вкладке шестеренки `⚙`.
    - **Settings (`modules/settings`)**: кнопки мгновенного переключения языка (`RU` / `EN`), атомарное сохранение в `config.json` и эмиссия сигнала `bus.language_changed`.
    - **Sidebar & Shell (`ui/sidebar.py`, `ui/widgets/mini_media_bar.py`)**: локализация тултипов вкладок сайдбара и кнопки блокировки экрана.
  - **Автоматизированная верификация и тестирование (227 тестов, 100% PASS)**:
    - Модульные тесты `tests/unit/test_i18n.py` (9 тестов).
    - Модульные тесты `tests/unit/test_audio_i18n.py` (3 теста), `tests/unit/test_deck_i18n.py` (3 теста), `tests/unit/test_telemetry_i18n.py` (1 тест), `tests/unit/test_media_i18n.py` (1 тест), `tests/unit/test_showcase_i18n.py` (2 теста), `tests/unit/test_settings_language.py` (7 тестов), `tests/unit/test_i18n_ui.py` (6 тестов), `tests/unit/test_locale_validation.py` (5 тестов).
    - Тест-линтер чистоты строк `tests/unit/test_i18n_completeness.py` (3 теста: 100% паритет ключей, консистентность плейсхолдеров интерполяции, AST-сканер отсутствия сырого кириллического хардкода в UI коде).
    - Сквозной интеграционный тест `tests/integration/test_i18n_hot_reload.py` (проверка полной смены языков RU -> EN -> RU во всех вкладках без перезапуска).
    - Общий тест-сьют увеличен со 181 до **227 тестов (100% PASS)**.

## [0.4.1] - 2026-11-19

### Added
- **DuckDeck v0.4.1 (Этап 4: Режим заглушек Stubs Mode, звуковой движок DeckSoundEngine и DoD верификация)**:
  - **Stubs Mode (`simulation_mode`)**:
    - В `modules/deck/action_dispatcher.py` внедрен флаг `simulation_mode: bool = False`.
    - В режиме симуляции при тапе по кнопке воспроизводится тактильный цикл (`action_started` -> `executing`, `action_finished` -> `success`) с трансляцией сообщения в `bus.deck_notification` без запуска задач в `QThreadPool`.
    - Изолированный антидребезг (cooldown 250 мс) по идентификаторам кнопок.
    - Корневой параметр `"simulation_mode": false` в `config/deck_config.json` с валидацией Pydantic v2.
  - **Звуковой движок интерфейса (`DeckSoundEngine`)**:
    - В `modules/deck/sound_engine.py` реализован движок аппаратных звуковых эффектов (Zero-Latency Audio) на базе `PySide6.QtMultimedia.QSoundEffect` с предзагрузкой семплов в RAM (0 мс задержка, без кражи фокуса и без блокировки Qt Event Loop):
      - `button_click.wav` (клик плитки / tap),
      - `button_sw_page.wav` (переключение страницы / page_switch),
      - `button_offline.wav` (ошибка / блокировка / error),
      - `button_online.wav` (успешное выполнение / success).
    - Управление громкостью (`0.0 .. 1.0`) и включением/выключением из модели `SoundSettings`.
    - Поддержка индивидуального переопределения звука кнопки (`sound_override`).
    - Создан фасад обратной совместимости `core/deck/sound_engine.py` (Re-export Shim) и экспорт в `modules/deck/__init__.py`.
  - **Связка с `DeckView` и жизненный цикл**:
    - Озвучивание тапов по плиткам, смены страниц (свайп/пагинация) и ошибок выполнения.
    - Каскадный метод `cleanup()` с гарантированной остановкой `QSoundEffect` и очисткой ресурсов.
  - **Модульное и интеграционное тестирование**:
    - Создан сьют `tests/unit/test_deck_sound_engine.py` (6 тестов).
    - Расширены сьюты `tests/unit/test_deck_actions.py` и `tests/unit/test_deck_panel.py`.
    - Рекурсивный аудит Stealth Focus (`test_deck_interactive_panel_full_stealth_focus_audit`) — 100% дочерних виджетов имеют `Qt.NoFocus`.
    - Проверка сохранности боевых экшенов `modules/deck/actions/` (`hotkey_sender`, `process_launcher`, `http_client`, `screen_capture`, `audio_device_switcher`).
    - Тест-сьют увеличен со 165 до **181 теста (100% PASS)**.

### Fixed
- **Стабилизация тайминга анимации диммера**:
  - В `tests/unit/test_dimmer.py` оптимизировано ожидание завершения анимации `DimmerOverlay` при высокой нагрузке на процессор во время прогона полного тест-сьюта.

## [0.4.0] - 2026-11-16

### Added
- **DuckDeck v0.4.0 (Этапы 1–3: Архитектурный фундамент, интерактивная панель и кинематика свайпа)**:
  - **Этап 1: Раскладка 2×5 и спецификация ресурсов:**
    - `core/event_bus.py`:
      - Зарегистрированы сигналы `deck_notification = Signal(str)` (трансляция сообщений в тикер панели) и `deck_page_changed = Signal(str)` (синхронизация смены активного профиля).
    - `modules/deck/models.py`:
      - Расширение Pydantic v2 модели `DeckButtonConfig`: `slot_index` (0..9), `category` (`system`, `shortcut`, `program`, `api`), `icon_size` (16..128 px), `icon_path`, `sound_override`.
      - Модель `SoundSettings` (`enabled`, `volume` 0.0..1.0, `default_tap_sound`, `page_switch_sound`, `error_sound`, `success_sound`).
      - Поддержка `simulation_mode` и `sound_settings` в `DeckRootConfig`.
    - `config/deck_config.json`:
      - Актуализация страниц `default` и `grid4x6` под строгую сетку 2x5 (ровно 10 кнопок на страницу со слотами 0..9).
    - `DuckDock.spec`:
      - Регистрация `resources/deck` и `config/deck_config.json` в `datas`, `PySide6.QtMultimedia` в `hiddenimports`.
    - `.gitignore`:
      - Белый список `!DuckDock.spec` для контроля спецификации сборки в Git.
  - **Этап 2: Интерактивная сенсорная панель (`DeckInteractivePanel`):**
    - `modules/deck/widgets/interactive_panel.py`:
      - Создана сенсорная панель 920×216 px (`TouchModuleView`, `Qt.NoFocus`, фон `#111622`, радиус 14 px) с 3 секциями:
        - Левая секция (280 px): медиа-пульт с обложкой 48×48 px, бегущей строкой `MarqueeLabel` и сенсорными кнопками ⏮ ⏯ ⏭ (`media_action_requested` / `media_state_changed`).
        - Центральная секция (360 px): моноширинные цифровые часы 34 px Bold `#38bdf8` с датой, сенсорный трек свайпа и точечная пагинация `DotPagingWidget` (● ○ ○) с кинетическим перекатом точки (220 мс, OutCubic) и световыми шевронами ‹ ›.
        - Правая секция (280 px): мини-индикаторы температур CPU/GPU (`sensors_updated`), `NotificationTicker` для системных уведомлений с затуханием 3с и кнопка настроек ⚙.
  - **Этап 3: Детекция горизонтального свайпа и кинематика переключения страниц:**
    - `modules/deck/widgets/swipe_detector.py`:
      - Реализован кинематический детектор 1-пальцевого горизонтального свайпа `DeckSwipeDetector` (пороги $dt \le 600$ мс, $|dx| \ge 60$ px, угловой фильтр $|dx| > 1.5 \cdot |dy|$).
      - Защита от синтетического клика мыши (`_suppress_mouse_release`).
      - Бесконфликтная изоляция с глобальным 2-пальцевым фильтром `TouchCursorFilter` (`len(points) > 1` беспрепятственно передается выше).
    - `modules/deck/widgets/deck_button.py`:
      - Автоматический сброс нажатия кнопки (`cancel_press()`, возврат в `"idle"`) при смещении пальца $|dx| \ge 20$ px с гарантированным подавлением клика при отпускании (`_swipe_consumed = True`).
    - `modules/deck/widgets/deck_grid.py`:
      - Интеграция `DeckSwipeDetector` на сетку и все кнопки тайлов, плавная Fade-In анимация (160 мс) при смене страниц.
    - `modules/deck/view.py`:
      - Связка свайпов сетки и панели с перелистыванием страниц `next_page()` / `prev_page()` и шиной `bus.deck_page_changed`.
  - **Тестирование и верификация:**
    - Новые сьюты: `tests/unit/test_deck_panel.py`, `tests/unit/test_deck_swipe_isolation.py`, `tests/unit/test_deck_swipe_paging.py`.
    - Общий тест-сьют увеличен до **165 тестов (100% PASS)** без регрессий.
- **Спринт 6: Переход на Feature-First модульную архитектуру и Foundation Decoupling**:
  - `core/ui_base.py`:
    - Базовый абстрактный класс `TouchModuleView(QWidget)` с принудительной политикой `setFocusPolicy(Qt.NoFocus)` и методом жизненного цикла `cleanup()`.
    - Все экранные модули (`SensorsView`, `YouTubeView`, `AudioMixerView`, `DeckView`, `SettingsView`) переведены на наследование от `TouchModuleView`.
  - `modules/` — автономная Feature-First структура модулей:
    - `modules/audio/`: сервис аудиомикшера `service.py` (`AudioManager`), модели `models.py` (`AudioSessionInfo`, `AudioDeviceInfo`), Win32/COM драйвер переключения конечных точек `platform/device_switcher.py`, экран `view.py` (`AudioMixerView`).
    - `modules/telemetry/`: Ring 0 мониторинг `hardware_monitor.py` (`HardwareMonitor`), сборщик XML `aida_reader.py`, фоновый поток `worker.py` (`TelemetryWorker`), буфер метрик `history.py` (`RingBuffer`, `TelemetryHistory`), DTO `models.py` (`TelemetrySnapshot`), NOC-экран `view.py` (`SensorsView`).
    - `modules/media/`: профиль браузера `web_profile.py` (`WebProfileManager`), блокировщик рекламы `interceptor.py` (`AdBlockInterceptor`), сквозной мини-плеер `widgets/mini_media_bar.py` (`MiniMediaBar`), плеер `view.py` (`YouTubeView`).
    - `modules/deck/`: диспетчер действий `action_dispatcher.py` (`DeckActionDispatcher`), Pydantic-модели `models.py`, драйверы `actions/` (`hotkey_sender`, `process_launcher`, `http_client`, `screen_capture`), виджеты `widgets/` (`DeckButtonWidget`, `DotPagingWidget`), экран `view.py` (`DeckView`).
    - `modules/settings/`: валидация и загрузка настроек `config.py` (`AppConfig`, `DisplayConfig`, `StealthConfig`, `load_config`), каркас экрана настроек `view.py` (`SettingsView`).
  - `ui/widgets/`:
    - Выделение переиспользуемых независимых UI-компонентов: `touch_slider.py` (`TouchSlider`), `marquee_label.py` (`MarqueeLabel`), `sparkline.py` (`SparklineWidget`).

### Changed
  - **Shell Integration & Direct Imports**:
    - `main.py`: переключен на прямой импорт `load_config` из `modules.settings.config`.
    - `ui/main_window.py`: переключен на прямые импорты представлений экранов из `modules.*.view` (`SensorsView`, `YouTubeView`, `AudioMixerView`, `DeckView`) и конфигурации `AppConfig` из `modules.settings.config`.
    - `ui/sidebar.py`: переключен на прямой импорт `MiniMediaBar` из `modules.media.widgets.mini_media_bar`.
  - **Decoupling Audio & Deck**:
    - Полностью устранена циклическая зависимость между `AudioManager` и `DeckActionDispatcher`.
    - Модель `AudioDeviceInfo` перемещена в `modules/audio/models.py`.
    - COM-драйвер `IPolicyConfigClient` изолирован в `modules/audio/platform/device_switcher.py`.
  - **Re-export Shims & Backward Compatibility**:
    - Организованы прозрачные фасады обратной совместимости в `core/` и `ui/modules/` с динамическим алиасингом `sys.modules`, сохранившие 100% работоспособность всех внешних потребителей и тестов без регрессий.
  - `pyproject.toml`:
    - Версия обновлена до `0.4.0`.
    - Сконфигурирован линтер ruff: исключения служебных папок, правила `E`, `F`, `W`, per-file-ignores для `main.py`, shims и тестов.

## [0.3.0] - 2026-11-15

### Added
- **Спринт 5: Сенсорная макро-панель DuckDeck и управление аудиоустройствами**:
  - `core/deck/`:
    - Модели данных `models.py`: Pydantic V2 схемы конфигурации DuckDeck (`DeckRootConfig`, `DeckPageConfig`, `DeckButtonConfig`, `DeckActionConfig`), типы параметров (`HotkeyParams`, `ProcessParams`, `HttpParams`, `ScreenshotParams`, `AudioDeviceParams`, `SystemParams`), типизированное представление `AudioDeviceInfo`.
    - Диспетчер действий `action_dispatcher.py` (`DeckActionDispatcher`):
      - Асинхронное выполнение задач в глобальном пуле потоков `QThreadPool`.
      - Защита от дребезга нажатий (cooldown 250 мс на тайл).
      - Сигналы обратной связи `action_started`, `action_finished` (успех/ошибка с описанием) и `page_switch_requested`.
    - Действия `core/deck/actions/`:
      - `hotkey_sender.py`: отправка аппаратных скан-кодов через `SendInput` (`KEYEVENTF_SCANCODE`) с поддержкой Win/Ctrl/Alt/Shift, очисткой модификаторов и предварительным восстановлением фокуса целевого окна без активации DuckDock.
      - `audio_device_switcher.py`: прямое управление аудиоустройствами по умолчанию Windows через нативный COM-интерфейс `IPolicyConfigClient` (`eConsole`, `eMultimedia`, `eCommunications`) и циклический переключатель `toggle_audio_device`.
      - `process_launcher.py`: detached-запуск процессов и протоколов (`os.startfile` / `subprocess.Popen` с `CREATE_NO_WINDOW | DETACHED_PROCESS`).
      - `http_client.py`: неблокирующие REST/HTTP-запросы (`urllib.request`) с таймаутами для локальных API (OpenRGB, Home Assistant, OBS).
      - `screen_capture.py`: чистый захват основного экрана 2560×1440 через `QScreen` / `BitBlt` напрямую в буфер обмена `QGuiApplication.clipboard()`.
  - `ui/modules/deck_view.py`:
    - Полноэкранный сенсорный интерфейс макро-панели 944×600 (`DeckView`):
      - Верхняя панель (Header Bar 48 px): динамический селектор страниц, кнопка перезагрузки JSON-конфига и статус.
      - Настраиваемая сетка кнопок (3×5 — 174×168 px или 4×6 — 145×124 px).
      - Сенсорные тайлы (`DeckButtonWidget`): крупные иконки (48×48 px), заголовки и субтитры, кинетическая тактильная обратная связь при нажатии (`_is_pressed`, `_is_executing`), анимация ошибки (тряска Shake) и защита от зависания через сторожевой таймер (Watchdog 5000 мс).
      - Реактивные динамические тайлы (`Live Tiles`): автоматическое обновление иконки и статуса переключателя аудиоустройств (`🎧`/`🔊`) и микрофона (`🎙`/`🔇`) через события `EventBus`.
  - `ui/sidebar.py`:
    - Кнопка вкладки 2 переименована в `btn_deck` с иконкой `🎛` и подсказкой `DuckDeck (Макро-панель и управление)`.
  - `ui/modules/audio_view.py`:
    - Сенсорная кнопка быстрого переключения вывода звука `btn_switch_device` в шапке микшера.
    - Мгновенная синхронизация мастер-громкости и списка сессий при смене устройства по умолчанию.
  - `config/deck_config.json`:
    - Готовая дефолтная конфигурация профилей: «Default» (звук, микрофон, диммер, скриншот, калькулятор, блокнот), «Dev / Tools» (VSCode, Windows Terminal, Chrome, Git GUI), «Gaming» (хоткеи Discord, оверлей, полноэкранный захват).
  - Тестирование:
    - Модульные тесты `tests/unit/test_deck_actions.py`, `tests/unit/test_deck_view.py`, `tests/unit/test_audio_device_switcher.py`.
    - Интеграционный тест `tests/integration/test_deck_integration.py` (сквозная проверка маршрутизации сигналов, микшера и DuckDeck).

### Changed
  - `ui/main_window.py`:
    - Заменена статическая заглушка `page_happ` на интерактивную макро-панель `DeckView`.
    - Добавлен жизненный цикл `cleanup()` при закрытии окна.
  - `config.json`:
    - Удален устаревший процесс `happ` из списка `tracked_apps`.
  - `core/audio_manager.py`:
    - Интегрированы методы управления дефолтными эндпоинтами (`get_playback_devices`, `set_default_playback_device`, `toggle_playback_device`).
    - Добавлено управление состоянием микрофона (`is_mic_muted`, `set_mic_mute`, `toggle_mic_mute`).
    - Добавлено кэширование и метод `invalidate_cache()`.
  - `core/event_bus.py`:
    - Добавлены сигналы `playback_device_changed(device_name, device_id)` и `mic_mute_changed(is_muted)`.

## [0.2.0] - 2026-11-14

### Added
- **Спринт 6: Тач-жесты (Swipe Engine), кинетика Dimmer и автономная сборка**:
  - `core/touch_filter.py`:
    - Движок распознавания двухпальцевого вертикального свайпа (`TouchCursorFilter`):
      - Свайп снизу вверх (`avg_dy <= -70px`) — переключение на следующий экран (`+1`).
      - Свайп сверху вниз (`avg_dy >= +70px`) — переключение на предыдущий экран (`-1`).
      - Строгая фильтрация ложных жестов: $len(points) == 2$, $dt \le 500\text{ ms}$, сонаправленность $dy_0 \cdot dy_1 > 0$, отсечение горизонтальных/диагональных движений $|avg\_dy| > 1.3 \cdot |avg\_dx|$.
      - Подавление синтетического клика мыши после завершения жеста (`_suppress_mouse_release = True`).
      - Свободный пропуск одиночных тапов (включая сайдбар) элементам UI без задержек.
  - `resources/manifest.xml`:
    - Windows PE манифест с правами `requireAdministrator` (Ring 0 драйвер LHM) и `PerMonitorV2` DPI Awareness.
  - `build_exe.py` & `build.bat`:
    - Автономный сборщик PyInstaller в режиме `--onedir` (`dist/DuckDock/`) со временем старта <300 мс.
    - Бандлинг ресурсов: `resources/bin/LibreHardwareMonitorLib.dll`, `resources/css/`, `resources/js/`, `config.json`.
    - Твик реестра Windows: автоматическая регистрация `GpuPreference=1;` в `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` для изоляции на iGPU.
    - Автоматическая генерация автономного архива `dist/DuckDock-v0.2.0.zip` (184.9 МБ).
    - Вспомогательный переносимый скрипт `register_igpu.bat`.
  - `tests/unit/test_gestures.py`:
    - 10 сценариев модульного тестирования синтетических тач-событий (свайпы вверх/вниз, таймауты, амплитуда, пинч/зум, циклический переключатель).

### Changed
  - `ui/dimmer_overlay.py`:
    - Кинетическая анимация изменения прозрачности через `QVariantAnimation` (200 мс, `QEasingCurve.Type.OutCubic`).
    - Бинарный переключатель `toggle(target_level=0.50)` между 0.0 (день) и 0.50 (ночь).
    - Плавный реверс анимации на лету при повторном нажатии без скачков.
    - Оптимизация `paintEvent` (0% нагрузки на GPU при opacity=0.0).
    - Строгое сохранение инвариантов `Qt.WA_TransparentForMouseEvents`, `Qt.WA_ShowWithoutActivating` и `Qt.NoFocus`.
  - `config.json` & `core/config.py`:
    - Значение `"night_mode_opacity"` обновлено с `0.85` до `0.50` (50% затемнение).
  - `ui/showcase_view.py`:
    - Управление ночным режимом строго через кнопку `🌙 Включить ночной режим (Диммер)` в разделе «Диагностика».
    - Кнопка диммера удалена из сайдбара (`SidebarDock`) в соответствии со спецификацией.
  - `core/config.py`, `core/web_profile.py`, `core/hardware_monitor.py`:
    - Бесшовный fallback поиска конфигурации и ассетов (`config.json`, DLL, CSS, JS) при запуске из `--onedir` скомпилированного пакета (`sys.executable / sys._MEIPASS`).
  - `tests/unit/test_dimmer.py`:
    - 12 комплексных тестов кинетики анимации, смены направления на лету, устойчивости к быстрому клику и сквозной интеграции.

### Fixed
  - Устранена потенциальная рассинхронизация тач-свайпов и мышиного клика.
  - Обеспечен чистый импорт `sys` в модуле `core/web_profile.py`.

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
