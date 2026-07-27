"""通道降级原子。

主通道失败时自动切备用通道。
"""
import threading
from typing import Any, Callable, List, Tuple

from channel.base import Channel
from channel.health_probe import filter_healthy
from core.logger import log


def dispatch_with_fallback(
    channels: List[Channel],
    primary_names: set,
    ammo: Any,
    draft_path: str,
    timeout: int = 35,
) -> List[Tuple[str, bool, str]]:
    """主通道并发发射，失败时切备用。"""
    primary = [ch for ch in channels if ch.name in primary_names]
    fallback = [ch for ch in channels if ch.name not in primary_names]
    results: List[Tuple[str, bool, str]] = []
    lock = threading.Lock()

    def _run(ch: Channel):
        if not ch.healthy():
            log.info(f"{ch.name} 通道不可达，跳过")
            with lock:
                results.append((ch.name, False, "通道不可达"))
            return
        ok, note = ch.dispatch(ammo, draft_path)
        with lock:
            results.append((ch.name, ok, note))

    threads = []
    for ch in primary:
        t = threading.Thread(target=_run, args=(ch,), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=timeout)

    failed_primary = any(not ok for _, ok, _ in results if results)
    if failed_primary and fallback:
        log.info("主通道失败，切换备用通道")
        fb_threads = []
        for ch in fallback:
            t = threading.Thread(target=_run, args=(ch,), daemon=True)
            t.start()
            fb_threads.append(t)
        for t in fb_threads:
            t.join(timeout=30)

    return results
