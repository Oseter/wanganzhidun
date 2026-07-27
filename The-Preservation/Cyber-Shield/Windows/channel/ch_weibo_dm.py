"""微博私信原子（预留）。

通过微博 API 私信举报入口提交。
待微博开放平台审核。
"""
from typing import Any, Tuple

from channel.base import Channel


class WeiboDMChannel(Channel):
    name = "微博私信"

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        return False, "待接入"

    def healthy(self) -> bool:
        return False
