"""
Модуль симуляции аппаратного ввода клавиатуры (SendInput Scancodes).
Обеспечивает передачу хоткеев в активное приложение на основном экране
с сохранением фокуса (Stealth Focus Guardian) и гарантированным LIFO-отпусканием клавиш.
"""
import ctypes
from ctypes import wintypes
import logging
import time
from typing import Dict, List, Optional, Set

from core.focus_guardian import FocusGuardian

logger = logging.getLogger("duckdock.deck.hotkey")

try:
    import win32con
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    win32con = None
    win32gui = None

# Константы WinAPI SendInput
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0


# Структуры ctypes для SendInput
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION),
    ]


# Таблица сопоставления строковых имен клавиш в виртуальные коды VK_*
VK_MAPPING: Dict[str, int] = {
    # Модификаторы
    "ctrl": 0x11,        # VK_CONTROL
    "control": 0x11,
    "lctrl": 0xA2,       # VK_LCONTROL
    "rctrl": 0xA3,       # VK_RCONTROL
    "alt": 0x12,         # VK_MENU
    "lalt": 0xA4,        # VK_LMENU
    "ralt": 0xA5,        # VK_RMENU
    "shift": 0x10,       # VK_SHIFT
    "lshift": 0xA0,      # VK_LSHIFT
    "rshift": 0xA1,      # VK_RSHIFT
    "win": 0x5B,         # VK_LWIN
    "windows": 0x5B,
    "lwin": 0x5B,
    "rwin": 0x5C,        # VK_RWIN
    "cmd": 0x5B,
    "super": 0x5B,
    "apps": 0x5D,        # VK_APPS

    # Базовые управляющие клавиши
    "enter": 0x0D,       # VK_RETURN
    "return": 0x0D,
    "esc": 0x1B,         # VK_ESCAPE
    "escape": 0x1B,
    "tab": 0x09,         # VK_TAB
    "space": 0x20,       # VK_SPACE
    "backspace": 0x08,   # VK_BACK
    "delete": 0x2E,      # VK_DELETE
    "del": 0x2E,
    "insert": 0x2D,      # VK_INSERT
    "ins": 0x2D,
    "capslock": 0x14,    # VK_CAPITAL
    "numlock": 0x90,     # VK_NUMLOCK
    "scrolllock": 0x91,  # VK_SCROLL
    "pause": 0x13,       # VK_PAUSE
    "printscreen": 0x2C, # VK_SNAPSHOT
    "prtsc": 0x2C,

    # Навигация
    "home": 0x24,        # VK_HOME
    "end": 0x23,         # VK_END
    "pageup": 0x21,      # VK_PRIOR
    "pgup": 0x21,
    "pagedown": 0x22,    # VK_NEXT
    "pgdn": 0x22,
    "up": 0x26,          # VK_UP
    "down": 0x28,        # VK_DOWN
    "left": 0x25,        # VK_LEFT
    "right": 0x27,       # VK_RIGHT

    # Медиа и громкость
    "volup": 0xAF,       # VK_VOLUME_UP
    "volume_up": 0xAF,
    "voldown": 0xAE,     # VK_VOLUME_DOWN
    "volume_down": 0xAE,
    "volmute": 0xAD,     # VK_VOLUME_MUTE
    "volume_mute": 0xAD,
    "media_play_pause": 0xB3,
    "play_pause": 0xB3,
    "media_stop": 0xB2,
    "media_next": 0xB0,
    "media_next_track": 0xB0,
    "media_prev": 0xB1,
    "media_prev_track": 0xB1,
}

# Добавляем функциональные клавиши F1 - F24 (0x70 - 0x87)
for i in range(1, 25):
    VK_MAPPING[f"f{i}"] = 0x70 + (i - 1)

# Добавляем буквенные клавиши A-Z (0x41 - 0x5A)
for char_code in range(ord('a'), ord('z') + 1):
    VK_MAPPING[chr(char_code)] = ord(chr(char_code).upper())

# Добавляем цифры 0-9 (0x30 - 0x39)
for digit in range(10):
    VK_MAPPING[str(digit)] = 0x30 + digit
    VK_MAPPING[f"num{digit}"] = 0x60 + digit
    VK_MAPPING[f"numpad{digit}"] = 0x60 + digit

