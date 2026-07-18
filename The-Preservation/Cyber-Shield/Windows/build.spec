# -*- mode: python ; coding: utf-8 -*-
# 网安智盾 Windows 版 — PyInstaller 打包配置
# 用法：pyinstaller build.spec
# 产物：dist/WangAnZhiDun.exe（单文件、无控制台窗口）

import os

block_cipher = None

app_name = "WangAnZhiDun"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("config.ini", "."),
    ],
    hiddenimports=[
        "winrt.windows.ui.notifications",
        "winsdk",
        "cv2",
        "numpy",
        "pystray",
        "mss",
        "cryptography",
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # 无控制台窗口，常驻后台
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="resources/icon.ico" if os.path.exists("resources/icon.ico") else None,
)
