from typing import List, Tuple

from ammo.personal_ammo import PersonalAmmo
from channel.base import Channel
from channel.ch_12377_web import Web12377Channel
from channel.ch_12377_app import App12377Channel
from channel.ch_weixin_gzh import WeixinGzhChannel
from channel.ch_weibo_dm import WeiboDMChannel
from channel.ch_12377_hotline import HotlineChannel
from channel.ch_email import EmailChannel
from channel.ch_guard import WebGuardChannel
from channel.ch_provincial import ProvincialChannel
from channel.ch_miit import MIITChannel
from channel.ch_cyberpolice import CyberPoliceChannel
from channel.channel_degrade import dispatch_with_fallback


class ChannelManager:
    def __init__(self, config, crypto=None):
        self.config = config
        self.crypto = crypto
        self._channels: List[Channel] = []
        self._build_channels()

    def _build_channels(self):
        cfg = self.config.channels
        email = self.config.email
        self._channels = []
        if cfg.get("web_12377"):
            self._channels.append(Web12377Channel())
        if cfg.get("email_12377"):
            self._channels.append(EmailChannel(
                smtp_server=email.get("smtp_server", ""),
                smtp_port=email.get("smtp_port", 587),
                sender=email.get("sender", ""),
                password=email.get("sender_password", ""),
                receiver=cfg.get("email_receiver", "jubao@12377.cn"),
                crypto=self.crypto,
            ))
        if cfg.get("guard"):
            self._channels.append(WebGuardChannel())
        if cfg.get("provincial"):
            self._channels.append(ProvincialChannel())
        if cfg.get("miit"):
            self._channels.append(MIITChannel())

    def dispatch_all(self, ammo: PersonalAmmo, draft_path: str) -> List[Tuple[str, bool, str]]:
        results: List[Tuple[str, bool, str]] = []
        import threading
        lock = threading.Lock()

        def _run(ch: Channel):
            if not ch.healthy():
                with lock:
                    results.append((ch.name, False, "通道不可达"))
                return
            ok, note = ch.dispatch(ammo, draft_path)
            with lock:
                results.append((ch.name, ok, note))

        threads = []
        for ch in self._channels:
            t = threading.Thread(target=_run, args=(ch,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=30)
        return results

    def dispatch_with_fallback(self, ammo: PersonalAmmo, draft_path: str) -> List[Tuple[str, bool, str]]:
        return dispatch_with_fallback(
            self._channels,
            primary_names={"12377官网", "举报邮箱", "腾讯卫士"},
            ammo=ammo,
            draft_path=draft_path,
        )
