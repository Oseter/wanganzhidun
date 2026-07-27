import webbrowser
from typing import Any, Tuple

from channel.base import Channel


class MIITChannel(Channel):
    name = "工信部备用"

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        url = "https://www.12321.cn/"
        try:
            ok = webbrowser.open(url)
            return ok, "" if ok else "浏览器打开失败"
        except Exception as e:
            return False, str(e)
