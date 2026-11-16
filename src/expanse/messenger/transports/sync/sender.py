from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.sender import Sender
from expanse.messenger.envelope import Envelope
from expanse.messenger.registry import Registry


class SyncSender(Sender):
    """
    Handle messages right away, upon dispatch.
    """

    def __init__(self, container: Container, registry: Registry) -> None:
        self._container: Container = container
        self._registry: Registry = registry

    async def send(self, envelope: Envelope) -> Envelope:
        message = envelope.open()

        handlers = self._registry.get_handlers(type(message))
        for handler in handlers:
            await self._container.call(handler, message)

        return envelope

    async def close(self) -> None:
        pass
