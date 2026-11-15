"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.telemetry.history.
"""
import sys
import modules.telemetry.history as _history

globals().update({k: v for k, v in _history.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _history
