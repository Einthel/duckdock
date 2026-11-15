"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.deck.actions.hotkey_sender.
"""
import sys
import modules.deck.actions.hotkey_sender as _hotkey

globals().update({k: v for k, v in _hotkey.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _hotkey
