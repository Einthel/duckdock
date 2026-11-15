"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.deck.actions.process_launcher.
"""
import sys
import modules.deck.actions.process_launcher as _launcher

globals().update({k: v for k, v in _launcher.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _launcher
