"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.audio.view.
"""
import sys
import modules.audio.view as _view

globals().update({k: v for k, v in _view.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _view
