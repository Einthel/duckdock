"""
Инициализация Per-Monitor DPI Awareness V2 в Windows 10/11.
Должна вызываться до создания QApplication.
"""
import sys
import ctypes

# Значение DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 в WinUser.h: ((DPI_AWARENESS_CONTEXT)-4)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

def init_dpi_awareness() -> bool:
    """
    Установить режим Per-Monitor DPI Awareness V2 для корректной работы координат 800x600.
    Возвращает True в случае успеха, False при ошибке или на не-Windows системах.
    """
    if sys.platform != "win32":
        return False

    # 1. Попытка через user32.SetProcessDpiAwarenessContext (Windows 10 1703+)
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            result = user32.SetProcessDpiAwarenessContext(
                ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
            )
            if result:
                return True
    except Exception as e:
        print(f"[!] Предупреждение SetProcessDpiAwarenessContext: {e}")

    # 2. Fallback через shcore.SetProcessDpiAwareness (Windows 8.1 / 10 early)
    try:
        shcore = ctypes.windll.shcore
        if hasattr(shcore, "SetProcessDpiAwareness"):
            # 2 = PROCESS_PER_MONITOR_DPI_AWARE
            hr = shcore.SetProcessDpiAwareness(2)
            return hr == 0
    except Exception as e:
        print(f"[!] Предупреждение SetProcessDpiAwareness: {e}")

    # 3. Fallback через старый user32.SetProcessDPIAware (Windows Vista+)
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetProcessDPIAware"):
            return bool(user32.SetProcessDPIAware())
    except Exception as e:
        print(f"[!] Предупреждение SetProcessDPIAware: {e}")

    return False
