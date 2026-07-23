"""防点号：检测改包攻击（异常加好友频率、异常临时会话、异常拉群），
接口封锁建议，频率监控与自动入口冻结。

实际协议封锁由用户在各平台手动开关，本模块仅检测与提醒。
"""
import time
from typing import Callable, Optional

from .logger import log
from .monitor import FrequencyMonitor


class AntiTag:
    """防点号检测。"""

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
        """记录一次加好友请求，返回窗口内总数。"""
        window = self.config.get("friend_request_window", 300)
        return self.freq.record("friend_request", window)

    def record_temp_session(self) -> int:
        """记录一次临时会话，返回窗口内总数。"""
        window = self.config.get("temp_session_window", 300)
        return self.freq.record("temp_session", window)

    def record_group_invite(self) -> int:
        """记录一次拉群邀请，返回窗口内总数。"""
        window = self.config.get("group_invite_window", 300)
        return self.freq.record("group_invite", window)

    def check_friend_request(self) -> bool:
        """检查加好友频率是否异常。"""
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
        """检查临时会话频率是否异常。"""
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
        """检查拉群频率是否异常。"""
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
        """执行全部频率检查，返回异常事件列表。"""
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
        """自动冻结入口（调用注册的回调）。"""
        self._frozen = True
        if self._on_freeze:
            try:
                self._on_freeze()
                log.info("已触发入口冻结")
            except Exception as e:
                log.warning(f"入口冻结失败：{e}")

    def get_lockdown_checks(self) -> list:
        """返回接口封锁检查清单。"""
        return [
            ("QID 搜索", "关闭 QID/Q 号搜索添加"),
            ("临时会话", "关闭临时会话/私聊权限"),
            ("陌生人拉群", "关闭陌生人拉群权限"),
            ("加好友验证", "开启加好友验证问题"),
            ("添加方式", "限制添加方式为仅扫码"),
            ("群邀请验证", "开启群邀请需要我确认"),
        ]
