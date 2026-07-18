"""证据归档模块：把截图 / 录像 / 通知文本打包为标准弹药格式。

标准弹药格式（同谐命途维护）：
    目标账号 | 时间 | 违规内容 | 对应条款 | 证据附件

每条取证事件生成一个事件目录，内含：
    - meta.json     标准弹药元数据
    - shot_*.png    截图
    - replay.*      自带循环缓冲录像（MP4 或 JPEG 序列，如有）
    - raw.txt       原始通知文本
"""
import json
import os
import shutil
from datetime import datetime
from typing import List, Optional


class Archiver:
    """证据归档器。"""

    def __init__(self, root: str, encrypt: bool = True,
                 crypto=None, default_clause: str = ""):
        self.root = root
        self.encrypt = encrypt
        self.crypto = crypto
        self.default_clause = default_clause
        os.makedirs(root, exist_ok=True)

    def archive(self, app: str, text: str, screenshots: List[str],
                replay: Optional[str] = None,
                target_account: str = "待确认", clause: str = "") -> dict:
        """归档一次取证事件，返回标准弹药字典。"""
        ts = datetime.now()
        ts_str = ts.strftime("%Y%m%d_%H%M%S")
        # 事件目录：时间_来源_首关键词
        event_dir = os.path.join(self.root, f"{ts_str}_{app}")
        os.makedirs(event_dir, exist_ok=True)

        # 复制截图进事件目录
        saved_shots: List[str] = []
        for i, sp in enumerate(screenshots, 1):
            dst = os.path.join(event_dir, f"shot_{i}{os.path.splitext(sp)[1]}")
            if os.path.exists(sp):
                shutil.copy(sp, dst)
                saved_shots.append(dst)

        # 录像（MP4 文件，或降级时的 JPEG 目录）
        saved_replay = None
        if replay and os.path.exists(replay):
            dst = os.path.join(event_dir, os.path.basename(replay))
            if os.path.isdir(replay):
                shutil.copytree(replay, dst, dirs_exist_ok=True)
            else:
                shutil.copy(replay, dst)
            saved_replay = dst

        # 原始文本
        raw_path = os.path.join(event_dir, "raw.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(text)

        # 标准弹药元数据
        ammo = {
            "target_account": target_account,       # 目标账号
            "time": ts.isoformat(),                 # 时间
            "violation_content": text,              # 违规内容
            "clause": clause or self.default_clause,  # 对应条款
            "evidence_attachments": {              # 证据附件
                "screenshots": saved_shots,
                "replay": saved_replay,
                "raw_text": raw_path,
            },
            "source_app": app,
        }
        meta_path = os.path.join(event_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(ammo, f, ensure_ascii=False, indent=2)

        # 本地加密（可选）
        if self.encrypt and self.crypto:
            to_encrypt = list(saved_shots) + [raw_path, meta_path]
            # 录像为文件则加密；为目录则加密其中每个 jpg
            if saved_replay:
                if os.path.isdir(saved_replay):
                    for root, _, files in os.walk(saved_replay):
                        for fn in files:
                            to_encrypt.append(os.path.join(root, fn))
                else:
                    to_encrypt.append(saved_replay)
            for p in to_encrypt:
                if os.path.exists(p) and not p.endswith(".enc"):
                    try:
                        self.crypto.encrypt_file(p)
                        os.remove(p)
                    except Exception as e:
                        from .logger import log
                        log.warning(f"加密失败 {p}: {e}")

        return ammo
