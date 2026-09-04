from abc import ABC
from abc import abstractmethod
from typing import Any


class EventDispatcher(ABC):
    @abstractmethod
    async def dispatch(self, event: Any) -> None: ...

    @abstractmethod
    def dispatch_sync(self, event: Any) -> None: ...
