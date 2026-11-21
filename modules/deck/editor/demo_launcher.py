"""
Автономный демонстрационный лончер DuckDeck Editor (Рис. 1).
Инициализирует Per-Monitor DPI Awareness V2 до создания QApplication,
создает DeckEditorWindow, загружает эталонный демо-профиль и центрирует окно на основном экране.
"""
from __future__ import annotations

import sys

# 1. Предварительная инициализация Per-Monitor DPI Awareness V2 до импорта PySide6
try:
    from core.dpi import init_dpi_awareness
    init_dpi_awareness()
except Exception as exc:
    print(f"[!] DPI awareness warning: {exc}", file=sys.stderr)

from PySide6.QtWidgets import QApplication

from modules.deck.editor.demo_data import load_demo_profile_into_window
from modules.deck.editor.window import DeckEditorWindow


def main() -> int:
    """Точка входа автономного лончера редактора DuckDeck."""
    app = QApplication.instance() or QApplication(sys.argv)

    window = DeckEditorWindow()
    load_demo_profile_into_window(window)
    window._center_on_primary_screen()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
