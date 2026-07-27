"""群组管控原子（预留）。

功能：敏感词过滤、群成员异常变动监控、入群验证自动化、替身号管理。
当前仅提供接口定义，具体实现需对接各平台 API。
"""


def check_sensitive_content(text: str, keywords: list) -> bool:
    """检查消息是否含敏感内容。"""
    return any(k in text for k in keywords if k)


def auto_enable_verification(threshold: int = 10, window: int = 300):
    """（预留）短时间内大量陌生号加入时自动开启入群验证。"""
    raise NotImplementedError("群组管控待实现")


def auto_kick_strangers(member_list: list, known_members: set) -> list:
    """（预留）踢出不在白名单的新入群成员。"""
    raise NotImplementedError("群组管控待实现")
