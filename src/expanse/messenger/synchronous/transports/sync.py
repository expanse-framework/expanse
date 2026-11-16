from expanse.container.container import Container
from expanse.contracts.messenger.synchronous.sender import Sender
from expanse.messenger.envelope import Envelope
from expanse.messenger.registry import Registry
from expanse.support._concurrency import async_to_sync


class SyncSender(Sender):
    def __init__(self, container: Container, registry: Registry) -> None:
        self._container: Container = container
        self._registry: Registry = registry

    def send(self, envelope: Envelope) -> Envelope:
        message = envelope.open()

        handlers = self._registry.get_handlers(type(message))
        for handler in handlers:
            async_to_sync(self._container.call)(handler, message)

        return envelope

    def close(self) -> None:
        pass
