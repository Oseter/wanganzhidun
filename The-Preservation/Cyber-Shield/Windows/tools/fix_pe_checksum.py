"""PE 校验和修复：Post-build 修复 EXE 的 PE 头部校验和。

PyInstaller 从 4.6+ 已修复此问题，但手动运行确保万无一失。
有效校验和可降低部分 AV（尤其是 Defender）的误报概率。
"""
import os
import sys


def fix_checksum(exe_path: str):
    if not os.path.exists(exe_path):
        print(f"文件不存在：{exe_path}")
        return False
    try:
        import pefile
        pe = pefile.PE(exe_path)
        old = pe.OPTIONAL_HEADER.CheckSum
        pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()
        pe.write(exe_path)
        print(f"校验和：{old} → {pe.OPTIONAL_HEADER.CheckSum}")
        return True
    except ImportError:
        print("pefile 未安装，跳过校验和修复。pip install pefile")
        return False
    except Exception as e:
        print(f"校验和修复失败：{e}")
        return False


if __name__ == "__main__":
    paths = sys.argv[1:] or [
        os.path.join(os.path.dirname(__file__), "..", "dist", "WangAnZhiDun", "WangAnZhiDun.exe"),
    ]
    for p in paths:
        fix_checksum(os.path.abspath(p))
