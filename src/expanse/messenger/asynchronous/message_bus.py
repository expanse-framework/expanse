from typing import override

from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.envelope import Envelope
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.support.asynchronous.pipeline import Pipeline
from expanse.types.messenger import Message


class MessageBus(MessageBusContract):
    def __init__(
        self,
        transport_manager: TransportManager,
        container: Container,
        middleware_stack: MiddlewareStack,
    ) -> None:
        self._container: Container = container
        self._transport_manager: TransportManager = transport_manager
        self._middleware_stack: MiddlewareStack = middleware_stack

    @override
    async def dispatch(self, message: Message | Envelope) -> Envelope:
        """
        Dispatch a message through the bus, applying middleware and returning the final envelope.

        :param message: The message, or envelope, to dispatch.
        """
        envelope = Envelope.wrap(message)
        transport = await self._transport_manager.transport()

        pipeline = Pipeline[Envelope, Envelope]()

        pipeline.use(
            [
                (await self._container.get(mw)).handle
                for mw in self._middleware_stack.middleware
            ]
        )

        return await pipeline.send(envelope).to(transport.send)
