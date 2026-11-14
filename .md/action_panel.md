# DuckDock: Архитектурный план и спецификация модуля «DuckDeck» (Action Panel / Stream Deck)

> **Статус документа:** Активный план реализации и архитектурная спецификация (Спринт 5 / v0.2.0)  
> **Целевая конфигурация:** Windows 10/11 x64, два монитора: 27" Primary 2560×1440 (dGPU) + 7" 1024×600 (JRP7813S Touchscreen на iGPU AMD Radeon Graphics, Ryzen 7 7700).  
> **Архитектурный закон:** `GEMINI.md` (Platform-First, Zero-Bespoke, Stealth Focus, Non-blocking I/O, Per-Monitor DPI V2).  
> **Зона размещения:** Вкладка 2 (`QStackedWidget`, геометрия рабочей зоны 944×600), полная замена рудиментарного тайлинга `happ.exe`.

---

## 1. Концепция и цели модуля

Вкладка 2 исходно проектировалась как заглушка тайлинга внешнего прокси-клиента `happ.exe`. Практический опыт показал, что статичный тайлинг стороннего окна неэффективно использует ресурсы 7-дюймового сенсорного дисплея.

**DuckDeck (Action Panel)** преобразует вторую вкладку в полноценный сенсорный макро-пульт (аналог Elgato Stream Deck / Loupedeck), ориентированный на гейминг, разработку и системное управление ПК:
1. **Клавиатурные макросы и хоткеи:** Симуляция аппаратных скан-кодов клавиш без кражи фокуса у активных полноэкранных игр или среды разработки на основном 27" экране.
2. **Переключение аудиоустройств (Audio Device Switcher):** Сенсорный переключатель активного устройства вывода Windows (Наушники 🎧 <-> Колонки 🔊) в один тап через нативный COM-интерфейс `IPolicyConfig`.
3. **Запуск процессов и утилит:** Мгновенный запуск приложений, bat/ps1 скриптов и системных утилит в изолированном detached-режиме (`CREATE_NO_WINDOW`).
4. **API-интеграция с локальным софтом:** Асинхронные HTTP/REST запросы к OpenRGB (управление подсветкой), OBS WebSocket / REST bridge (сцены, запись), Home Assistant (свет, розетки), Discord RPC.
5. **Системные операции и скриншоты:** Захват чистого скриншота основного экрана (2560×1440) или активного окна напрямую в буфер обмена Windows; быстрое переключение микрофона (Mute Mic), блокировка рабочей станции, управление затемнением экрана.
6. **Мультипрофильность и страницы:** Организация клавиш по страницам («Default», «Gaming», «Dev / Tools») с мгновенным переключением в Header Bar и динамическими живыми тайлами (Live Tiles).

---

## 2. Архитектурные инварианты и анализ рисков

### Инвариант 1: Stealth SendInput & Неприкосновенность фокуса (P0)
* **Проблема:** При таче по экрану DuckDock Windows пытается сфокусировать нажатое окно. Если фокус перейдет на DuckDock, отправка хоткея (например, шорткат Discord или игры) уйдет в пустоту, а активное окно на мониторе 1 потеряет ввод.
* **Решение:**
  1. Окно панели сохраняет атрибуты `WS_EX_NOACTIVATE` и `Qt.WA_ShowWithoutActivating`.
  2. Все виджеты кнопок и переключатели страниц строго получают `Qt.NoFocus`.
  3. Модуль `core.deck.actions.hotkey` считывает целевое окно через `GetForegroundWindow()`. Если окно принадлежит DuckDock, `FocusGuardian` предварительно восстанавливает фокус последнего активного окна (`last_primary_hwnd`).
  4. Симуляция ввода выполняется через Win32 API `SendInput` с флагом `KEYEVENTF_SCANCODE` и аппаратными скан-кодами (`MapVirtualKeyW`) плюс `KEYEVENTF_EXTENDEDKEY` для расширенных клавиш, что обеспечивает 100% совместимость с играми на DirectX/Vulkan.
  5. Очистка модификаторов: блок `finally` гарантирует отправку `KEYEVENTF_KEYUP` для всех зажатых модификаторов (`Ctrl`, `Alt`, `Shift`, `Win`).

### Инвариант 2: Неблокирующий ввод-вывод (Thread Pool Isolation & Debounce)
* **Проблема:** Сетевые HTTP-запросы (OpenRGB, Home Assistant) или запуск тяжелых скриптов могут заблокировать поток Qt GUI при недоступности сервиса или таймауте сокета. Дребезг пальца на сенсорном экране может вызвать лавину дублирующих вызовов.
* **Решение:**
  1. Диспетчер действий `DeckActionDispatcher` делегирует сетевые и дисковые операции в пул потоков `QThreadPool.globalInstance()`.
  2. Результаты и индикация ошибок возвращаются в UI исключительно через сигналы `EventBus`.
  3. Внедрен аппаратный/программный антидребезг (Cooldown 250 мс на тайл).

