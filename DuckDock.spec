# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('D:/Projects_X/duckdock/config.json', '.'),
    ('D:/Projects_X/duckdock/config/deck_config.json', 'config'),
    ('D:/Projects_X/duckdock/resources/bin/LibreHardwareMonitorLib.dll', 'resources/bin'),
    ('D:/Projects_X/duckdock/resources/css', 'resources/css'),
    ('D:/Projects_X/duckdock/resources/js', 'resources/js'),
    ('D:/Projects_X/duckdock/resources/deck', 'resources/deck'),
]
binaries = []
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
    'PySide6.QtNetwork',
    'PySide6.QtMultimedia',
    'win32gui',
    'win32con',
    'win32api',
    'win32process',
    'psutil',
    'pycaw',
    'comtypes',
    'pydantic',
    'pydantic_core',
]
tmp_ret = collect_all('pythonnet')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pycaw')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['D:/Projects_X/duckdock/main.py'],
    pathex=['D:/Projects_X/duckdock'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DuckDock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest='D:/Projects_X/duckdock/resources/manifest.xml',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DuckDock',
)
