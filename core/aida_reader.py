"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.telemetry.aida_reader.
"""
import sys
import modules.telemetry.aida_reader as _aida_reader

globals().update({k: v for k, v in _aida_reader.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _aida_reader
