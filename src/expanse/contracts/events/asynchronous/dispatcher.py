from abc import ABC
from abc import abstractmethod

from expanse.contracts.events.event import Event
from expanse.contracts.events.listener import EventListener


class AsyncEventDispatcher(ABC):
    @abstractmethod
    def listen(self, event_type: type[Event], listener: EventListener[Event]) -> None:
        """
        Register a listener for a specific event type.

        :param event_type: The type of event to listen for.
        :param listener: The listener to will handle the event.
        """
        ...

    @abstractmethod
    async def dispatch(self, event: Event, *args: object, **kwargs: object) -> None:
        """
        Dispatch an event to all registered listeners.

        :param event: The event to dispatch.
        :param args: Additional positional arguments to pass to the listeners.
        :param kwargs: Additional keyword arguments to pass to the listeners.
        """
        ...

    @abstractmethod
    def has_listeners(self, event_type: type[Event]) -> bool:
        """
        Check if there are any listeners registered for a specific event type.

        :param event_type: The type of event to check for listeners.
        :return: True if there are listeners registered, False otherwise.
        """
        ...
