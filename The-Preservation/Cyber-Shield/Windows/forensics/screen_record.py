import time
from typing import Optional

from core.logger import log


class OBSRecorder:
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