### Инвариант 3: Тач-эргономика под экран 944×600
* **Разметка пространства:**
  * Высота рабочей зоны: 600 px.
  * Верхняя панель (Header Bar): 48 px (селектор страниц, индикатор текущего профиля, кнопка перезагрузки JSON-конфига).
  * Поле сетки кнопок (Margins 12 px): чистая область 920 × 528 px.
* **Базовая матрица: 3 строки × 5 колонок (15 клавиш):**
  * Габариты кнопки: ровно **174 × 168 px** (промежутки 12 px, радиус скругления 14 px).
  * Элементы тайла: крупная иконка 48×48 px, заголовок 13 px (Bold), подпись статуса 11 px. Оптимально по закону Фиттса под слепое нажатие пальцем.
* **Плотная матрица: 4 строки × 6 колонок (24 клавиши):**
  * Габариты кнопки: ровно **145 × 124 px** (промежутки 10 px). Режим для насыщенных макро-профилей.

### Инвариант 4: Таргетированный захват экрана (Clean Multi-DPI Screenshot)
* **Проблема:** В двухмониторной конфигурации (2560×1440 dGPU + 1024×600 iGPU) вызов стандартного захвата рабочего стола склеивает оба экрана или искажает масштаб из-за разного системного масштабирования (DPI).
* **Решение:** Модуль `core.deck.actions.screenshot` использует WinAPI `BitBlt` контекста DC первичного экрана (`GetDC(NULL)` с жесткими координатами `(0, 0, 2560, 1440)`) либо точный выбор экземпляра `QScreen` из `QApplication.screens()`, расположенного в начале координат `(0, 0)`. Изображение копируется в системный буфер `QGuiApplication.clipboard()`.

### Инвариант 5: WASAPI Endpoint Routing & COM IPolicyConfig
* **Проблема:** Windows Core Audio API (WASAPI) не содержит документированных публичных методов смены устройства воспроизведения по умолчанию в базовом интерфейсе `IMMDeviceEnumerator`.
* **Решение:** Модуль `core.deck.actions.audio_device` использует нативный COM-клиент `CPolicyConfigClient` (`CLSID {870af99c-171d-4f9e-af0d-e63df40c2bc9}`, `IID {f8679f50-850a-41cf-9c72-430f290290c8}`) с вызовом `SetDefaultEndpoint(device_id, role)` для всех трех ролей (`eConsole`, `eMultimedia`, `eCommunications`). Переключение выполняется в изолированном COM-контексте (`CoInitialize`), без сторонних бинарных утилит, поддерживая как точный Device ID, так и гибкий поиск по подстроке дружелюбного имени ("Наушники", "Динамики", "Sennheiser", "Realtek").

---

## 3. Архитектурная схема взаимодействия модулей

```mermaid
flowchart TD
    subgraph ConfigLayer ["Слой конфигурации (JSON & Pydantic)"]
        CFG["config/deck_config.json"] --> Loader["core.deck.models.DeckConfigLoader"]
        Loader --> Schema["Pydantic v2 Models (DeckRootConfig)"]
    end

    subgraph PresentationLayer ["Слой представления (UI 944x600)"]
        MainWindow["ui.main_window.MainWindow"] --> DeckTab["ui.modules.deck_view.DeckView (Tab 2)"]
        Sidebar["ui.sidebar.SidebarDock"] -.->|Tab Switch '🎛'| DeckTab

        DeckTab --> Header["HeaderBar (Профили, Статус, Reload)"]
        DeckTab --> Grid["DeckGrid (QGridLayout 3x5 / 4x6)"]
        Grid --> Buttons["DeckButtonWidget (Qt.NoFocus, Visual Haptics)"]
        
        AudioView["ui.modules.audio_view.AudioMixerView (Tab 3)"] -.->|Device Switch Sync| Header
    end

    subgraph CoreEngine ["Слой ядра (core/deck/ & core/audio_manager)"]
        Buttons -->|Touch Tap (250ms Debounce)| Dispatcher["core.deck.action_dispatcher.DeckActionDispatcher"]
        Dispatcher -->|Worker ThreadPool| Handlers["Action Handlers"]

        subgraph ActionHandlers ["Обработчики действий"]
            H_Key["hotkey.py (SendInput Scancodes)"]
            H_Dev["audio_device.py (IPolicyConfig WASAPI)"]
            H_Proc["process.py (Popen Detached CREATE_NO_WINDOW)"]
            H_Http["http_request.py (Async REST / Webhooks)"]
            H_Shot["screenshot.py (Win32 BitBlt Primary 2560x1440)"]
            H_Sys["system.py (Mic Mute, Dimmer, Lock)"]
        end
    end

    subgraph OS_Targets ["Внешняя среда и подсистемы"]
        H_Key -->|ScanCodes| ActiveApp["Активное окно (GetForegroundWindow)"]
        H_Dev -->|SetDefaultEndpoint| AudioWASAPI["Windows Audio (Наушники / Колонки)"]
        H_Proc -->|CREATE_NO_WINDOW| WindowsOS["Процессы ОС / Утилиты"]
        H_Http -->|HTTP POST/GET| ExtServices["OpenRGB / OBS / Home Assistant"]
        H_Shot -->|QClipboard| WinClip["Буфер обмена Windows"]
        H_Sys -->|AudioUtilities| AudioMgr["core.audio_manager.AudioManager"]
    end
```

