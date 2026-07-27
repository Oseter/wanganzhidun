"""通道健康探测原子。"""
from typing import List, Tuple

from channel.base import Channel


def probe_all(channels: List[Channel]) -> List[Tuple[str, bool]]:
    """探测全部通道可达性。"""
    return [(ch.name, ch.healthy()) for ch in channels]


def filter_healthy(channels: List[Channel]) -> List[Channel]:
    """返回可达通道。"""
    return [ch for ch in channels if ch.healthy()]
