import threading
import time
from collections import deque
from typing import Callable, Optional

from core.logger import log


class FrequencyMonitor:
    def __init__(self):
        self._lock = threading.Lock()
        self._windows: dict = {}

    def _window(self, key: str, window_seconds: int) -> deque:
        if key not in self._windows:
            self._windows[key] = deque(maxlen=1000)
        return self._windows[key]

    def record(self, event_type: str, window_seconds: int):
        now = time.time()
        key = event_type
        with self._lock:
            w = self._window(key, window_seconds)
            w.append(now)
            while w and w[0] < now - window_seconds:
                w.popleft()
            return len(w)

    def count(self, event_type: str, window_seconds: int) -> int:
        now = time.time()
        with self._lock:
            w = self._window(event_type, window_seconds)
            while w and w[0] < now - window_seconds:
                w.popleft()
            return len(w)


class AntiTag:
    def __init__(self, config: dict):
        self.config = config
        self.freq = FrequencyMonitor()
        self._frozen = False
        self._on_freeze: Optional[Callable] = None

    def set_on_freeze(self, fn: Callable):
        self._on_freeze = fn

    @property
    def enabled(self) -> bool:
        return self.config.get("enabled", True)

    def record_friend_request(self) -> int:
        window = self.config.get("friend_request_window", 300)
        return self.freq.record("friend_request", window)

    def record_temp_session(self) -> int:
        window = self.config.get("temp_session_window", 300)
        return self.freq.record("temp_session", window)

    def record_group_invite(self) -> int:
        window = self.config.get("group_invite_window", 300)
        return self.freq.record("group_invite", window)

    def check_friend_request(self) -> bool:
        if not self.enabled:
            return False
        window = self.config.get("friend_request_window", 300)
        threshold = self.config.get("friend_request_threshold", 20)
        count = self.freq.count("friend_request", window)
        if count > threshold:
            log.warning(f"加好友频率异常：{count}/{window}s (阈值 {threshold})")
            return True
        return False

    def check_temp_session(self) -> bool:
        if not self.enabled:
            return False
        window = self.config.get("temp_session_window", 300)
        threshold = self.config.get("temp_session_threshold", 30)
        count = self.freq.count("temp_session", window)
        if count > threshold:
            log.warning(f"临时会话频率异常：{count}/{window}s (阈值 {threshold})")
            return True
        return False

    def check_group_invite(self) -> bool:
        if not self.enabled:
            return False
        window = self.config.get("group_invite_window", 300)
        threshold = self.config.get("group_invite_threshold", 10)
        count = self.freq.count("group_invite", window)
        if count > threshold:
            log.warning(f"拉群频率异常：{count}/{window}s (阈值 {threshold})")
            return True
        return False

    def check_all(self) -> list:
        alerts = []
        if self.check_friend_request():
            alerts.append(("friend_request", "加好友频率异常"))
        if self.check_temp_session():
            alerts.append(("temp_session", "临时会话频率异常"))
        if self.check_group_invite():
            alerts.append(("group_invite", "拉群频率异常"))

        if alerts and self.config.get("auto_freeze", False) and not self._frozen:
            self._freeze()
        return alerts

    def _freeze(self):
        self._frozen = True
        if self._on_freeze:
            try:
                self._on_freeze()
                log.info("已触发入口冻结")
            except Exception as e:
                log.warning(f"入口冻结失败：{e}")

    def get_lockdown_checks(self) -> list:
        return [
            ("QID 搜索", "关闭 QID/Q 号搜索添加"),
            ("临时会话", "关闭临时会话/私聊权限"),
            ("陌生人拉群", "关闭陌生人拉群权限"),
            ("加好友验证", "开启加好友验证问题"),
            ("添加方式", "限制添加方式为仅扫码"),
            ("群邀请验证", "开启群邀请需要我确认"),
        ]
