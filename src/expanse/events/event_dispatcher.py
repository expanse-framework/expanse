from typing import Any

from expanse.container.container import Container
from expanse.contracts.events.event_dispatcher import (
    EventDispatcher as EventDispatcherContract,
)
from expanse.contracts.events.event_registry import EventRegistry
from expanse.support._concurrency import async_to_sync


class EventDispatcher(EventDispatcherContract):
    def __init__(self, container: Container, registry: EventRegistry) -> None:
        self._container: Container = container
        self._registry: EventRegistry = registry

    async def dispatch(self, event: Any) -> None:
        event_type = type(event)
        for listener in self._registry.get_listeners(event_type):
            await self._container.call(listener, event)

    def dispatch_sync(self, event: Any) -> None:
        event_type = type(event)

        for listener in self._registry.get_listeners(event_type):
            async_to_sync(self._container.call)(listener, event)
