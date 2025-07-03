from typing import Any
from typing import Literal
from typing import Protocol

from expanse.contracts.events.event import Event


class AsyncClassEventListener(Protocol[Event]):
    """
    Class based event listener.
    """

    async def handle(
        self, event: Event, *args: Any, **kwargs: Any
    ) -> None | Literal[False]:
        """
        Handle the event.

        :param event: The event to handle.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: None if the event was handled, False to stop the propagation of the event.
        """
        ...


class AsyncCallableEventListener(Protocol[Event]):
    """
    Callable based event listener.
    """

    async def __call__(
        self, event: Event, *args: Any, **kwargs: Any
    ) -> None | Literal[False]:
        """
        Handle the event.

        :param event: The event to handle.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: None if the event was handled, False to stop the propagation of the event.
        """
        ...


type AsyncEventListener[Event] = (
    AsyncCallableEventListener[Event] | type[AsyncClassEventListener[Event]]
)


__all__ = ["AsyncEventListener"]
