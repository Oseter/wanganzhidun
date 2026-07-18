"""通知监听模块：监听 Windows 通知中心（QQ/微信弹窗通知）。

Windows 端使用 winrt UserNotificationListener 订阅系统通知；
非 Windows 环境（开发/调试）降级为轮询模式：读取 injection_queue 中的
模拟通知，便于沙箱自测，不接入任何真实账号数据。

命中关键词 → 回调 on_trigger(app_name, text, timestamp)。
"""
import platform
import threading
import time
from typing import Callable, Optional

from .logger import log
from .keyword_engine import KeywordEngine


class NotificationMonitor:
    """通知监听器，跨平台降级。"""

    def __init__(self, keyword_engine: KeywordEngine,
                 on_trigger: Callable[[str, str, float], None]):
        self.kw = keyword_engine
        self.on_trigger = on_trigger
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._listener = None

    # ---------------- Windows 实现 ----------------
    def _setup_winrt(self) -> bool:
        try:
            from winrt.windows.ui.notifications.management import (
                UserNotificationListener,
                NotificationListenerAccessStatus,
            )
            from winrt.windows.ui.notifications import NotificationKinds
            self._listener = UserNotificationListener.current()
            # request_access() 返回 IAsyncOperation（异步），必须等待结果后再判定。
            # 本方法运行于同步上下文（无事件循环），用 .get() 阻塞等待其完成，
            # 否则 acc 拿到的只是未完成的异步句柄，acc != 1 判定会失效（W4 修复）。
            op = self._listener.request_access()
            status = op.get() if hasattr(op, "get") else op
            if status != NotificationListenerAccessStatus.ALLOWED:
                log.warning("通知监听未获授权（需在系统设置中允许）。")
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

    # ---------------- 通用分发 ----------------
    def _dispatch(self, app: str, text: str):
        hit = self.kw.match(text)
        if hit:
            log.info(f"命中关键词[{hit}] 来自 {app}: {text[:40]}")
            self.on_trigger(app, text, time.time())

    # ---------------- 轮询降级（开发/调试） ----------------
    def _poll_loop(self, queue_path: str = "injection_queue.txt"):
        """读取注入队列中的模拟通知（每行：app|text）。"""
        import os
        seen = 0
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

    # ---------------- 生命周期 ----------------
    def start(self):
        self._running = True
        if platform.system() == "Windows" and self._setup_winrt():
            log.info("通知监听已启动（winrt 模式）。")
            return
        log.info("通知监听已启动（轮询降级模式）。")
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
