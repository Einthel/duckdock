"""
Главная точка входа приложения DuckDock / TouchWM.
Запуск: python main.py
Запуск конфигуратора DuckDeck: python main.py --editor (или --deck-editor)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для надежности импортов
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 1. КРИТИЧЕСКИ ВАЖНО: Инициализация Per-Monitor DPI Awareness V2 до любых импортов Qt
from core.dpi import init_dpi_awareness
init_dpi_awareness()

# 2. Настройка Chromium флагов под легковесный рендеринг на iGPU (AMD Radeon Graphics)
# и обход детекции автоматизации WebEngine в Google Accounts
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--enable-gpu-rasterization "
    "--enable-zero-copy "
    "--disable-gpu-compositing "
    "--disable-features=UseEcoQoSForBackgroundProcess,WebGPU "
    "--disable-webgpu "
    "--disable-blink-features=AutomationControlled"
)

# 3. Импорты PySide6
from PySide6.QtWidgets import QApplication

from modules.settings.config import load_config
from ui.main_window import MainWindow


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Парсинг аргументов командной строки приложения."""
    parser = argparse.ArgumentParser(
        description="DuckDock / TouchWM Application Shell & Configurator"
    )
    parser.add_argument(
        "--editor",
        "--deck-editor",
        action="store_true",
        dest="editor",
        help="Launch DuckDeck Button & Touchbar Editor on the primary display",
    )
    return parser.parse_args(args)


def main(argv: list[str] | None = None) -> int:
    """Главная точка входа процесса DuckDock."""
    cli_args = parse_args(argv)

    # Создание приложения Qt
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("DuckDock")
    app.setOrganizationName("DuckDockOrg")

    if cli_args.editor:
        print("[*] Запуск DuckDeck Button & Touchbar Editor...")
        from modules.deck.editor.demo_data import load_demo_profile_into_window
        from modules.deck.editor.window import DeckEditorWindow

        editor_window = DeckEditorWindow()
        load_demo_profile_into_window(editor_window)
        editor_window._center_on_primary_screen()
        editor_window.show()

        print("[+] DuckDeck Editor успешно открыт на основном экране!")
        return app.exec()

    print("[*] Запуск DuckDock / TouchWM v0.4.1...")
    # Загрузка конфигурации
    config = load_config()

    # Создание главного окна оболочки второго экрана (1024x600)
    window = MainWindow(config)
    window.show()

    print("[+] DuckDock успешно инициализирован на вспомогательном экране!")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
