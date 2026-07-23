"""取证模块：截图（mss）、录屏（OBS WebSocket）、聊天记录导出。

证据统一归档至 evidence/ 事件目录。
"""
import json
import os
import time
from datetime import datetime
from typing import List, Optional, Tuple

import mss
from PIL import Image

from .logger import log


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


class OBSRecorder:
    """通过 obs-websocket 控制 OBS Studio 的录像缓冲。

    依赖：obs-websocket-py（需安装）。
    降级：obs 未运行/未配置时返回 None，不阻塞取证。
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 4455,
                 password: str = "", buffer_seconds: int = 60):
        self.host = host
        self.port = port
        self.password = password
        self.buffer_seconds = buffer_seconds
        self._ws = None
        self._available = False
        self._connect()

    def _connect(self):
        try:
            from obswebsocket import obsws, requests as obs_req
            self._ws = obsws(self.host, self.port, self.password)
            self._ws.connect()
            self._ws.call(obs_req.GetVersion())
            self._available = True
            log.info("OBS WebSocket 已连接")
        except Exception as e:
            log.info(f"OBS 不可用（降级）：{e}")
            self._available = False

    @property
    def enabled(self) -> bool:
        return self._available

    def save_replay(self, out_path: str) -> Optional[str]:
        if not self._available:
            return None
        try:
            from obswebsocket import requests as obs_req
            self._ws.call(obs_req.SaveReplayBuffer())
            time.sleep(1)
            self._ws.call(obs_req.GetReplayBufferStatus())
            return out_path
        except Exception as e:
            log.warning(f"OBS 保存回放失败：{e}")
            return None

    def disconnect(self):
        if self._ws:
            try:
                self._ws.disconnect()
            except Exception:
                pass


class EvidenceManager:
    """协调取证流程：截图 → OBS 录屏 → 归档。"""

    def __init__(self, save_path: str, config):
        self.save_path = save_path
        obs_cfg = config.obs
        self.screenshotter = Screenshotter(
            save_path, config.screenshot_format, config.max_screenshots,
        )
        self.obs = OBSRecorder(
            host=obs_cfg.get("host", "127.0.0.1"),
            port=obs_cfg.get("port", 4455),
            password=obs_cfg.get("password", ""),
            buffer_seconds=obs_cfg.get("replay_buffer_seconds", 60),
        )
        self.encrypt = config.encrypt
        self.crypto = None

    def set_crypto(self, crypto):
        self.crypto = crypto

    def collect(self, source_app: str, text: str, delay: int = 1) -> dict:
        """执行完整取证，返回证据附件字典。"""
        if delay > 0:
            time.sleep(delay)

        ts = datetime.now()
        ts_str = ts.strftime("%Y%m%d_%H%M%S")
        event_dir = os.path.join(self.save_path, f"{ts_str}_{source_app}")
        os.makedirs(event_dir, exist_ok=True)

        screenshots = self.screenshotter.capture(prefix="shot")
        saved_shots: List[str] = []
        for sp in screenshots:
            dst = os.path.join(event_dir, os.path.basename(sp))
            if os.path.exists(sp):
                os.replace(sp, dst)
                saved_shots.append(dst)

        replay_path = os.path.join(event_dir, f"replay_{ts_str}.mp4")
        replay = self.obs.save_replay(replay_path) if self.obs.enabled else None

        raw_path = os.path.join(event_dir, "raw.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(text)

        attachments = {
            "screenshots": saved_shots,
            "replay": replay,
            "raw_text": raw_path,
        }

        if self.encrypt and self.crypto and self.crypto.available:
            self._encrypt_attachments(attachments)

        return attachments

    def _encrypt_attachments(self, att: dict):
        def _enc(p):
            if os.path.exists(p) and not p.endswith(".enc"):
                try:
                    self.crypto.encrypt_file(p)
                    os.remove(p)
                    return p + ".enc"
                except Exception as e:
                    log.warning(f"加密失败 {p}: {e}")
            return p

        att["screenshots"] = [_enc(p) for p in att.get("screenshots", [])]
        if att.get("replay"):
            att["replay"] = _enc(att["replay"])
        if att.get("raw_text"):
            att["raw_text"] = _enc(att["raw_text"])
