"""
Главная точка входа приложения DuckDock / TouchWM.
Запуск: python main.py
"""
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
from PySide6.QtCore import Qt

from core.config import load_config
from ui.main_window import MainWindow

def main():
    print("[*] Запуск DuckDock / TouchWM v0.1.5...")
    
    # Создание приложения Qt
    app = QApplication(sys.argv)
    app.setApplicationName("DuckDock")
    app.setOrganizationName("DuckDockOrg")

    # Загрузка конфигурации
    config = load_config()

    # Создание главного окна оболочки второго экрана (800x600)
    window = MainWindow(config)
    window.show()

    print("[+] DuckDock успешно инициализирован на вспомогательном экране!")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
