from expanse.support.service_provider import ServiceProvider


class EventServicerProvider(ServiceProvider):
    """
    Service provider for the event system.
    """

    async def register(self) -> None:
        from expanse.events.dispatcher import AsyncEventDispatcher
        from expanse.events.dispatcher import EventDispatcher

        self._container.singleton(EventDispatcher)
        self._container.singleton(AsyncEventDispatcher)
