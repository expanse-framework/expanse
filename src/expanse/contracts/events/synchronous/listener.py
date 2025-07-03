from typing import Any
from typing import Literal
from typing import Protocol

from expanse.contracts.events.event import Event


class ClassEventListener(Protocol[Event]):
    """
    Class based event listener.
    """

    def handle(self, event: Event, *args: Any, **kwargs: Any) -> None | Literal[False]:
        """
        Handle the event.

        :param event: The event to handle.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: None if the event was handled, False to stop the propagation of the event.
        """
        ...


class CallableEventListener(Protocol[Event]):
    """
    Callable based event listener.
    """

    def __call__(
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


type EventListener[Event] = (
    CallableEventListener[Event] | type[ClassEventListener[Event]]
)
