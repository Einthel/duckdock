"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.audio.service.
"""
import sys
import modules.audio.service as _service

globals().update({k: v for k, v in _service.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _service
