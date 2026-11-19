"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.deck.sound_engine.
"""
import sys
import modules.deck.sound_engine as _sound_engine

globals().update({k: v for k, v in _sound_engine.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _sound_engine
