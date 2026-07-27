"""12377 热线原子（预留）。

拨号界面：用户点确认后打开拨号盘预填 12377。
"""
from typing import Any, Tuple

from channel.base import Channel


class HotlineChannel(Channel):
    name = "12377 热线"

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        return False, "待接入"

    def healthy(self) -> bool:
        return False
