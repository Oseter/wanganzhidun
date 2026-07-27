import os
from datetime import datetime
from typing import List

import mss
from PIL import Image

from core.logger import log


class Screenshotter:
    def __init__(self, save_dir: str, fmt: str = "png", max_count: int = 3):
        self.save_dir = save_dir
        self.fmt = fmt.lower()
        self.max_count = max_count
        os.makedirs(save_dir, exist_ok=True)

    def capture(self, prefix: str = "shot") -> List[str]:
        paths: List[str] = []
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        with mss.mss() as sct:
            for idx, mon in enumerate(sct.monitors[1:], start=1):
                if idx > self.max_count:
                    break
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
                    log.warning(f"截图显示器 {idx} 失败：{e}")
        return paths
