"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.media.web_profile.
"""
import sys
import modules.media.web_profile as _web_profile

globals().update({k: v for k, v in _web_profile.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _web_profile
