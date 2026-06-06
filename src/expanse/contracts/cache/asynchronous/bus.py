from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import TypeVar


_T = TypeVar("_T")


class Bus(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        """
        Get the unique identifier of the bus.
        """

    @abstractmethod
    async def publish(self, message: Any) -> None:
        """
        Publish a message to the bus.

        :param message: The message to be published.
        """

    @abstractmethod
    def subscribe(
        self,
        message: type[_T],
        handler: Callable[[_T], None] | Callable[[_T], Awaitable[None]],
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
