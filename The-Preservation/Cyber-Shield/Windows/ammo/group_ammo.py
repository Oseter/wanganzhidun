"""群聊版标准弹药 v1 格式。"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any


AMMO_VERSION = "v1"


class GroupAmmo:
    def __init__(self, **kwargs):
        self.data: Dict[str, Any] = {
            "version": AMMO_VERSION,
            "ammo_type": "group",
            "target_account": "",
            "target_platform": "",
            "violation_time": datetime.now().isoformat(),
            "violation_content": "",
            "clause": "",
            "evidence_attachments": {},
            "reporter_info": {
                "tool": "WangAnZhiDun",
                "version": AMMO_VERSION,
            },
            "meta": {
                "source_app": "",
                "collected_at": datetime.now().isoformat(),
                "collection_method": "",
            },
            "group_id": "",
            "group_name": "",
            "admin_info": "",
            "member_count": 0,
            "additional_context": "",
        }
        self.data.update(kwargs)

    @classmethod
    def from_dict(cls, d: dict) -> "GroupAmmo":
        inst = cls()
        inst.data.update(d)
        inst.data["ammo_type"] = "group"
        return inst

    @classmethod
    def from_json(cls, path: str) -> "GroupAmmo":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_dict(self) -> dict:
        return dict(self.data)

    def to_json(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def validate(self) -> List[str]:
        errors = []
        if not self.data.get("target_account"):
            errors.append("target_account 缺失")
        if not self.data.get("violation_content"):
            errors.append("violation_content 缺失")
        if not self.data.get("clause"):
            errors.append("clause 缺失")
        return errors

    @property
    def target_account(self) -> str:
        return self.data.get("target_account", "")

    @target_account.setter
    def target_account(self, v: str):
        self.data["target_account"] = v

    @property
    def violation_content(self) -> str:
        return self.data.get("violation_content", "")

    @violation_content.setter
    def violation_content(self, v: str):
        self.data["violation_content"] = v

    def set_evidence(self, screenshots: List[str] = None,
                     replay: str = None, raw_text: str = None):
        self.data["evidence_attachments"] = {
            "screenshots": screenshots or [],
            "replay": replay,
            "raw_text": raw_text,
        }

    def to_draft_text(self) -> str:
        d = self.data
        lines = [
            f"【网安智盾 · 举报草稿】",
            f"弹药版本：{d.get('version', AMMO_VERSION)}",
            f"弹药类型：群聊版",
            f"来源应用：{d.get('meta', {}).get('source_app', '未知')}",
            f"取证时间：{d.get('violation_time', '')}",
            f"目标平台：{d.get('target_platform', '')}",
            f"目标账号：{d.get('target_account', '待确认')}",
            f"对应条款：{d.get('clause', '')}",
            "",
            "违规内容：",
            d.get("violation_content", ""),
            "",
            "证据附件：",
        ]
        att = d.get("evidence_attachments", {})
        for s in att.get("screenshots", []):
            lines.append(f"  - 截图：{s}")
        if att.get("replay"):
            lines.append(f"  - 录像：{att.get('replay')}")
        if att.get("raw_text"):
            lines.append(f"  - 原文：{att.get('raw_text')}")
        lines.extend([
            "",
            f"群 ID：{d.get('group_id', '')}",
            f"群名称：{d.get('group_name', '')}",
            f"管理员信息：{d.get('admin_info', '')}",
            f"成员数：{d.get('member_count', 0)}",
        ])
        return "\n".join(lines)
