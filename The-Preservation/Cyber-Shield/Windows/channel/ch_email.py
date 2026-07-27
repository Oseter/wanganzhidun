import os
import smtplib
import tempfile
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional, Tuple

from channel.base import Channel
from core.logger import log


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

    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        if not self.smtp_server or not self.sender:
            return False, "SMTP 未配置"
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = self.receiver
            msg["Subject"] = f"举报恶意账号 {ammo.target_account}"
            with open(draft_path, "r", encoding="utf-8") as f:
                msg.attach(MIMEText(f.read(), "plain", "utf-8"))

            att = ammo.to_dict().get("evidence_attachments", {})
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
