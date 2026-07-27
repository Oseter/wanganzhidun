"""网络举报 APP 原子（预留）。

通过 Android Intent 唤起网络举报客户端。
PC 端暂不实现，移动端通过 ReportLauncher.kt 处理。
"""
from typing import Any, Tuple

from channel.base import Channel


class App12377Channel(Channel):
    name = "网络举报 APP"

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        return False, "仅移动端支持"

    def healthy(self) -> bool:
        return False
