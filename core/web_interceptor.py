"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.media.interceptor.
"""
import sys
import modules.media.interceptor as _interceptor

globals().update({k: v for k, v in _interceptor.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _interceptor
