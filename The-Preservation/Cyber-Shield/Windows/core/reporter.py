"""举报生成模块：把标准弹药整理成可发送的举报草稿。

支持三种官方合规通道（同谐命途·多入口并发）：
    1. 12377 网信办官网（浏览器打开举报页）；
    2. 腾讯卫士（浏览器打开举报页）；
    3. 举报邮箱（可选 SMTP，发往 jubao@12377.cn 等官方地址）。

report_channels() 在用户手动确认后并发发起上述已启用通道。

红线：不伪造证据；只对恶意攻击目标使用；邮件仅发往官方举报地址；
      绝不自动举报（必须由确认弹窗授权）。
"""
import os
import smtplib
import tempfile
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Callable, Dict, List, Optional, Tuple


class Reporter:
    """举报草稿生成与发送。"""

    def __init__(self, email_cfg: Dict, save_dir: str, crypto=None):
        self.email_cfg = email_cfg
        self.save_dir = save_dir
        self.crypto = crypto
        os.makedirs(save_dir, exist_ok=True)

    def build_draft(self, ammo: Dict) -> str:
        """生成可读举报草稿文本，返回保存路径。"""
        lines = [
            "【网安智盾 · 举报草稿】",
            f"来源应用：{ammo.get('source_app', '未知')}",
            f"时间：{ammo.get('time', '')}",
            f"目标账号：{ammo.get('target_account', '待确认')}",
            f"对应条款：{ammo.get('clause', '')}",
            "",
            "违规内容：",
            ammo.get("violation_content", ""),
            "",
            "证据附件：",
        ]
        att = ammo.get("evidence_attachments", {})
        for s in att.get("screenshots", []):
            lines.append(f"  - 截图：{s}")
        if att.get("replay"):
            lines.append(f"  - 录像：{att.get('replay')}")
        lines.append(f"  - 原文：{att.get('raw_text', '')}")

        ts = ammo.get("time", "").replace(":", "").replace("-", "")[:14]
        path = os.path.join(self.save_dir, f"report_draft_{ts}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path

    def send_email(self, ammo: Dict, draft_path: str) -> bool:
        """通过 SMTP 发送举报邮件到官方邮箱。失败返回 False。"""
        cfg = self.email_cfg
        if not cfg.get("smtp_server") or not cfg.get("sender"):
            return False
        try:
            msg = MIMEMultipart()
            msg["From"] = cfg["sender"]
            msg["To"] = cfg.get("receiver", "jubao@12377.cn")
            msg["Subject"] = f"举报恶意攻击账号 {ammo.get('target_account', '待确认')}"
            with open(draft_path, "r", encoding="utf-8") as f:
                body = f.read()
            msg.attach(MIMEText(body, "plain", "utf-8"))
            # 附件：截图。证据默认加密存储（.enc），发往官方邮箱前需先解密到
            # 临时文件；若加密关闭则为明文，直接附加。解密出的临时文件发送后清理。
            att = ammo.get("evidence_attachments", {})
            tmp_attachments = []
            try:
                for s in att.get("screenshots", []):
                    plain = self._resolve_attachment(s)
                    if plain:
                        tmp_attachments.append(plain)
                for s in tmp_attachments:
                    with open(s, "rb") as fp:
                        part = MIMEApplication(fp.read())
                        part.add_header(
                            "Content-Disposition", "attachment",
                            filename=os.path.basename(s),
                        )
                        msg.attach(part)
            finally:
                temp_dir = (tempfile.gettempdir() or "").rstrip(os.sep)
                for t in tmp_attachments:
                    if temp_dir and t.startswith(temp_dir):
                        try:
                            os.remove(t)
                        except OSError:
                            pass
            with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
                server.starttls()
                server.login(cfg["sender"], cfg["sender_password"])
                server.send_message(msg)
            return True
        except Exception as e:
            from .logger import log
            log.warning(f"邮件发送失败：{e}")
            return False

    def _resolve_attachment(self, path: str):
        """返回可直接附邮件的文件路径：明文直接返回；加密 .enc 则解密到临时文件。

        证据默认以 .enc 落盘（加密存储），邮件必须发真实证据，故先解密。
        解密出的临时文件由调用方发送后清理。
        """
        if os.path.exists(path):
            return path
        enc = path if path.endswith(".enc") else path + ".enc"
        if os.path.exists(enc) and self.crypto is not None:
            try:
                suffix = ".png" if "shot" in os.path.basename(path) else (
                    os.path.splitext(path)[1] or ".bin"
                )
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.close()
                self.crypto.decrypt_file(enc, tmp.name)
                return tmp.name
            except Exception as e:
                from .logger import log
                log.warning(f"解密证据附件失败 {enc}：{e}")
        return None

    # ---------------- 多通道并发举报（同谐命途） ----------------
    def report_channels(self, ammo: Dict, draft_path: str,
                        report_cfg: Dict) -> List[Tuple[str, bool, str]]:
        """按配置并发发起已启用的举报通道。

        返回 [(通道名, 是否成功, 备注), ...]，便于上层汇总与提示。
        仅在所有通道已在用户手动确认的前提下调用（红线）。
        """
        jobs: List[Tuple[str, Callable]] = []
        if report_cfg.get("enable_12377"):
            jobs.append(("12377", lambda: self._open_web(
                report_cfg.get("url_12377", "https://www.12377.cn/"))))
        if report_cfg.get("enable_guard"):
            jobs.append(("腾讯卫士", lambda: self._open_web(
                report_cfg.get("url_guard", "https://110.qq.com/"))))
        if report_cfg.get("enable_email"):
            jobs.append(("举报邮箱", lambda: self.send_email(ammo, draft_path)))

        if not jobs:
            return []

        results: List[Tuple[str, bool, str]] = []
        with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
            futures = {ex.submit(fn): name for name, fn in jobs}
            for fut in futures:
                name = futures[fut]
                try:
                    ok = bool(fut.result(timeout=30))
                except Exception as e:  # noqa: BLE001
                    ok, note = False, str(e)
                    from .logger import log
                    log.warning(f"通道 {name} 举报失败：{note}")
                    results.append((name, ok, note))
                    continue
                results.append((name, ok, ""))
        return results

    @staticmethod
    def _open_web(url: str) -> bool:
        """用默认浏览器打开官方举报页（仅官方合规地址）。"""
        try:
            return bool(webbrowser.open(url))
        except Exception as e:  # noqa: BLE001
            from .logger import log
            log.warning(f"打开网页失败 {url}：{e}")
            return False
