"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.deck.models.
"""
import sys
import modules.deck.models as _models

globals().update({k: v for k, v in _models.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _models
