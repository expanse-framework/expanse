from typing import override

from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.messenger.asynchronous.middleware.middleware import Middleware
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.envelope import Envelope
from expanse.support.asynchronous.pipeline import Pipeline
from expanse.types.messenger import Message


class MessageBus(MessageBusContract):
    def __init__(
        self, transport_manager: TransportManager, container: Container
    ) -> None:
        self._container: Container = container
        self._transport_manager: TransportManager = transport_manager
        self._middleware: list[type[Middleware]] = []

    @override
    async def dispatch(self, message: Message | Envelope) -> Envelope:
        """
        Dispatch a message through the bus, applying middleware and returning the final envelope.
        :param message: The message, or envelope, to dispatch.
        """
        envelope = Envelope.wrap(message)
        transport = self._transport_manager.transport()

        pipeline = Pipeline[Envelope, Envelope]()

        pipeline.use(
            [(await self._container.get(mw)).handle for mw in self._middleware]
        )

        return await pipeline.send(envelope).to(transport.send)

    def append_middleware(self, middleware: type[Middleware]) -> None:
        self._middleware.append(middleware)