# Набор клавиш, требующих флаг KEYEVENTF_EXTENDEDKEY
EXTENDED_KEYS: Set[int] = {
    0x21,  # VK_PRIOR
    0x22,  # VK_NEXT
    0x23,  # VK_END
    0x24,  # VK_HOME
    0x25,  # VK_LEFT
    0x26,  # VK_UP
    0x27,  # VK_RIGHT
    0x28,  # VK_DOWN
    0x2D,  # VK_INSERT
    0x2E,  # VK_DELETE
    0x5B,  # VK_LWIN
    0x5C,  # VK_RWIN
    0x5D,  # VK_APPS
    0xA3,  # VK_RCONTROL
    0xA5,  # VK_RMENU
    0x6F,  # VK_DIVIDE
    0x90,  # VK_NUMLOCK
    0xAD,  # VK_VOLUME_MUTE
    0xAE,  # VK_VOLUME_DOWN
    0xAF,  # VK_VOLUME_UP
    0xB0,  # VK_MEDIA_NEXT_TRACK
    0xB1,  # VK_MEDIA_PREV_TRACK
    0xB2,  # VK_MEDIA_STOP
    0xB3,  # VK_MEDIA_PLAY_PAUSE
}

# Базовые модификаторы для аварийной очистки
MODIFIER_VKS: Set[int] = {0x10, 0x11, 0x12, 0x5B, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5C}


def resolve_vk(key_name: str) -> Optional[int]:
    """Разрешает строковое название клавиши в виртуальный код VK."""
    normalized = key_name.strip().lower()
    return VK_MAPPING.get(normalized)


def _send_key_event(user32, vk: int, is_up: bool = False) -> None:
    """Отправляет одно нажатие или отпускание через WinAPI SendInput со скан-кодом."""
    scancode = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    flags = KEYEVENTF_SCANCODE
    if is_up:
        flags |= KEYEVENTF_KEYUP
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = 0  # При использовании KEYEVENTF_SCANCODE wVk рекомендуется устанавливать в 0
    inp.ki.wScan = scancode
    inp.ki.dwFlags = flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = 0

    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_hotkey(
    keys: List[str],
    restore_focus: bool = True,
    focus_delay_sec: float = 0.02,
) -> bool:
    """
    Симулирует нажатие комбинации клавиш через WinAPI SendInput с аппаратными скан-кодами.
    - Перед вводом проверяет и восстанавливает фокус целевого окна через FocusGuardian.
    - Клавиши зажимаются в прямом порядке (keys[0] -> keys[1]...).
    - В блоке finally гарантированно отпускаются в обратном порядке (LIFO).
    """
    if not keys:
        return False

    vks = []
    for k in keys:
        vk = resolve_vk(k)
        if vk is None:
            logger.warning(f"Неизвестная клавиша: '{k}'. Пропуск хоткея.")
            return False
        vks.append(vk)

    # Проверка и восстановление фокуса на основном мониторе
    if restore_focus and HAS_WIN32:
        try:
            fg = FocusGuardian.get_instance()
            if fg and fg.last_primary_hwnd:
                curr_fore = win32gui.GetForegroundWindow()
                if curr_fore != fg.last_primary_hwnd or fg.is_subscreen_window(curr_fore):
                    fg.restore_focus_to_primary(delay=False)
                    if focus_delay_sec > 0:
                        time.sleep(focus_delay_sec)
        except Exception as focus_err:
            logger.debug(f"Ошибка проверки фокуса перед SendInput: {focus_err}")

    user32 = ctypes.windll.user32
    pressed_vks: List[int] = []

    try:
        # Нажатие клавиш в прямом порядке
        for vk in vks:
            _send_key_event(user32, vk, is_up=False)
            pressed_vks.append(vk)
            time.sleep(0.005)  # 5 мс интервал между клавишами комбинации

        time.sleep(0.015)  # 15 мс удержание полной комбинации
        return True

    except Exception as e:
        logger.error(f"Ошибка при симуляции хоткея {keys}: {e}")
        return False

    finally:
        # Гарантированное LIFO-отпускание зажатых клавиш
        for vk in reversed(pressed_vks):
            try:
                _send_key_event(user32, vk, is_up=True)
            except Exception:
                pass

        # Аварийная очистка модификаторов, если они были среди переданных клавиш
        for vk in pressed_vks:
            if vk in MODIFIER_VKS:
                try:
                    _send_key_event(user32, vk, is_up=True)
                except Exception:
                    pass


__all__ = [
    "VK_MAPPING",
    "EXTENDED_KEYS",
    "MODIFIER_VKS",
    "KEYBDINPUT",
    "HARDWAREINPUT",
    "MOUSEINPUT",
    "INPUT",
    "INPUT_KEYBOARD",
    "KEYEVENTF_EXTENDEDKEY",
    "KEYEVENTF_KEYUP",
    "KEYEVENTF_SCANCODE",
    "MAPVK_VK_TO_VSC",
    "resolve_vk",
    "_send_key_event",
    "send_hotkey",
]
