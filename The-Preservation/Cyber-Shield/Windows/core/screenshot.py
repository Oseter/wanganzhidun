"""截图模块：多显示器截图，命中关键词后自动捕获当前屏幕。

使用 mss 实现高性能多屏截图；PIL 做后处理。仅截取用户自己屏幕，
不截取他人内容（红线：不爬取非授权数据）。
"""
import os
import time
from datetime import datetime
from typing import List

import mss
from PIL import Image


class Screenshotter:
    """多显示器截图器。"""

    def __init__(self, save_dir: str, fmt: str = "png", max_count: int = 3):
        self.save_dir = save_dir
        self.fmt = fmt.lower()
        self.max_count = max_count
        os.makedirs(save_dir, exist_ok=True)

    def capture(self, prefix: str = "shot") -> List[str]:
        """截取所有显示器，返回保存路径列表。"""
        paths: List[str] = []
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        with mss.mss() as sct:
            monitors = sct.monitors[1:]  # 跳过合成虚拟屏(0)
            for idx, mon in enumerate(monitors[: self.max_count], start=1):
                try:
                    shot = sct.grab(mon)
                    img = Image.frombytes("RGB", shot.size, shot.rgb)
                    fname = f"{prefix}_{ts}_m{idx}.{self.fmt}"
                    fpath = os.path.join(self.save_dir, fname)
                    if self.fmt == "jpg":
                        img.save(fpath, "JPEG", quality=85)
                    else:
                        img.save(fpath, "PNG")
                    paths.append(fpath)
                except Exception as e:
                    from .logger import log
                    log.warning(f"截图显示器 {idx} 失败：{e}")
        return paths
