from collections import defaultdict
from typing import Any

from expanse.contracts.events.event_registry import (
    EventRegistry as EventRegistryContract,
)
from expanse.types.events import EventListener


class EventRegistry(EventRegistryContract):
    def __init__(self):
        self._listeners: dict[type[Any], list[EventListener[Any]]] = defaultdict(list)

    def add_listener[EventT](
        self, event_type: type[EventT], listener: EventListener[EventT]
    ) -> None:
        self._listeners[event_type].append(listener)

    def remove_listener[EventT](
        self, event_type: type[EventT], listener: EventListener[EventT]
    ) -> None:
        if event_type in self._listeners:
            self._listeners[event_type].remove(listener)

    def get_listeners[EventT](
        self, event_type: type[EventT]
    ) -> list[EventListener[EventT]]:
        return self._listeners.get(event_type, [])

    def has_listeners[EventT](self, event_type: type[EventT]) -> bool:
        return event_type in self._listeners and len(self._listeners[event_type]) > 0
