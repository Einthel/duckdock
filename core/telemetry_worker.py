"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.telemetry.worker.
"""
import sys
import modules.telemetry.worker as _worker

globals().update({k: v for k, v in _worker.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _worker
