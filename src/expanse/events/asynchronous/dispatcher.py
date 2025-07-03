from collections import defaultdict
from functools import partial

from expanse.container.container import Container
from expanse.contracts.events.dispatcher import AsyncEventDispatcher as Contract
from expanse.contracts.events.event import Event
from expanse.contracts.events.listener import EventListener


class EventDispatcher(Contract):
    def __init__(self, container: Container) -> None:
        self._container = container
        self._listeners: dict[type[object], list[EventListener[object]]] = defaultdict(
            list
        )

    def listen(self, event_type: type[Event], listener: EventListener[Event]) -> None:
        self._listeners[event_type].append(listener)

    async def dispatch(self, event: Event, *args: object, **kwargs: object) -> None:
        for listener in self._listeners[type(event)]:
            if isinstance(listener, type) and hasattr(listener, "handle"):
                # Class based listener
                listener_instance = await self._container.get(listener)

                result = await self._container.call(
                    partial(listener_instance.handle, event)
                )
            else:
                # Callable based listener
                result = await self._container.call(listener)

            if result is False:
                break

    def has_listeners(self, event_type: type[Event]) -> bool:
        return len(self._listeners[event_type]) > 0
