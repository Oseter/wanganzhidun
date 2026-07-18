# -*- mode: python ; coding: utf-8 -*-
# 网安智盾 Windows 版 — PyInstaller 打包配置
# 用法：pyinstaller build.spec
# 产物：dist/WangAnZhiDun.exe（单文件、无控制台窗口）

import os

# collect_all 是 PyInstaller.utils.hooks 的模块级函数，
# 必须在 Analysis 创建【之前】调用，把收集到的二进制/数据/隐式导入传进去。
# 错误写法 a.collect_all(pkg) 会导致 'Analysis' object has no attribute 'collect_all'。
from PyInstaller.utils.hooks import collect_all

block_cipher = None

app_name = "WangAnZhiDun"

# cryptography 的 _rust 编译模块、cv2/numpy 的二进制扩展都必须整包收集，
# 否则运行期会报 ModuleNotFoundError。
collected_binaries = []
collected_datas = []
collected_hiddenimports = [
    # winrt 通知监听（monitor.py 实际导入路径）
    "winrt.windows.ui.notifications.management",
    "winrt.windows.ui.notifications",
    # 其他纯 Python 依赖
    "pystray",
    "mss",
]

for _pkg in ("cryptography", "cv2", "numpy"):
    try:
        _bin, _dat, _imp = collect_all(_pkg)
        collected_binaries += _bin
        collected_datas += _dat
        collected_hiddenimports += _imp
        print(f"[info] collect_all({_pkg}) 成功")
    except Exception as _e:  # noqa: BLE001
        print(f"[warn] collect_all({_pkg}) 失败：{_e}")

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
