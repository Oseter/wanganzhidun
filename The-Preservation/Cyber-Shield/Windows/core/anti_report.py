"""防打号：检测恶意举报行为，账号加固建议，反申诉预案。"""
import re
import time
from typing import Optional

from .logger import log


REPORT_KEYWORDS = [
    "举报", "投诉", "封号", "冻结", "恶意", "违规",
    "提交举报", "举报反馈", "申诉失败", "账号受限",
    "功能冻结", "永久封禁",
]

APPEAL_TEMPLATES = {
    "malicious_report": (
        "本人账号 {account} 于 {time} 收到平台通知，"
        "对方举报理由为「{reason}」。经核实，该举报系恶意行为，"
        "对方举报内容与事实不符，且举报时机与恶意攻击时间吻合，"
        "附件证据可证明举报人存在主观恶意。"
        "恳请平台核实并驳回恶意举报。"
    ),
    "hijacked_appeal": (
        "本人账号 {account} 于 {time} 发现异常登录/操作，"
        "已立即修改密码并绑定设备锁。"
        "若在该时间点后有违规操作，系他人恶意行为，"
        "本人已在公安机关报案，报案编号：{case_no}。"
    ),
}


class AntiReport:
    """防打号检测与账号加固。"""

    def __init__(self):
        self._last_report_time = 0
        self._report_window: list = []

    def is_report_notification(self, app: str, text: str) -> bool:
        """判断通知是否为举报反馈/封号通知。"""
        text_lower = text.lower()
        for kw in REPORT_KEYWORDS:
            if kw in text_lower or kw in text:
                self._report_window.append((time.time(), app, text))
                self._prune_window()
                return True
        return False

    def _prune_window(self, window: int = 300):
        now = time.time()
        self._report_window = [(t, a, s) for t, a, s in self._report_window
                               if now - t < window]

    def report_frequency(self, window: int = 300) -> int:
        """返回时间窗口内举报通知数量。"""
        self._prune_window(window)
        return len(self._report_window)

    def is_malicious_report_chain(self, threshold: int = 3, window: int = 300) -> bool:
        """多平台短时间内连续收到举报通知 → 恶意聚众举报。"""
        self._prune_window(window)
        return len(self._report_window) >= threshold

    def generate_appeal(self, template: str = "malicious_report",
                        **kwargs) -> str:
        tpl = APPEAL_TEMPLATES.get(template, APPEAL_TEMPLATES["malicious_report"])
        return tpl.format(**kwargs)

    def get_account_hardening_checks(self) -> list:
        """返回账号加固检查清单。"""
        return [
            ("设备锁", "检查是否已开启设备锁/登录保护"),
            ("实名认证", "确认已完成实名认证"),
            ("多因子认证", "开启二次验证/多因子认证"),
            ("登录保护", "开启异地登录保护"),
            ("登录设备管理", "清理不常用登录设备"),
            ("密码强度", "检查密码是否为高强度唯一密码"),
        ]
