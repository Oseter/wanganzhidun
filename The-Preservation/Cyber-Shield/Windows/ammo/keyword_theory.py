"""关键词论匹配原子。

将监测关键词分类为攻击性、骚扰性、取证性，
用于威胁评分和反伤决策。
"""
from typing import Dict, List

ATTACK_KEYWORDS = [
    "举报你", "恶意举报", "封你", "搞你", "炸你", "去死", "人肉",
    "定位你", "找你", "上门", "弄死你", "曝光你",
]

HARASS_KEYWORDS = [
    "傻逼", "废物", "垃圾", "滚", "脑残", "智障",
    "全家", "祖安", "司马", "死妈",
]

FORENSICS_KEYWORDS = [
    "账号异常", "异地登录", "批量举报", "被加好友", "被拉群",
    "举报反馈", "申诉失败", "账号受限", "功能冻结",
]


def classify_keywords(text: str, custom_keywords: List[str] = None) -> Dict[str, bool]:
    return {
        "is_attack": any(k in text for k in ATTACK_KEYWORDS),
        "is_harass": any(k in text for k in HARASS_KEYWORDS),
        "is_forensics": any(k in text for k in FORENSICS_KEYWORDS),
        "is_custom": any(k in text for k in (custom_keywords or [])),
    }
