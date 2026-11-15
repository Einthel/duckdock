"""
Обработчики действий DuckDeck.
"""
from modules.deck.actions.hotkey_sender import resolve_vk, send_hotkey
from modules.deck.actions.http_client import execute_http_request
from modules.deck.actions.process_launcher import launch_process
from modules.deck.actions.screen_capture import capture_screen, copy_pixmap_to_clipboard, get_primary_screen

__all__ = [
    "send_hotkey",
    "resolve_vk",
    "launch_process",
    "execute_http_request",
    "capture_screen",
    "copy_pixmap_to_clipboard",
    "get_primary_screen",
]
