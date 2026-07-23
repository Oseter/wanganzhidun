"""攻击监测：Windows 通知监听 + 频率异常检测。

- winrt UserNotificationListener 订阅系统通知
- 非 Windows 环境降级为轮询模式（injection_queue.txt）
- 命中关键词 → 回调 on_trigger
"""
import platform
import threading
import time
from collections import deque
from datetime import datetime
from typing import Callable, Optional

from .logger import log
from .keyword_engine import KeywordEngine


class NotificationMonitor:
    def __init__(self, keyword_engine: KeywordEngine,
                 on_trigger: Callable[[str, str, float], None]):
        self.kw = keyword_engine
        self.on_trigger = on_trigger
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._listener = None

    def _setup_winrt(self) -> bool:
        try:
            from winrt.windows.ui.notifications.management import (
                UserNotificationListener, NotificationListenerAccessStatus,
            )
            from winrt.windows.ui.notifications import NotificationKinds
            self._listener = UserNotificationListener.current()
            op = self._listener.request_access()
            status = op.get() if hasattr(op, "get") else op
            if status != NotificationListenerAccessStatus.ALLOWED:
                log.warning("通知监听未获授权")
                return False

            def _on_added(sender, args):
                try:
                    notif = sender.get_notification(args.user_notification_id)
                    if notif is None:
                        return
                    app = notif.app_info.display_info.display_name
                    text = self._extract_text(notif)
                    self._dispatch(app, text)
                except Exception as e:
                    log.debug(f"解析通知异常：{e}")

            self._listener.add_notification_changed(_on_added)
            return True
        except Exception as e:
            log.warning(f"winrt 不可用，降级轮询：{e}")
            return False

    @staticmethod
    def _extract_text(notif) -> str:
        try:
            vis = notif.notification.visual
            binding = vis.bindings[0]
            parts = []
            for txt in binding.get_text_elements():
                parts.append(txt.text)
            return " ".join(p for p in parts if p)
        except Exception:
            return ""

    def _dispatch(self, app: str, text: str):
        hit = self.kw.match(text)
        if hit:
            log.info(f"命中关键词[{hit}] 来自 {app}")
            self.on_trigger(app, text, time.time())

    def _poll_loop(self, queue_path: str = "injection_queue.txt"):
        seen = 0
        import os
        while self._running:
            if os.path.exists(queue_path):
                try:
                    with open(queue_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    if len(lines) > seen:
                        for line in lines[seen:]:
                            line = line.strip()
                            if "|" in line:
                                app, text = line.split("|", 1)
                                self._dispatch(app.strip(), text.strip())
                        seen = len(lines)
                except Exception as e:
                    log.debug(f"轮询读取异常：{e}")
            time.sleep(1)

    def start(self):
        self._running = True
        if platform.system() == "Windows" and self._setup_winrt():
            log.info("通知监听已启动（winrt）")
            return
        log.info("通知监听已启动（轮询降级）")
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)


class FrequencyMonitor:
    """频率监控：防点号用，检测异常加好友/临时会话/拉群。"""

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
