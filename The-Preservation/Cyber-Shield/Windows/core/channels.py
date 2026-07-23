"""通道抽象：Channel.dispatch(ammo) 接口 + 健康探测 + 自动降级。

内置通道：
    - Web12377Channel:     浏览器打开 12377 官网举报页
    - EmailChannel:         SMTP 发往官方举报邮箱
    - WebGuardChannel:      浏览器打开腾讯卫士
    - ProvincialChannel:    省网信办备用通道
    - MIITChannel:          工信部备用通道

健康探测：channel.healthy() 定期检查可达性。
自动降级：ChannelManager 在主通道失败时顺位切备用通道。
"""
import os
import smtplib
import tempfile
import threading
import time
import webbrowser
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, List, Optional, Tuple, Callable

from .ammo import StandardAmmo
from .logger import log


class Channel(ABC):
    name: str = "base"

    @abstractmethod
    def dispatch(self, ammo: StandardAmmo, draft_path: str) -> Tuple[bool, str]:
        ...

    def healthy(self) -> bool:
        return True


class Web12377Channel(Channel):
    name = "12377官网"

    def dispatch(self, ammo: StandardAmmo, draft_path: str) -> Tuple[bool, str]:
        url = "https://www.12377.cn/"
        try:
            ok = webbrowser.open(url)
            return ok, "" if ok else "浏览器打开失败"
        except Exception as e:
            return False, str(e)

    def healthy(self) -> bool:
        return True


class WebGuardChannel(Channel):
    name = "腾讯卫士"

    def dispatch(self, ammo: StandardAmmo, draft_path: str) -> Tuple[bool, str]:
        url = "https://110.qq.com/"
        try:
            ok = webbrowser.open(url)
            return ok, "" if ok else "浏览器打开失败"
        except Exception as e:
            return False, str(e)

    def healthy(self) -> bool:
        return True


class EmailChannel(Channel):
    name = "举报邮箱"

    def __init__(self, smtp_server: str, smtp_port: int,
                 sender: str, password: str, receiver: str,
                 crypto=None):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.receiver = receiver
        self.crypto = crypto

    def dispatch(self, ammo: StandardAmmo, draft_path: str) -> Tuple[bool, str]:
        if not self.smtp_server or not self.sender:
            return False, "SMTP 未配置"
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = self.receiver
            msg["Subject"] = f"举报恶意账号 {ammo.target_account}"
            with open(draft_path, "r", encoding="utf-8") as f:
                msg.attach(MIMEText(f.read(), "plain", "utf-8"))

            att = ammo.data.get("evidence_attachments", {})
            tmp_files = []
            try:
                for s in att.get("screenshots", []):
                    plain = self._resolve(s)
                    if plain:
                        tmp_files.append(plain)
                for fp in tmp_files:
                    with open(fp, "rb") as f:
                        part = MIMEApplication(f.read())
                        part.add_header("Content-Disposition", "attachment",
                                        filename=os.path.basename(fp))
                        msg.attach(part)
            finally:
                for t in tmp_files:
                    try:
                        os.remove(t)
                    except OSError:
                        pass

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)
            return True, ""
        except Exception as e:
            log.warning(f"邮件发送失败：{e}")
            return False, str(e)

    def _resolve(self, path: str) -> Optional[str]:
        if os.path.exists(path):
            return path
        enc = path if path.endswith(".enc") else path + ".enc"
        if os.path.exists(enc) and self.crypto is not None:
            try:
                suffix = ".png" if "shot" in os.path.basename(path) else ".bin"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.close()
                self.crypto.decrypt_file(enc, tmp.name)
                return tmp.name
            except Exception as e:
                log.warning(f"解密附件失败：{e}")
        return None

    def healthy(self) -> bool:
        if not self.smtp_server or not self.sender:
            return False
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=5) as s:
                s.starttls()
                s.quit()
            return True
        except Exception:
            return False


class ProvincialChannel(Channel):
    name = "省网信办备用"

    def dispatch(self, ammo: StandardAmmo, draft_path: str) -> Tuple[bool, str]:
        url = "http://www.scio.gov.cn/"
        try:
            ok = webbrowser.open(url)
            return ok, "" if ok else "浏览器打开失败"
        except Exception as e:
            return False, str(e)


class MIITChannel(Channel):
    name = "工信部备用"

    def dispatch(self, ammo: StandardAmmo, draft_path: str) -> Tuple[bool, str]:
        url = "https://www.12321.cn/"
        try:
            ok = webbrowser.open(url)
            return ok, "" if ok else "浏览器打开失败"
        except Exception as e:
            return False, str(e)


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

    def dispatch_all(self, ammo: StandardAmmo, draft_path: str) -> List[Tuple[str, bool, str]]:
        results: List[Tuple[str, bool, str]] = []
        lock = threading.Lock()

        def _run(ch: Channel):
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

    def dispatch_with_fallback(self, ammo: StandardAmmo, draft_path: str) -> List[Tuple[str, bool, str]]:
        """主通道失败时自动降级到备用通道。"""
        results: List[Tuple[str, bool, str]] = []
        primary = [ch for ch in self._channels
                   if ch.name in ("12377官网", "举报邮箱", "腾讯卫士")]
        fallback = [ch for ch in self._channels
                    if ch.name not in ("12377官网", "举报邮箱", "腾讯卫士")]
        lock = threading.Lock()

        def _run(ch: Channel):
            ok, note = ch.dispatch(ammo, draft_path)
            with lock:
                results.append((ch.name, ok, note))

        threads = []
        for ch in primary:
            t = threading.Thread(target=_run, args=(ch,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=35)

        failed_primary = any(not ok for _, ok, _ in results if results)
        if failed_primary and fallback:
            log.info("主通道失败，切换备用通道")
            fb_threads = []
            for ch in fallback:
                t = threading.Thread(target=_run, args=(ch,), daemon=True)
                t.start()
                fb_threads.append(t)
            for t in fb_threads:
                t.join(timeout=30)

        return results
