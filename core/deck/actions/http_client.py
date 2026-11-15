"""
Re-export Shim для обратной совместимости.
Модуль перенесен в modules.deck.actions.http_client.
"""
import sys
import modules.deck.actions.http_client as _http

globals().update({k: v for k, v in _http.__dict__.items() if not k.startswith("__")})

sys.modules[__name__] = _http
