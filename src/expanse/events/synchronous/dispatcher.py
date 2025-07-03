import inspect

from collections import defaultdict
from functools import partial

from expanse.container.container import Container
from expanse.contracts.events.dispatcher import AsyncEventDispatcher as Contract
from expanse.contracts.events.event import Event
from expanse.contracts.events.listener import EventListener
from expanse.support._concurrency import run_async_as_sync


class EventDispatcher(Contract):
    def __init__(self, container: Container) -> None:
        self._container = container
        self._listeners: dict[type[object], list[EventListener[object]]] = defaultdict(
            list
        )

    def listen(self, event_type: type[Event], listener: EventListener[Event]) -> None:
        self._listeners[event_type].append(listener)

    def dispatch(self, event: Event, *args: object, **kwargs: object) -> None:
        for listener in self._listeners[type(event)]:
            if isinstance(listener, type) and hasattr(listener, "handle"):
                # Class based listener
                handler = listener.handle
                if inspect.iscoroutinefunction(handler):
                    result = run_async_as_sync(self._dispatch_async, event, listener)
                else:
                    result = run_async_as_sync(self._dispatch_sync, event, listener)
            else:
                # Callable based listener
                if inspect.iscoroutinefunction(listener):
                    result = run_async_as_sync(self._dispatch_async, event, listener)
                else:
                    result = run_async_as_sync(self._dispatch_sync, event, listener)

            if result is False:
                break

    def has_listeners(self, event_type: type[Event]) -> bool:
        return len(self._listeners[event_type]) > 0

    async def _dispatch_sync(
        self, event: Event, listener: type[EventListener[Event]]
    ) -> None:
        if isinstance(listener, type) and hasattr(listener, "handle"):
            listener_instance = await self._container.get(listener)

            listener = partial(listener_instance.handle, event)

            # Resolve dependencies for the listener's handle method
            positional, keywords = await self._container.resolve_callable_dependencies(
                listener
            )

            return listener_instance.handle(event, *positional, **keywords)

        listener = partial(listener, event)
        positional, keywords = await self._container.resolve_callable_dependencies(
            listener
        )

        return listener(positional, keywords)

    async def _dispatch_async(
        self, event: Event, listener: type[EventListener[Event]]
    ) -> None:
        if isinstance(listener, type) and hasattr(listener, "handle"):
            listener_instance = await self._container.get(listener)

            return await self._container.call(listener_instance.handle, event)

        return await self._container.call(listener, event)