---

## 4. Спецификация контрактов и моделей данных

### 4.1. Декларативная схема конфигурации (`core/deck/models.py`)

```python
from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field

ActionType = Literal[
    "hotkey",         # Симуляция клавиш (SendInput)
    "audio_device",   # Переключение аудиоустройств вывода (Наушники/Динамики)
    "launch",         # Запуск программы / скрипта
    "http_request",   # REST API запрос к сторонним программам
    "screenshot",     # Скриншот основного монитора / окна
    "system",         # Системное действие (mute mic, lock, dimmer)
    "navigation"      # Переход на страницу/папку
]

class HotkeyParams(BaseModel):
    keys: List[str]

class AudioDeviceParams(BaseModel):
    mode: Literal["toggle", "set", "cycle"] = "toggle"
    devices: List[str] = Field(default_factory=lambda: ["Наушники", "Динамики"])

class LaunchParams(BaseModel):
    path: str
    args: List[str] = Field(default_factory=list)
    working_dir: Optional[str] = None
    detached: bool = True

class HttpRequestParams(BaseModel):
    url: str
    method: Literal["GET", "POST", "PUT"] = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    json_body: Optional[Dict[str, Any]] = None
    timeout_sec: float = 1.5

class ScreenshotParams(BaseModel):
    target: Literal["primary_screen", "active_window"] = "primary_screen"
    clipboard: bool = True
    save_path: Optional[str] = None

class SystemParams(BaseModel):
    command: Literal["toggle_mic_mute", "toggle_master_mute", "lock_workstation", "toggle_dimmer"]

class NavigationParams(BaseModel):
    target_page_id: str

class AudioDeviceInfo(BaseModel):
    """Информация об аудиоустройстве вывода/ввода."""
    id: str
    name: str
    is_default: bool = False
    state: int = 1  # 1 = DEVICE_STATE_ACTIVE

class DeckActionConfig(BaseModel):
    """Типизированные параметры выполнения команды."""
    action_type: ActionType
    params: Dict[str, Any] = Field(default_factory=dict)

    def get_typed_params(self) -> Union[
        HotkeyParams, AudioDeviceParams, LaunchParams,
        HttpRequestParams, ScreenshotParams, SystemParams, NavigationParams
    ]:
        """Фабрика типизированных параметров действия."""
        mapping = {
            "hotkey": HotkeyParams,
            "audio_device": AudioDeviceParams,
            "launch": LaunchParams,
            "http_request": HttpRequestParams,
            "screenshot": ScreenshotParams,
            "system": SystemParams,
            "navigation": NavigationParams,
        }
        model_cls = mapping.get(self.action_type)
        if model_cls:
            return model_cls(**self.params)
        return self.params

class DeckButtonConfig(BaseModel):
    """Конфигурация отдельного сенсорного тайла."""
    id: str
    title: str
    icon: str                          # Символ Unicode, SVG имя или путь к PNG
    color_accent: str = "#38bdf8"       # Неоновый акцент рамки/иконки
    background_color: str = "#161b26"   # Цвет фона кнопки
    action: DeckActionConfig
    toggle_action: Optional[DeckActionConfig] = None   # Второе действие (для переключателей)
    status_source: Optional[str] = None               # Имя источника статуса в EventBus ("mic_mute", "audio_device", "dimmer")

class DeckPageConfig(BaseModel):
    """Страница кнопок (профиль или подпапка)."""
    id: str
    name: str
    grid_rows: int = 3
    grid_cols: int = 5
    buttons: List[DeckButtonConfig]

class DeckRootConfig(BaseModel):
    """Корневая конфигурация макро-панели."""
    active_profile: str = "default"
    pages: List[DeckPageConfig]

class DeckConfigLoader:
    """Безопасный загрузчик конфигурации с автоматическим fallback."""
    @staticmethod
    def load_from_file(path: str) -> DeckRootConfig:
        ...
```

### 4.2. Пример эталонного файла конфигурации (`config/deck_config.json`)

