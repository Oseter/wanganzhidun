"""12377 举报专区类别映射。"""

CATEGORIES = {
    "political": "政治类",
    "terror": "暴恐类",
    "fraud": "诈骗类",
    "enterprise": "涉企侵权",
    "minor": "涉未成年人",
    "porn": "色情类",
    "vulgar": "低俗类",
    "gambling": "赌博类",
    "ai_misuse": "涉 AI 应用乱象",
    "infringement": "侵权类",
    "rumor": "谣言类",
    "other": "其他类",
}


def match_category(text: str) -> str:
    """根据文本内容推断举报类别。"""
    text_lower = text.lower()
    if any(k in text_lower for k in ("诈骗", "骗", "欺诈", "非法集资")):
        return CATEGORIES["fraud"]
    if any(k in text_lower for k in ("色情", "淫秽", "裸")):
        return CATEGORIES["porn"]
    if any(k in text_lower for k in ("赌博", "赌")):
        return CATEGORIES["gambling"]
    if any(k in text_lower for k in ("谣言", "造谣", "传谣")):
        return CATEGORIES["rumor"]
    if any(k in text_lower for k in ("侵权", "盗用", "抄袭")):
        return CATEGORIES["infringement"]
    if any(k in text_lower for k in ("未成年", "儿童", "青少年")):
        return CATEGORIES["minor"]
    return CATEGORIES["other"]
