from abc import ABC
from abc import abstractmethod
from typing import Any

from expanse.queue.asynchronous.queues.queue import AsyncQueue


class AsyncConnector(ABC):
    """
    Base class for asynchronous connectors.
    """

    @abstractmethod
    async def connect(self, config: Any) -> AsyncQueue:
        """
        Connect to the queue.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the queue.
        """
        ...
