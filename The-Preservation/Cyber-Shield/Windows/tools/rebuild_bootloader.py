"""重建 PyInstaller 启动器（从源码编译），降低杀软误报。

原理：PyInstaller 自带的预编译启动器（run.exe/runw.exe）
在全球所有机器上字节一致，AV 厂商将其特征码加入黑名单。
从源码重新编译后，启动器的哈希/特征码改变，误报率大幅下降。

依赖：MSYS2（UCRT64）+ GCC
  https://www.msys2.org/

用法：
  python tools/rebuild_bootloader.py
"""
import os
import shutil
import subprocess
import sys


BOOT_SRC = os.path.join(os.path.dirname(__file__), "..", "bootloader_source")
BOOT_DST = None  # 会在 find_site_packages 中设置


def find_site_packages() -> str:
    for p in sys.path:
        if p.endswith("site-packages"):
            return p
    return os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages")


def find_msys2_gcc() -> str:
    candidates = [
        r"C:\msys64\ucrt64\bin\gcc.exe",
        r"C:\msys64\mingw64\bin\gcc.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def clone_pyinstaller():
    if os.path.exists(BOOT_SRC):
        print(f"已存在：{BOOT_SRC}")
        return
    subprocess.run(
        ["git", "clone", "--depth", "1",
         "https://github.com/pyinstaller/pyinstaller.git", BOOT_SRC],
        check=True,
    )


def build_bootloader():
    gcc = find_msys2_gcc()
    if not gcc:
        print("未找到 MSYS2 GCC，请先安装 MSYS2 (https://www.msys2.org/)")
        print("安装后在 UCRT64 终端执行：pacman -S mingw-w64-ucrt-x86_64-gcc")
        return False

    clone_pyinstaller()
    os.chdir(BOOT_SRC)
    subprocess.run(
        [sys.executable, "./waf", "distclean", "all", "--target-arch=64bit"],
        check=True,
        cwd=BOOT_SRC,
    )

    src_dir = os.path.join(BOOT_SRC, "bootloader", "build")
    site_pkg = find_site_packages()
    dst_dir = os.path.join(site_pkg, "PyInstaller", "bootloader", "Windows-64bit-intel")
    print(f"目标目录：{dst_dir}")

    for f in ["run.exe", "runw.exe"]:
        src = os.path.join(src_dir, f)
        dst = os.path.join(dst_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"已覆盖：{dst}")
        else:
            print(f"未找到：{src}")
    return True


def main():
    print("PyInstaller 启动器重建工具")
    print("=" * 50)
    print()

    site_pkg = find_site_packages()
    boot_dir = os.path.join(site_pkg, "PyInstaller", "bootloader", "Windows-64bit-intel")
    print(f"PyInstaller 启动器目录：{boot_dir}")
    for f in ["run.exe", "runw.exe"]:
        fp = os.path.join(boot_dir, f)
        if os.path.exists(fp):
            import hashlib
            h = hashlib.sha256(open(fp, "rb").read()).hexdigest()[:16]
            print(f"  当前 {f}：{os.path.getsize(fp)} bytes, SHA256={h}")

    print()
    if find_msys2_gcc():
        print("MSYS2 GCC 可用")
        if input("重建启动器？(y/N): ").lower() == "y":
            build_bootloader()
    else:
        print("MSYS2 GCC 未安装。")
        print("如需降低杀软误报，请安装 MSYS2 后重试：")
        print("  1. https://www.msys2.org/")
        print("  2. UCRT64 终端：pacman -S mingw-w64-ucrt-x86_64-gcc")
        print("  3. 再次运行本脚本")


if __name__ == "__main__":
    main()
