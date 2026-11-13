"""
Компилятор проекта DuckDock в автономный Windows EXE.
Запуск: .\\.venv\\Scripts\\python.exe build_exe.py
"""
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_NAME = "duckdock"

def build():
    print(f"[*] Сборка автономного исполняемого файла {PROJECT_NAME}.exe (Desktop GUI)...")
    dist_dir = BASE_DIR / "dist"
    build_dir = BASE_DIR / "build"
    
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        f"--name={PROJECT_NAME}",
        "--onefile",
        "--noconfirm",
        "--clean",
        "--noconsole",
        f"--paths={BASE_DIR}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--add-data={BASE_DIR / 'config.json'};.",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=win32gui",
        "--hidden-import=win32con",
        "--hidden-import=win32api",
        "--hidden-import=win32process",
        "--hidden-import=psutil",
        "--hidden-import=pycaw",
    ]
    
    entry_point = BASE_DIR / "main.py"
    cmd.append(str(entry_point))
    
    print("[*] Выполнение PyInstaller...")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"\n[+] Сборка завершена успешно! Файл готов: dist/{PROJECT_NAME}.exe")
    else:
        print(f"\n[!] Ошибка сборки. Код возврата: {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()
