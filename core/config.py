"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.settings.config.
"""
import sys
import modules.settings.config as _config

globals().update({k: v for k, v in _config.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _config
