import webbrowser
from typing import Any, Tuple

from channel.base import Channel


class ProvincialChannel(Channel):
    name = "省网信办备用"

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        url = "http://www.scio.gov.cn/"
        try:
            ok = webbrowser.open(url)
            return ok, "" if ok else "浏览器打开失败"
        except Exception as e:
            return False, str(e)