```json
{
  "active_profile": "default",
  "pages": [
    {
      "id": "default",
      "name": "Основной",
      "grid_rows": 3,
      "grid_cols": 5,
      "buttons": [
        {
          "id": "btn_toggle_audio_device",
          "title": "Аудиовыход",
          "icon": "🎧",
          "color_accent": "#06b6d4",
          "status_source": "audio_device",
          "action": {
            "action_type": "audio_device",
            "params": {
              "mode": "toggle",
              "devices": ["Наушники", "Динамики"]
            }
          }
        },
        {
          "id": "btn_mute_mic",
          "title": "Микрофон",
          "icon": "🎙",
          "color_accent": "#ef4444",
          "status_source": "mic_mute",
          "action": {
            "action_type": "system",
            "params": { "command": "toggle_mic_mute" }
          }
        },
        {
          "id": "btn_screenshot_primary",
          "title": "Скриншот",
          "icon": "📸",
          "color_accent": "#38bdf8",
          "action": {
            "action_type": "screenshot",
            "params": { "target": "primary_screen", "clipboard": true }
          }
        },
        {
          "id": "btn_discord_deafen",
          "title": "Discord Deafen",
          "icon": "🎧",
          "color_accent": "#818cf8",
          "action": {
            "action_type": "hotkey",
            "params": { "keys": ["ctrl", "shift", "d"] }
          }
        },
        {
          "id": "btn_obs_record",
          "title": "OBS Запись",
          "icon": "⏺",
          "color_accent": "#dc2626",
          "action": {
            "action_type": "hotkey",
            "params": { "keys": ["ctrl", "f9"] }
          }
        },
        {
          "id": "btn_openrgb_red",
          "title": "RGB Red Alert",
          "icon": "💡",
          "color_accent": "#f43f5e",
          "action": {
            "action_type": "http_request",
            "params": {
              "url": "http://127.0.0.1:6742/api/profiles/RedAlert/load",
              "method": "POST"
            }
          }
        },
        {
          "id": "btn_launch_terminal",
          "title": "Терминал",
          "icon": "💻",
          "color_accent": "#10b981",
          "action": {
            "action_type": "launch",
            "params": { "path": "wt.exe", "args": [] }
          }
        },
        {
          "id": "btn_toggle_dimmer",
          "title": "Ночной режим",
          "icon": "🌙",
          "color_accent": "#a855f7",
          "status_source": "dimmer",
          "action": {
            "action_type": "system",
            "params": { "command": "toggle_dimmer" }
          }
        },
        {
          "id": "btn_lock_pc",
          "title": "Заблокировать",
          "icon": "🔒",
          "color_accent": "#f59e0b",
          "action": {
            "action_type": "system",
            "params": { "command": "lock_workstation" }
          }
        }
      ]
    }
  ]
}
```

---

## 5. Поэтапный план реализации (Спринт 5: DuckDeck)

### Матрица ответственности (RACI)

| Компонент / Задача | Ответственный (R) | Утверждающий (A) | Консультант (C) | Наблюдатель (I) |
| :--- | :--- | :--- | :--- | :--- |
| **Pydantic схемы и Диспетчер I/O** | `@fullstack-builder` | `@deep-researcher` | `@code-review` | Пользователь |
| **Win32 SendInput & Скриншоты** | `@fullstack-builder` | `@deep-researcher` | `@bug-hunter` | Пользователь |
| **Переключатель аудиоустройств (`IPolicyConfig`)** | `@fullstack-builder` | `@deep-researcher` | `@code-review` | Пользователь |
| **Сенсорный UI виджет `DeckView` & Live Tiles** | `@frontend-ui-designer` | `@deep-researcher` | `@ui-creator` | Пользователь |
| **Интеграция в `main_window`, Сайдбар и Микшер** | `@fullstack-builder` | `@deep-researcher` | `@code-review` | Пользователь |
| **Pre-Flight аудит и Релиз v0.2.0** | `@code-review` | `@git-release-master`| `@bug-hunter` | Пользователь |

---

### Этап 5.1: Ядро системы действий и диспетчер (Core Engine)

- [ ] **5.1.1.** Создать модуль контрактов `core/deck/models.py`:
  - Pydantic v2 схемы `DeckRootConfig`, `DeckPageConfig`, `DeckButtonConfig`, `DeckActionConfig`.
  - Модели типизированных параметров (`HotkeyParams`, `AudioDeviceParams`, `LaunchParams`, `HttpRequestParams`, `ScreenshotParams`, `SystemParams`, `NavigationParams`).
  - Модель информации об аудиоустройстве `AudioDeviceInfo` (`id: str`, `name: str`, `is_default: bool = False`, `state: int = 1`).
  - Метод `DeckActionConfig.get_typed_params()` для полиморфной валидации словаря параметров в конкретную Pydantic-модель.
  - Загрузчик конфигурации `DeckConfigLoader`: чтение JSON, валидация по `DeckRootConfig` с graceful fallback на встроенный дефолтный профиль при ошибках парсинга.
- [ ] **5.1.2.** Реализовать транслятор горячих клавиш `core/deck/actions/hotkey_sender.py`:
  - Словарь сопоставления строковых названий клавиш (`"ctrl"`, `"alt"`, `"shift"`, `"win"`, `"f13"`, `"volup"`, `"esc"` и др.) в виртуальные коды `VK_*` (`win32con`).
  - Преобразование виртуальных кодов в аппаратные скан-коды через WinAPI `MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)`.
  - Поддержка флага `KEYEVENTF_EXTENDEDKEY` для стрелок, клавиш навигации (Del, Home, End, PgUp, PgDn) и правых модификаторов.
  - Порядок симуляции ввода: нажатие в прямом порядке (`Down -> Down`), отпускание строго в обратном (LIFO: `Up -> Up`).
  - Проверка активного окна и восстановление фокуса целевого процесса через `FocusGuardian.last_primary_hwnd` с задержкой 15–20 мс перед отправкой ввода.
  - Гарантированная очистка модификаторов (`Ctrl`, `Shift`, `Alt`, `Win`) через `finally`.
