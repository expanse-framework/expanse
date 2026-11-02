from typing import override

from expanse.contracts.messenger.synchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.transport import TransportStamp
from expanse.messenger.synchronous.middleware.middleware import Middleware
from expanse.messenger.synchronous.transport_manager import TransportManager
from expanse.support.synchronous.pipeline import Pipeline
from expanse.types.messenger import Message


class MessageBus(MessageBusContract):
    def __init__(
        self,
        transport_manager: TransportManager,
        middleware: list[Middleware],
    ) -> None:
        self._transport_manager: TransportManager = transport_manager
        self._middleware: list[Middleware] = middleware

    @override
    def dispatch(self, message: Message | Envelope) -> Envelope:
        """
        Dispatch a message through the bus, applying middleware and returning the final envelope.

        :param message: The message, or envelope, to dispatch.
        """
        envelope = Envelope.wrap(message)
        transport_stamp = envelope.stamp(TransportStamp)
        transport_name = transport_stamp.name if transport_stamp else None
        transport = self._transport_manager.transport(transport_name)

        pipeline = Pipeline[Envelope, Envelope]()
        pipeline.use([mw.handle for mw in self._middleware])

        return pipeline.send(envelope).to(transport.send).run()
