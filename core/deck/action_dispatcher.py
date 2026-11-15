"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.deck.action_dispatcher.
"""
import sys
import modules.deck.action_dispatcher as _dispatcher

globals().update({k: v for k, v in _dispatcher.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _dispatcher
