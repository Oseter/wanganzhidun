"""举报生成模块：把标准弹药整理成可发送的举报草稿。

支持两种输出：
    1. 本地举报草稿（.txt / .html），用户复制后手动提交官方通道；
    2. 邮件通道（可选）：通过 SMTP 发送到 jubao@12377.cn 等官方邮箱。

红线：不伪造证据；只对恶意攻击目标使用；邮件仅发往官方举报地址。
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, Optional


class Reporter:
    """举报草稿生成与发送。"""

    def __init__(self, email_cfg: Dict, save_dir: str):
        self.email_cfg = email_cfg
        self.save_dir = save_dir
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
            # 附件：截图（仅原始未加密副本，若存在）
            att = ammo.get("evidence_attachments", {})
            for s in att.get("screenshots", []):
                if os.path.exists(s):
                    with open(s, "rb") as fp:
                        part = MIMEApplication(fp.read())
                        part.add_header(
                            "Content-Disposition", "attachment",
                            filename=os.path.basename(s),
                        )
                        msg.attach(part)
            with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
                server.starttls()
                server.login(cfg["sender"], cfg["sender_password"])
                server.send_message(msg)
            return True
        except Exception as e:
            from .logger import log
            log.warning(f"邮件发送失败：{e}")
            return False
