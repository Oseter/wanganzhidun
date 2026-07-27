"""聊天记录导出原子（预留）。

当前通过 raw.txt 保存触发原文。
后续可对接 QQ/微信漫游消息 API 拉取完整上下文。
"""
import os
from typing import Optional


def export_raw_text(event_dir: str, text: str) -> str:
    path = os.path.join(event_dir, "raw.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
