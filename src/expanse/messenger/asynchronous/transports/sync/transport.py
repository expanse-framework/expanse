from collections.abc import AsyncIterator

from expanse.container.container import Container
from expanse.messenger.envelope import Envelope
from expanse.messenger.registry import Registry


class SyncTransport:
    def __init__(self, container: Container, registry: Registry) -> None:
        self._container: Container = container
        self._registry: Registry = registry

    async def send(self, envelope: Envelope) -> Envelope:
        message = envelope.open()

        handlers = self._registry.get_handlers(type(message))
        for handler in handlers:
            await self._container.call(handler, message)

        return envelope

    async def receive(self) -> AsyncIterator[Envelope]:
        raise NotImplementedError("SyncTransport does not support receiving messages.")
        yield  # pragma: no cover

    async def acknowledge(self, envelope: Envelope) -> None:
        raise NotImplementedError(
            "SyncTransport does not support acknowledging messages."
        )

    async def reject(self, envelope: Envelope) -> None:
        raise NotImplementedError("SyncTransport does not support rejecting messages.")
