"""反杀毒误报：收集信息并打开各厂商的误报申诉页面。

PyInstaller 打包的 exe 因启动器特征码被多家杀软误报，这是已知问题。
提交误报申诉可逐步降低检测率。运行此脚本打开各厂商申诉页面。
"""
import hashlib
import os
import platform
import sys
import webbrowser


def get_exe_info() -> dict:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base, "dist", "WangAnZhiDun", "WangAnZhiDun.exe")
    info = {
        "exe_path": exe_path,
        "exists": os.path.exists(exe_path),
        "size": 0,
        "sha256": "",
        "md5": "",
    }
    if os.path.exists(exe_path):
        data = open(exe_path, "rb").read()
        info["size"] = len(data)
        info["sha256"] = hashlib.sha256(data).hexdigest()
        info["md5"] = hashlib.md5(data).hexdigest()
    return info


SUBMIT_URLS = {
    "Microsoft Defender": "https://www.microsoft.com/en-us/wdsi/filesubmission",
    "360 安全卫士": "https://open.soft.360.cn/report.php",
    "腾讯电脑管家": "https://guanjia.qq.com/privacy/report.html",
    "火绒": "https://bbs.huorong.cn/forum-59-1.html",
    "金山毒霸": "https://www.duba.com/",
    "VirusTotal (全网检测)": "https://www.virustotal.com/gui/home/upload",
}


def main():
    info = get_exe_info()
    print("=" * 60)
    print("网安智盾 · 反杀毒误报申诉助手")
    print("=" * 60)
    print()
    if info["exists"]:
        print(f"文件：{info['exe_path']}")
        print(f"大小：{info['size'] / 1024 / 1024:.1f} MB")
        print(f"SHA256：{info['sha256']}")
        print(f"MD5：{info['md5']}")
    else:
        print("⚠ 未找到打包后的 EXE，请先执行 pyinstaller build.spec")
        print()

    print()
    print("误报原因：PyInstaller 打包的 exe 启动器具有固定特征码，")
    print("杀毒软件据此将其标记为可疑。源码全公开可审计，无毒无害。")
    print()
    print("申诉步骤：")
    print("1. 将上述 SHA256/MD5 提交给各厂商申诉")
    print("2. 说明这是 PyInstaller 打包的 Python 应用，源码开源")
    print("3. 附上 GitHub 仓库地址：https://github.com/Oseter/wanganzhidun")
    print()
    print("正在打开各厂商申诉页面...")
    print()

    for name, url in SUBMIT_URLS.items():
        print(f"  {name}：{url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass

    print()
    print("或手动提交：")
    for name, url in SUBMIT_URLS.items():
        print(f"  {name}")
        print(f"    {url}")

    # 保存信息到文件方便提交
    report_path = os.path.join(os.path.dirname(info["exe_path"]), "false_positive_report.txt") if info["exists"] else "false_positive_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"网安智盾 误报申诉信息\n")
        f.write(f"{'='*50}\n")
        f.write(f"软件名称：网安智盾 WangAnZhiDun\n")
        f.write(f"版本：v1.6.0-beta\n")
        f.write(f"源码：https://github.com/Oseter/wanganzhidun\n")
        f.write(f"说明：PyInstaller 打包的 Python 桌面应用，用于恶俗攻击防御取证\n")
        if info["exists"]:
            f.write(f"\n文件信息：\n")
            f.write(f"SHA256：{info['sha256']}\n")
            f.write(f"MD5：{info['md5']}\n")
            f.write(f"大小：{info['size']} bytes\n")
    print()
    print(f"申诉信息已保存到：{report_path}")


if __name__ == "__main__":
    main()
