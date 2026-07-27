import webbrowser
from typing import Any, Tuple

from channel.base import Channel


class WebGuardChannel(Channel):
    name = "腾讯卫士"

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        url = "https://110.qq.com/"
        try:
            ok = webbrowser.open(url)
            return ok, "" if ok else "浏览器打开失败"
        except Exception as e:
            return False, str(e)
