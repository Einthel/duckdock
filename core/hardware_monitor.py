"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.telemetry.hardware_monitor.
"""
import sys
import modules.telemetry.hardware_monitor as _hw_monitor

globals().update({k: v for k, v in _hw_monitor.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _hw_monitor