- [ ] **5.1.3.** Реализовать модуль переключения аудиоустройств `core/deck/actions/audio_device_switcher.py`:
  - Объявление COM-интерфейса `IPolicyConfig` (`CLSID {870af99c-171d-4f9e-af0d-e63df40c2bc9}`, `IID {f8679f50-850a-41cf-9c72-430f290290c8}`) в `comtypes` с точной таблицей виртуальных методов vtable:
    `GetMixFormat`, `GetDeviceFormat`, `ResetDeviceFormat`, `SetDeviceFormat`, `GetProcessingPeriod`, `SetProcessingPeriod`, `GetShareMode`, `SetShareMode`, `GetPropertyValue`, `SetPropertyValue`, `SetDefaultEndpoint`, `SetEndpointVisibility`.
  - Извлечение FriendlyName аудиоустройств через `device.OpenPropertyStore(STGM_READ)` и свойство `PKEY_Device_FriendlyName` (`{a45c254e-df1c-4efd-8020-67d146a850e0}, 14`).
  - Получение списка активных аудиоустройств вывода через `AudioUtilities.GetAllDevices()`.
  - Определение текущего устройства по умолчанию через `AudioUtilities.GetSpeakers()`.
  - Метод `switch_default_device(device_id: str) -> bool` с установкой ролей `eConsole (0)`, `eMultimedia (1)`, `eCommunications (2)` в изолированном COM-контексте (`CoInitialize`/`CoUninitialize`).
  - Метод `toggle_audio_device(targets: List[str]) -> AudioDeviceInfo` для циклического переключения между списком ключевых слов ("Наушники", "Динамики", "Sennheiser" и др.).
- [ ] **5.1.4.** Расширить фасад `core/audio_manager.py`:
  - Интегрировать функции получения и переключения дефолтных устройств воспроизведения со сбросом кэша `self._speakers` и повторным запросом `AudioUtilities.GetSpeakers()` для актуализации мастер-громкости.
  - Добавить методы управления микрофоном через endpoint захвата `AudioUtilities.GetDeviceEnumerator().GetDefaultAudioEndpoint(eCapture, eConsole)`: `is_mic_muted() -> bool`, `set_mic_mute(mute: bool)`, `toggle_mic_mute() -> bool`.
  - Расширить `core/event_bus.py` новыми сигналами:
    - `playback_device_changed = Signal(str, str)` (device_name, device_id).
    - `mic_mute_changed = Signal(bool)` (is_muted).
- [ ] **5.1.5.** Реализовать безопасный модуль скриншотов `core/deck/actions/screen_capture.py`:
  - Захват первичного монитора (2560×1440) по геометрии экрана с координатами `(0, 0)` через Win32 `BitBlt` DC экрана или `QScreen.grabWindow(0)` без искажения DPI и без захвата 7" экрана.
  - Гарантия потокобезопасности: запись в системный буфер `QClipboard` выполняется строго в главном потоке GUI (через сигнал или `QMetaObject.invokeMethod`).
- [ ] **5.1.6.** Реализовать модуль запуска процессов `core/deck/actions/process_launcher.py`:
  - Запуск через `subprocess.Popen` с флагами detachment (`CREATE_NO_WINDOW | DETACHED_PROCESS`).
  - Отвязка дескрипторов ввода/вывода (`stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`) во избежание блокировок.
  - Поддержка развертывания переменных окружения (`os.path.expandvars`) и открытия URL-протоколов (например `discord://`, `https://`).
- [ ] **5.1.7.** Реализовать асинхронный HTTP-клиент `core/deck/actions/http_client.py`:
  - Запросы к REST API сторонних программ (OpenRGB, Home Assistant, OBS REST) через стандартную библиотеку `urllib.request` с таймаутом сокета 1.5 с (без раздувания зависимостей).
  - Подавление сетевых исключений (`URLError`, `TimeoutError`) с возвратом структурированного статуса ошибки без фриза UI.
- [ ] **5.1.8.** Реализовать диспетчер `core/deck/action_dispatcher.py`:
  - Выполнение I/O задач в пуле потоков `QThreadPool.globalInstance()`.
  - Архитектура передачи результатов: класс `QRunnable` со вспомогательным объектом сигналов `WorkerSignals(QObject)` для возврата данных в Main GUI Thread.
  - Потокобезопасный антидребезг (cooldown 250 мс на кнопку по `button_id`).
  - Эмиссия результатов через `EventBus`.
- [ ] **5.1.9.** Покрыть модули ядра тестами в `tests/unit/test_deck_actions.py` и `tests/unit/test_audio_device_switcher.py`:
  - 100% изоляция системных вызовов через `unittest.mock` (`SendInput`, `IPolicyConfig`, `AudioUtilities`, сокеты `urllib.request`, `QClipboard`).

