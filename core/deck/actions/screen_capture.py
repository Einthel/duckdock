"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.deck.actions.screen_capture.
"""
import sys
import modules.deck.actions.screen_capture as _screen

globals().update({k: v for k, v in _screen.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _screen
