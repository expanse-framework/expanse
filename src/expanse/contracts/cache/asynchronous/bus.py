from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any


class Bus(ABC):
    @abstractmethod
    async def publish(self, message: Any) -> None:
        """
        Publish a message to the bus.

        :param message: The message to be published.
        """

    @abstractmethod
    def subscribe(
        self, handler: Callable[[Any], None] | Callable[[Any], Awaitable[None]]
    ) -> None:
        """
        Subscribe a handler to the bus.

        :param handler: The handler to be subscribed.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Close the bus and release any resources.
        """
