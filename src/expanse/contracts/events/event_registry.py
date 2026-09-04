from abc import ABC
from abc import abstractmethod

from expanse.types.events import EventListener


class EventRegistry(ABC):
    @abstractmethod
    def add_listener[EventT](
        self, event_type: type[EventT], listener: EventListener[EventT]
    ) -> None: ...

    @abstractmethod
    def remove_listener[EventT](
        self, event_type: type[EventT], listener: EventListener[EventT]
    ) -> None: ...

    @abstractmethod
    def get_listeners[EventT](
        self, event_type: type[EventT]
    ) -> list[EventListener[EventT]]: ...

    @abstractmethod
    def has_listeners[EventT](self, event_type: type[EventT]) -> bool: ...
