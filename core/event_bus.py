"""
Централизованная шина событий (EventBus) для слабой связанности компонентов.
Основана на сигналах PySide6 QtCore.QObject.
"""
from typing import Any, Dict, Tuple
from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    """
    Синглтон шины событий DuckDock.
    Обеспечивает слабую связанность между UI, сервисами WinAPI и датчиками.
    """
    _instance = None

    # Навигация и переключение вкладок
    tab_changed = Signal(int)  # index страницы (0: Media, 1: Sensors, 2: External/happ, 3: Audio, 4: Showcase)

    # Управление яркостью (Dimmer)
    dimmer_opacity_changed = Signal(float)  # 0.0 - 0.95
    dimmer_toggle_requested = Signal()

    # Режим ввода текста / Stealth Focus
    input_lock_toggled = Signal(bool)  # True = lock input (disable stealth), False = stealth on

    # Телеметрия датчиков
    sensors_updated = Signal(dict)  # {"cpu_temp": 45, "gpu_temp": 50, ...}

    # Внешние окна
    external_window_tiled = Signal(str, int)  # app_name, hwnd

    # Аудиомикшер
    master_volume_changed = Signal(float, bool)  # level (0.0-1.0), is_muted
    session_volume_changed = Signal(int, float, bool)  # pid, level (0.0-1.0), is_muted
    playback_device_changed = Signal(str, str)  # device_name, device_id
    mic_mute_changed = Signal(bool)  # is_muted

    # Медиаплеер YouTube Music (Спринт 4)
    media_state_changed = Signal(dict)       # {"title": str, "artist": str, "is_playing": bool}
    media_action_requested = Signal(str)     # "toggle_play", "next", "prev"

    # Макро-колодка DuckDeck (Спринт 6)
    deck_notification = Signal(str)  # трансляция сообщений в тикер панели
    deck_page_changed = Signal(str)  # синхронизация смены активного профиля / страницы

    # События тача и фокуса
    touch_detected = Signal(int, int)  # x, y на 2-м экране
    primary_focus_lost = Signal(int)   # hwnd потерявшего фокус окна на основном экране

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()

# Глобальный экземпляр
bus = EventBus()
