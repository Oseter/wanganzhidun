from typing import List, Optional


class KeywordEngine:
    def __init__(self, keywords: List[str], attack_keywords: List[str] = None):
        self.keywords = sorted(set(keywords), key=len, reverse=True)
        self.attack_keywords = attack_keywords or [
            "举报你", "恶意举报", "封你", "搞你", "炸你",
        ]

    def match(self, text: str) -> Optional[str]:
        if not text:
            return None
        for kw in self.keywords:
            if kw and kw in text:
                return kw
        return None

    def is_attack(self, text: str) -> bool:
        return any(k in text for k in self.attack_keywords if k)

    def reload(self, keywords: List[str], attack_keywords: List[str] = None):
        self.keywords = sorted(set(keywords), key=len, reverse=True)
        if attack_keywords is not None:
            self.attack_keywords = attack_keywords
