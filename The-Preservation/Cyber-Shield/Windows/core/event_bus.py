"""事件总线：模块间解耦通信。"""

from typing import Any, Callable, Dict, List


class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, handler: Callable):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable):
        handlers = self._handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: str, **data):
        for handler in self._handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                import logging
                logging.warning(f"事件处理异常 {event}: {e}")

    def clear(self):
        self._handlers.clear()
