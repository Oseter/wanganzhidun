"""关键词引擎：从通知文本中匹配触发关键词。

设计原则（红线）：只匹配用户配置的关键词，不爬取非授权数据，
不伪造证据。命中即触发取证，证据如实归档。
"""
from typing import List, Optional


class KeywordEngine:
    """关键词匹配引擎，支持精确包含与优先级记录。"""

    def __init__(self, keywords: List[str]):
        # 按长度降序，优先匹配更长（更具体）的关键词
        self.keywords = sorted(set(keywords), key=len, reverse=True)

    def match(self, text: str) -> Optional[str]:
        """返回命中的关键词；未命中返回 None。"""
        if not text:
            return None
        for kw in self.keywords:
            if kw and kw in text:
                return kw
        return None

    def is_attack(self, text: str, attack_keywords: List[str] = None) -> bool:
        """判断通知是否为攻击性内容（用于反伤判定）。"""
        if not attack_keywords:
            attack_keywords = ["举报你", "恶意举报", "封你", "搞你", "炸你"]
        return any(k in text for k in attack_keywords if k)

    def reload(self, keywords: List[str]):
        self.keywords = sorted(set(keywords), key=len, reverse=True)
