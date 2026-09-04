from expanse.contracts.events.event_dispatcher import (
    EventDispatcher as EventDispatcherContract,
)
from expanse.contracts.events.event_registry import (
    EventRegistry as EventRegistryContract,
)
from expanse.support.service_provider import ServiceProvider


class EventsServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.events.event_dispatcher import EventDispatcher
        from expanse.events.event_registry import EventRegistry

        self._container.singleton(EventRegistryContract, EventRegistry)
        self._container.scoped(EventDispatcherContract, EventDispatcher)