#### Запуск шагов [5.1.1 - 5.1.9]:
```text
@fullstack-builder реализуй Этап 5.1 ядра макро-панели DuckDeck и модуль переключения аудиоустройств:
1. Создай Pydantic v2 модели в core/deck/models.py (DeckRootConfig, AudioDeviceInfo, get_typed_params, DeckConfigLoader).
2. Реализуй core/deck/actions/audio_device_switcher.py на базе comtypes IPolicyConfig (vtable Windows 10/11, PKEY_Device_FriendlyName, CoInitialize) и интеграцию в core/audio_manager.py (переключение наушники/колонки со сбросом кэша speakers + toggle_mic_mute через eCapture).
3. Добавь сигналы playback_device_changed и mic_mute_changed в core/event_bus.py.
4. Реализуй hotkey_sender.py (словарь VK_*, SendInput скан-коды + EXTENDEDKEY, LIFO up, задержка фокуса 20 мс), screen_capture.py (Primary 2560x1440, QClipboard в GUI thread), process_launcher.py (CREATE_NO_WINDOW, DEVNULL, expandvars), http_client.py (urllib.request, timeout 1.5s).
5. Реализуй диспетчер core/deck/action_dispatcher.py на базе QThreadPool и QRunnable + WorkerSignals с антидребезгом 250 мс.
6. Напиши юнит-тесты с изоляцией WinAPI через unittest.mock в tests/unit/test_deck_actions.py и tests/unit/test_audio_device_switcher.py.
Критерий завершения: 100% PASS тестов ядра DuckDeck.

#### Pre-Flight проверка:
@code-review проведи аудит реализации Этапа 5.1:
Проверь точность vtable IPolicyConfig во избежание Access Violation, потокобезопасность CoInitialize в QThreadPool, вызов QClipboard строго в GUI thread, корректность скан-кодов WinAPI и изоляцию фокуса.
```

---

### Этап 5.2: Сенсорный UI виджет и эргономичная сетка (Presentation Layer)

- [ ] **5.2.1.** Создать базовый компонент сенсорного тайла `DeckButtonWidget` в `ui/modules/deck_view.py`:
  - Базовый класс `QFrame`, инварианты `Qt.NoFocus` и `Qt.WA_AcceptTouchEvents`.
  - Точные габариты под геометрию экрана 944×600:
    - Сетка 3×5: фиксированный размер **174×168 px**, скругление 14 px.
    - Сетка 4×6: фиксированный размер **143×123 px**, скругление 10 px.
  - Компоновка внутри тайла (`QVBoxLayout` с отступами 8 px):
    - Верх: крупная иконка (`QLabel` с Unicode/SVG, размер 36–42 px, по центру).
    - Середина: заголовок тайла (`QLabel`, 12–13 px Bold, перенос строк, цвет `#e2e8f0`).
    - Низ: строка статуса/подписи (`QLabel`, 10 px, цвет `#94a3b8`, скрывается, если пуста).
  - Управление состояниями через динамические свойства `setProperty("state", ...)` без использования залипающего `:hover`:
    - `idle`: базовый фон `#161b26`, граница `#232b3e`.
    - `pressed`: сдвиг содержимого на 2 px вниз (`_content_offset`), фон затемняется на 15%.
    - `executing`: неоновый пульс границы через таймер/`QVariantAnimation` (цвет `color_accent`).
    - `success`: кратковременная изумрудная вспышка границы (`#10b981`, 600 мс).
    - `error`: рубиновая индикация (`#ef4444`, 800 мс) со сдвигом внутреннего смещения `_content_offset` (шейк содержимого без изменения геометрии в layout).
  - Сигнал нажатия: `triggered = Signal(DeckButtonConfig)`.
- [ ] **5.2.2.** Создать контейнер сетки `DeckGrid(QWidget)`:
  - Компоновщик `QGridLayout` с `setContentsMargins(12, 12, 12, 12)` и `setSpacing(12)`.
  - Метод `load_page(page_config: DeckPageConfig)`:
    - Очистка предыдущих виджетов без утечек памяти (`deleteLater()`).
    - Размещение кнопок по формуле `row = idx // cols`, `col = idx % cols`.
    - Поддержка распорок `QSpacerItem` для незаполненных ячеек сетки.
- [ ] **5.2.3.** Реализовать компонент верхней панели `HeaderBar(QFrame)` (высота 48 px):
  - Горизонтальная компоновка `QHBoxLayout` с отступами `(12, 4, 12, 4)`.
  - Левая часть: полоса сенсорных кнопок-пилюль страниц/профилей (`QPushButton` с `Qt.NoFocus`, скругление 16 px, индикатор активной вкладки).
  - Центр: текстовый индикатор фонового статуса (`QLabel`, 11 px, плавно угасающий статус «OBS: Запись включена», «Аудио: Наушники»).
  - Правая часть: кнопка быстрой перезагрузки JSON (`🔄`, 36×36 px, `Qt.NoFocus`).
  - Сигналы: `page_selected = Signal(str)` (page_id), `reload_requested = Signal()`.
