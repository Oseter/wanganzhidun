"""微信公众号原子（预留）。

通过 Android 唤起微信并跳转一键举报。
PC 端暂不实现。
"""
from typing import Any, Tuple

from channel.base import Channel


class WeixinGzhChannel(Channel):
    name = "微信公众号"

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        return False, "仅移动端支持"

    def healthy(self) -> bool:
        return False
