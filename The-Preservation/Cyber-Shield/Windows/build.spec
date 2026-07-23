# -*- mode: python ; coding: utf-8 -*-
import os
import sys

from PyInstaller.utils.hooks import collect_all

block_cipher = None
app_name = "WangAnZhiDun"

_console = "--console" in sys.argv[1:]

collected_binaries = []
collected_datas = []
collected_hiddenimports = [
    "winrt",
    "winrt.windows.ui.notifications.management",
    "winrt.windows.ui.notifications",
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.simpledialog",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "pystray",
    "pystray._win32",
    "cryptography.fernet",
    "mss",
    "ctypes",
    "logging",
    "obswebsocket",
]

for _pkg in ("cryptography", "pystray", "mss", "obswebsocket"):
    try:
        _bin, _dat, _imp = collect_all(_pkg)
        collected_binaries += _bin
        collected_datas += _dat
        collected_hiddenimports += _imp
    except Exception:
        pass

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=collected_binaries,
    datas=[("config.ini", ".")] + collected_datas,
    hiddenimports=collected_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=_console,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="resources/icon.ico" if os.path.exists("resources/icon.ico") else None,
    version="resources/version_info.txt" if os.path.exists("resources/version_info.txt") else None,
    manifest="resources/manifest.xml" if os.path.exists("resources/manifest.xml") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)
