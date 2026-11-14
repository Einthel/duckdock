"""
Компилятор проекта DuckDock в автономный Windows-дистрибутив (--onedir).
Создает исполняемый пакет dist/DuckDock/ и готовый zip-архив dist/DuckDock-v0.2.0.zip.

Инварианты сборки:
1. Режим --onedir со стартом <300 мс.
2. Прошивка Windows PE манифеста resources/manifest.xml (requireAdministrator + PerMonitorV2).
3. Бандлинг ресурсов: LibreHardwareMonitorLib.dll, css, js, config.json.
4. Твик реестра Windows: запись GpuPreference=1; в HKCU\\Software\\Microsoft\\DirectX\\UserGpuPreferences для изоляции на iGPU.
5. Упаковка в автономный zip-архив dist/DuckDock-v0.2.0.zip.
"""
import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_NAME = "DuckDock"
VERSION = "v0.2.0"
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
OUTPUT_DIR = DIST_DIR / PROJECT_NAME
ZIP_PATH = DIST_DIR / f"{PROJECT_NAME}-{VERSION}.zip"
MANIFEST_PATH = BASE_DIR / "resources" / "manifest.xml"


def register_igpu_preference(exe_path: Path):
    """Регистрация предпочтения iGPU в реестре Windows (DirectX UserGpuPreferences)."""
    import winreg
    key_path = r"Software\Microsoft\DirectX\UserGpuPreferences"
    exe_str = str(exe_path.resolve())
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, exe_str, 0, winreg.REG_SZ, "GpuPreference=1;")
        print(f"[✓] Реестр Windows обновлен: {exe_str} -> GpuPreference=1; (iGPU)")
    except Exception as e:
        print(f"[!] Предупреждение: Не удалось записать твик реестра GPU: {e}")


def copy_bundled_assets():
    """Копирование внешних ресурсов и конфигурации в корень каталога сборки."""
    print("[*] Копирование конфигурации и ресурсов в дистрибутив...")
    # config.json рядом с DuckDock.exe
    shutil.copy2(BASE_DIR / "config.json", OUTPUT_DIR / "config.json")

    # resources/bin/LibreHardwareMonitorLib.dll
    res_bin = OUTPUT_DIR / "resources" / "bin"
    res_bin.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        BASE_DIR / "resources" / "bin" / "LibreHardwareMonitorLib.dll",
        res_bin / "LibreHardwareMonitorLib.dll"
    )

    # resources/css
    res_css = OUTPUT_DIR / "resources" / "css"
    res_css.mkdir(parents=True, exist_ok=True)
    for f in (BASE_DIR / "resources" / "css").glob("*.*"):
        shutil.copy2(f, res_css / f.name)

    # resources/js
    res_js = OUTPUT_DIR / "resources" / "js"
    res_js.mkdir(parents=True, exist_ok=True)
    for f in (BASE_DIR / "resources" / "js").glob("*.*"):
        shutil.copy2(f, res_js / f.name)

    # Вспомогательный bat-скрипт регистрации iGPU на случай переноса папки
    bat_content = (
        "@echo off\r\n"
        "reg add \"HKCU\\Software\\Microsoft\\DirectX\\UserGpuPreferences\" "
        "/v \"%~dp0DuckDock.exe\" /t REG_SZ /d \"GpuPreference=1;\" /f\r\n"
        "echo [OK] DuckDock preference registered: iGPU (Power Saving)\r\n"
        "pause\r\n"
    )
    (OUTPUT_DIR / "register_igpu.bat").write_text(bat_content, encoding="utf-8")
    print("[✓] Ассеты успешно синхронизированы в каталог dist/DuckDock/")


def create_zip_archive():
    """Упаковка каталога сборки в zip-дистрибутив."""
    print(f"[*] Упаковка автономного архива {ZIP_PATH.name}...")
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(DIST_DIR)
                zf.write(file_path, arcname)

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"[✓] Готов автономный zip-архив: {ZIP_PATH} ({size_mb:.1f} МБ)")


def build():
    print("=" * 60)
    print(f"[*] Старт сборки автономного дистрибутива {PROJECT_NAME} ({VERSION})...")
    print("=" * 60)

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Файл манифеста не найден: {MANIFEST_PATH}")

    # Формирование аргументов PyInstaller
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        f"--name={PROJECT_NAME}",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--noconsole",
        f"--manifest={MANIFEST_PATH}",
        f"--paths={BASE_DIR}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--add-data={BASE_DIR / 'config.json'};.",
        f"--add-data={BASE_DIR / 'resources' / 'bin' / 'LibreHardwareMonitorLib.dll'};resources/bin",
        f"--add-data={BASE_DIR / 'resources' / 'css'};resources/css",
        f"--add-data={BASE_DIR / 'resources' / 'js'};resources/js",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtWebEngineWidgets",
        "--hidden-import=PySide6.QtWebEngineCore",
        "--hidden-import=PySide6.QtNetwork",
        "--hidden-import=win32gui",
        "--hidden-import=win32con",
        "--hidden-import=win32api",
        "--hidden-import=win32process",
        "--hidden-import=psutil",
        "--hidden-import=pycaw",
        "--hidden-import=comtypes",
        "--hidden-import=pydantic",
        "--hidden-import=pydantic_core",
        "--collect-all=pythonnet",
        "--collect-all=pycaw",
    ]

    entry_point = BASE_DIR / "main.py"
    cmd.append(str(entry_point))

    print("[*] Выполнение компиляции PyInstaller (--onedir)...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n[!] Ошибка PyInstaller. Код возврата: {result.returncode}")
        sys.exit(result.returncode)

    exe_file = OUTPUT_DIR / f"{PROJECT_NAME}.exe"
    if not exe_file.exists():
        print(f"\n[!] Ошибка: Исполняемый файл не найден: {exe_file}")
        sys.exit(1)

    # Дополнительная синхронизация внешних ассетов
    copy_bundled_assets()

    # Регистрация твика iGPU в реестре
    register_igpu_preference(exe_file)

    # Создание zip-архива
    create_zip_archive()

    print("\n" + "=" * 60)
    print(f"[+] Сборка {PROJECT_NAME} ({VERSION}) успешно завершена!")
    print(f"[+] Автономный каталог: {OUTPUT_DIR}")
    print(f"[+] Исполняемый файл:  {exe_file}")
    print(f"[+] ZIP-архив:          {ZIP_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    build()
