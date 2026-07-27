"""公安部网络违法犯罪举报网站原子（预留）。"""
from typing import Any, Tuple

from channel.base import Channel


class CyberPoliceChannel(Channel):
    name = "公安部"

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        return False, "待接入"

    def healthy(self) -> bool:
        return False
