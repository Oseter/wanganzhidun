"""协同接口：与 CWAS / 全频道频带阻塞干扰 / 复活甲 / 超限卫兵 对接。

CWAS 注册：组件启动时上报命途归属、弹药版本、占用通道。
标准弹药协议：弹药 v1 格式全体系通用。
五步闭环：覆盖「利用」（反伤发射）与「反馈」（结果回收）。
"""
import json
import threading
import time
import uuid
from typing import Dict, List, Optional, Callable, Any

from .logger import log


class CWASClient:
    """向 CWAS（网络空间武器系统）注册自身组件。"""

    def __init__(self, endpoint: str = "", api_key: str = "",
                 enabled: bool = False):
        self.endpoint = endpoint
        self.api_key = api_key
        self.enabled = enabled
        self.component_id = f"wanganzhidun-{uuid.uuid4().hex[:8]}"
        self._registered = False

    def register(self) -> bool:
        if not self.enabled or not self.endpoint:
            log.info("CWAS 未配置，跳过注册")
            return False
        try:
            import requests
            payload = {
                "component_id": self.component_id,
                "name": "网安智盾",
                "path": "存护",
                "ammo_version": "v1",
                "channels": ["12377官网", "举报邮箱", "腾讯卫士",
                             "省网信办备用", "工信部备用"],
                "capabilities": ["防打号", "防点号", "反伤取证", "多通道并发举报"],
            }
            resp = requests.post(
                f"{self.endpoint}/api/v1/components/register",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                self._registered = True
                log.info("CWAS 注册成功")
                return True
            log.warning(f"CWAS 注册失败：{resp.status_code}")
            return False
        except Exception as e:
            log.warning(f"CWAS 注册异常：{e}")
            return False

    def report_event(self, event_type: str, data: dict) -> bool:
        if not self._registered:
            return False
        try:
            import requests
            resp = requests.post(
                f"{self.endpoint}/api/v1/events",
                json={"component_id": self.component_id,
                      "event_type": event_type, "data": data},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def heartbeat(self):
        if not self._registered:
            return
        try:
            import requests
            requests.post(
                f"{self.endpoint}/api/v1/components/{self.component_id}/heartbeat",
                timeout=5,
            )
        except Exception:
            pass


class CoordinationBus:
    """与各命途的协同事件总线。"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, handler: Callable):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def emit(self, event: str, **data):
        for handler in self._handlers.get(event, []):
            try:
                handler(**data)
            except Exception as e:
                log.warning(f"协同事件 {event} 处理异常：{e}")

    def emit_async(self, event: str, **data):
        t = threading.Thread(target=self.emit, args=(event,), kwargs=data, daemon=True)
        t.start()

    def notify_counterstrike(self, ammo_data: dict):
        """反伤触发时通知虚无侧启动干扰。"""
        self.emit_async("counterstrike_triggered", ammo=ammo_data)
        log.info("已通知全频道频带阻塞干扰")

    def notify_defense_failed(self, account: str, platform: str):
        """存护未防住时通知超限卫兵/复活甲。"""
        self.emit_async("defense_failed", account=account, platform=platform)
        log.info("已通知超限卫兵/复活甲")