- [ ] **5.2.4.** Реализовать главный контейнер `DeckView(QWidget)`:
  - Вертикальная компоновка `QVBoxLayout`: `HeaderBar` (48 px) + `DeckGrid` (552 px).
  - Интеграция с `ActionDispatcher`:
    - Перехват сигнала `button.triggered` → вызов `dispatcher.dispatch(action_config)`.
    - Перехват ответов `dispatcher.action_finished` → перевод соответствующей кнопки в состояние `success` или `error`.
  - Централизованная реактивность Live Dynamic Tiles:
    - Подписка на сигналы `bus.playback_device_changed`, `bus.mic_mute_changed`, `bus.dimmer_changed`.
    - Маршрутизация обновления в кнопки текущей страницы по совпадению `button_config.status_source`.
  - Метод `reload_config()`: безопасная перезагрузка `config/deck_config.json` с откатом на дефолт при ошибке.
- [ ] **5.2.5.** Создать эталонный конфигурационный файл `config/deck_config.json`:
  - Профиль `default` (сетка 3×5) с преднастроенными действиями:
    1. Переключатель аудиовыхода (Live Tile, `🎧/🔊`).
    2. Переключатель микрофона (Live Tile, `🎙/🔇`).
    3. Первичный скриншот 2560×1440 (`📸`).
    4. Discord Deafen (`Ctrl+Shift+D`).
    5. OBS Запись (`Ctrl+F9`).
    6. RGB Alert (HTTP POST).
    7. Терминал (`wt.exe`).
    8. Ночной режим (`DimmerOverlay`).
    9. Блокировка ПК (`LockWorkstation`).
- [ ] **5.2.6.** Написать компонентные UI-тесты в `tests/unit/test_deck_view.py`:
  - Проверка инварианта: 100% дочерних кнопок и вкладок имеют `focusPolicy() == Qt.NoFocus`.
  - Проверка точной геометрии: размеры тайлов строго 174×168 px (3×5) и 143×123 px (4×6).
  - Тест динамических тайлов: эмиссия сигнала `bus.playback_device_changed` меняет текст и иконку целевой кнопки.
  - Тест переключения страниц и перезагрузки конфига.

#### Запуск шагов [5.2.1 - 5.2.6]:
```text
@frontend-ui-designer реализуй интерфейс сенсорной панели DuckDeck:
1. Создай ui/modules/deck_view.py с компонентами DeckView, DeckGrid, DeckButtonWidget и HeaderBar.
2. Примени точную геометрию под экран 944x600 (тайлы 174x168 px для 3x5 и 143x123 px для 4x6, отступы 12 px, Qt.NoFocus).
3. Реализуй централизованную реактивность в DeckView для живых тайлов (🎧/🔊, 🎙/🔇) без утечек подписок EventBus.
4. Добавь визуальную тактильность через состояния [state="..."] (вдавливание, пульсация, шейк содержимого _content_offset без поломки QGridLayout).
5. Создай config/deck_config.json и напиши тесты в tests/unit/test_deck_view.py.
Критерий завершения: 100% PASS тестов tests/unit/test_deck_view.py.

#### Pre-Flight проверка:
@code-review проведи аудит интерфейса Этапа 5.2:
Убедись в соблюдении инварианта Qt.NoFocus на всех элементах, отсутствии залипания :hover на таче и стабильной частоте кадров 60 FPS на iGPU.
```

---

### Этап 5.3: Интеграция в DuckDock, вывод `happ.exe` и связка подсистем

- [ ] **5.3.1.** Интеграция `DeckView` в `ui/main_window.py`:
  - Заменить создание заглушки `self.page_happ` на экземпляр `self.page_deck = DeckView(parent=self)`.
  - Зарегистрировать `self.page_deck` во 2-й индекс стека: `self.workspace.addWidget(self.page_deck)`.
  - В методе `MainWindow._cleanup()` добавить гарантированное освобождение ресурсов:
    `if hasattr(self, "page_deck") and hasattr(self.page_deck, "cleanup"): self.page_deck.cleanup()`.
  - Удалить устаревший вспомогательный метод `_create_external_app_view()`.
- [ ] **5.3.2.** Обновление сайдбара в `ui/sidebar.py`:
  - Переименовать атрибут кнопки `self.btn_happ` в `self.btn_deck`.
  - Установить иконку `"🎛"` и всплывающую подсказку `"DuckDeck (Макро-панель и управление)"` для вкладки с индексом 2.
- [ ] **5.3.3.** Сенсорный переключатель аудиовыхода в `ui/modules/audio_view.py`:
  - В `header_layout` шапки микшера (слева от кнопки `btn_refresh`) добавить сенсорную кнопку `self.btn_switch_device`:
    - Высота 40 px, минимальная ширина 140 px, стиль `Qt.NoFocus`, класс `refresh-btn`.
    - Динамический текст: текущий активный аудиовыход с префиксом иконки (`🎧 Наушники` / `🔊 Динамики`).
    - Обработчик нажатия: вызов `self.audio_manager.toggle_playback_device(["Наушники", "Динамики"])`.
  - Реализовать слот `_on_playback_device_changed(self, device_name: str, device_id: str)`:
    - Обновить заголовок текущего устройства: `self.lbl_device.setText(device_name)`.
    - Обновить текст и иконку на кнопке `self.btn_switch_device`.
    - Перечитать мастер-громкость через `self._refresh_master()`.
    - Выполнить полную пересборку сессий через `self._refresh_sessions(force_rebuild=True)`.
  - Подключить сигнал `bus.playback_device_changed.connect(self._on_playback_device_changed)`.
  - В `_cleanup` / `closeEvent` микшера добавить безопасное отключение слота от шины событий.
