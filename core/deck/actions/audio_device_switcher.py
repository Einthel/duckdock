"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.audio.platform.device_switcher.
"""
import sys
import modules.audio.platform.device_switcher as _dev_switcher

globals().update({k: v for k, v in _dev_switcher.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _dev_switcher
