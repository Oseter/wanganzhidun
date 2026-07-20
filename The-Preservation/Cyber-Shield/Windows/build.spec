# -*- mode: python ; coding: utf-8 -*-
# 网安智盾 Windows 版 — PyInstaller 打包配置
# 用法：pyinstaller build.spec
# 产物：dist/WangAnZhiDun/ 目录（onedir，含 WangAnZhiDun.exe）
#
# 杀软降级（去威胁）要点：
#   1. upx=False        —— UPX 压缩包被大量 AV 直接判恶意，必须关
#   2. manifest         —— requestedExecutionLevel=asInvoker，不请求提权
#   3. version          —— 填公司/版本/版权，匿名 exe 更易被拦
#   4. onedir           —— 单文件要在 temp 解包，触发更多启发式；目录版更干净
#   5. 代码签名         —— 见 sign.ps1；签 Authenticode 是消除 SmartScreen/Edge 红框的唯一办法

import os

from PyInstaller.utils.hooks import collect_all

block_cipher = None

app_name = "WangAnZhiDun"

# cryptography 的 _rust 模块、opencv/numpy 的二进制扩展、pystray 后端都必须整包收集，
# 否则运行期会报 ModuleNotFoundError（UI 线程静默崩溃 → 表现为「窗口没弹出来」）。
collected_binaries = []
collected_datas = []
collected_hiddenimports = [
    # winrt 通知监听（monitor.py 实际导入路径）
    "winrt.windows.ui.notifications.management",
    "winrt.windows.ui.notifications",
    # tkinter GUI（主窗口/配置窗/确认弹窗）
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.simpledialog",
    # 图标绘制 — 打包时必须显式声明
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    # pystray 后端（Windows 需要 win32api）
    "pystray",
    "pystray._win32",
    # 截图
    "mss",
]

# 注意：CI 的 Windows 控制台是 cp1252，print 中文会因 UnicodeEncodeError 直接崩 spec，
# 所以这里的诊断信息只用 ASCII（源码里的中文注释不会输出，无影响）。
for _pkg in ("cryptography", "cv2", "numpy", "pystray"):
    try:
        _bin, _dat, _imp = collect_all(_pkg)
        collected_binaries += _bin
        collected_datas += _dat
        collected_hiddenimports += _imp
        print(f"[info] collect_all({_pkg}) OK")
    except Exception as _e:  # noqa: BLE001
        print(f"[warn] collect_all({_pkg}) failed: {_e}")

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

# onedir：exe 与其依赖同目录，运行期不再往 temp 解包（单文件的典型 AV 触发点）
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # 关键：关掉 UPX，砍掉大部分误报
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # 无控制台窗口，常驻后台
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,   # Windows 用 sign.ps1 的 signtool 在构建后签名
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
