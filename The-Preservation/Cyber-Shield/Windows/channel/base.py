from abc import ABC, abstractmethod
from typing import Any, Tuple


class Channel(ABC):
    name: str = "base"

    @abstractmethod
    def dispatch(self, ammo: Any, draft_path: str) -> Tuple[bool, str]:
        ...

    def healthy(self) -> bool:
        return True
