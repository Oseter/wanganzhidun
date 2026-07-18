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

        # 标准弹药元数据（附件路径先指向明文文件）
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

        # 本地加密（可选）：加密后会删除明文原件，因此必须同步把 ammo 中的
        # 附件路径改写为加密后的 .enc 路径，保证 db / 草稿 / 邮件引用始终有效。
        # 否则 send_email 会因明文已删除而静默丢弃全部附件（历史 bug）。
        if self.encrypt and self.crypto:
            def _enc(p):
                if os.path.exists(p) and not p.endswith(".enc"):
                    try:
                        self.crypto.encrypt_file(p)
                        os.remove(p)
                        return p + ".enc"
                    except Exception as e:
                        from .logger import log
                        log.warning(f"加密失败 {p}: {e}")
                return p
            saved_shots = [_enc(p) for p in saved_shots]
            raw_path = _enc(raw_path)
            if saved_replay:
                if os.path.isdir(saved_replay):
                    for r, _, files in os.walk(saved_replay):
                        for fn in files:
                            _enc(os.path.join(r, fn))
                else:
                    saved_replay = _enc(saved_replay)
            ammo["evidence_attachments"] = {
                "screenshots": saved_shots,
                "replay": saved_replay,
                "raw_text": raw_path,
            }

        # 落盘标准弹药元数据（必须写在所有加密改写完成之后，保证 meta 与 ammo 一致）
        meta_path = os.path.join(event_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(ammo, f, ensure_ascii=False, indent=2)

        return ammo
