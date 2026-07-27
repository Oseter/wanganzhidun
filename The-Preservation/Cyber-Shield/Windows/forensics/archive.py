import os
import time
from datetime import datetime
from typing import List, Optional

from core.logger import log
from forensics.screenshot import Screenshotter
from forensics.screen_record import OBSRecorder
from forensics.chat_export import export_raw_text
from forensics.metadata_gen import write_metadata


class EvidenceManager:
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

    def collect(self, source_app: str, text: str, delay: int = 1,
                kind: str = "forensics") -> dict:
        if delay > 0:
            time.sleep(delay)

        ts = datetime.now()
        ts_str = ts.strftime("%Y%m%d_%H%M%S")
        date_str = ts.strftime("%Y-%m-%d")
        event_dir = os.path.join(self.save_path, date_str, kind, f"{ts_str}_{source_app}")
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

        raw_path = export_raw_text(event_dir, text)

        attachments = {
            "screenshots": saved_shots,
            "replay": replay,
            "raw_text": raw_path,
        }

        write_metadata(event_dir, ts, source_app, kind, text, attachments)

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