- [ ] **5.3.4.** Очистка конфигурации в `config.json`:
  - Удалить запись стороннего процесса `happ` из массива `tracked_apps`, исключая паразитные попытки тайлинга на вкладке 2.
- [ ] **5.3.5.** Маршрутизация системных действий (`core/deck/actions/system.py` и `EventBus`):
  - Реализовать диспетчеризацию команд `action_type: "system"`:
    - `command: "toggle_dimmer"` -> `bus.dimmer_toggle_requested.emit()`.
    - `command: "toggle_mic_mute"` -> вызов `AudioManager().toggle_mic_mute()`.
    - `command: "lock_workstation"` -> `ctypes.windll.user32.LockWorkStation()`.
  - Связать `action_type: "audio_device"` с прямым вызовом `AudioManager().toggle_playback_device(targets)`.
- [ ] **5.3.6.** Сквозное регрессионное и интеграционное тестирование:
  - Создать интеграционный тест `tests/integration/test_deck_integration.py`:
    - Проверка инициализации `MainWindow` с `DeckView` на вкладке 2.
    - Проверка переключения вкладок через `bus.tab_changed.emit(2)`.
    - Проверка вызова `cleanup()` при закрытии окна.
    - Проверка синхронного обновления `AudioMixerView` при эмиссии `bus.playback_device_changed`.
  - Запустить полный тестовый набор: `pytest tests/` (100% статус `PASS`).

#### Запуск шагов [5.3.1 - 5.3.6]:
```text
@fullstack-builder проведи интеграцию DuckDeck и модуля переключения аудиоустройств в DuckDock:
1. Замени page_happ на DeckView(parent=self) в ui/main_window.py, удали _create_external_app_view и добавь self.page_deck.cleanup() в _cleanup().
2. В ui/sidebar.py переименуй self.btn_happ в self.btn_deck с иконкой '🎛' и подсказкой 'DuckDeck (Макро-панель и управление)'.
3. В ui/modules/audio_view.py добавь кнопку btn_switch_device в header_layout, подключи слот _on_playback_device_changed к bus.playback_device_changed с обновлением мастера и сессий.
4. Удали запись happ из tracked_apps в config.json.
5. Настрой маршрутизацию системных действий колоды (toggle_dimmer через EventBus, toggle_mic_mute и toggle_playback_device через AudioManager, LockWorkStation).
6. Напиши интеграционные тесты в tests/integration/test_deck_integration.py и выполни прогон pytest tests/.
Критерий завершения: 100% PASS всех тестов проекта без регрессий.

#### Pre-Flight проверка:
@code-review проведи аудит интеграции Этапа 5.3:
Проверь чистоту diff, сохранение инварианта WS_EX_NOACTIVATE корневого окна, отсутствие циклических импортов между core/deck и ui/, а также корректное освобождение ресурсов в MainWindow._cleanup().
```

---

## 6. Критерии приемки (Definition of Done)

1. **Функциональные критерии:**
   - **Переключение аудиоустройств:** Касание кнопки аудиовыхода мгновенно переключает системный вывод звука Windows между наушниками и колонками (роли Console, Multimedia, Communications), тайл на панели и кнопка в микшере мгновенно обновляют иконку (`🎧`/`🔊`) и название активного устройства.
   - **Управление микрофоном:** Касание кнопки микрофона переключает mute микрофона Windows с визуальной индикацией (`🎙`/`🔇`).
   - **Скриншот:** Нажатие на кнопку со скриншотом мгновенно помещает изображение экрана 1 (2560×1440) в буфер обмена.
   - **Хоткеи:** Нажатие на хоткей отправляет скан-коды в активное окно переднего плана без потери фокуса и без сворачивания полноэкранных окон.
   - **HTTP и запуск процессов:** HTTP-запросы и запуск скриптов выполняются в фоне, UI DuckDock не подвисает даже при задержке сети 5 сек.
2. **Архитектурные инварианты:**
   - Все элементы вкладки обладают `Qt.NoFocus` и `Qt.WA_AcceptTouchEvents`.
   - Корневое окно сохраняет расширенный стиль `WS_EX_NOACTIVATE`.
   - Модуль `IPolicyConfig` работает изолированно и не крашит процесс при отсутствии определенного аудиоустройства.
3. **Стабильность и тесты:**
   - 100% тестов в директории `tests/` завершаются со статусом `PASS`.
   - Память, дескрипторы окон и COM-объекты не утекают при многократных нажатиях и переключениях вкладок.
