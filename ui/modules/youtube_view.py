"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.media.view.
"""
import sys
import modules.media.view as _view

globals().update({k: v for k, v in _view.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _view
