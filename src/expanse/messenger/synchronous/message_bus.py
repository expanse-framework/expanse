from typing import override

from asgiref.sync import async_to_sync

from expanse.contracts.messenger.synchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.messenger.asynchronous.message_bus import MessageBus as AsyncMessageBus
from expanse.messenger.asynchronous.middleware.middleware import Middleware
from expanse.messenger.envelope import Envelope
from expanse.types.messenger import Message


class MessageBus(MessageBusContract):
    def __init__(self, bus: AsyncMessageBus) -> None:
        self._bus: AsyncMessageBus = bus

    @override
    def dispatch(self, message: Message | Envelope) -> Envelope:
        """
        Dispatch a message through the bus, applying middleware and returning the final envelope.

        :param message: The message, or envelope, to dispatch.
        """
        return async_to_sync(self._bus.dispatch)(message)

    def append_middleware(self, middleware: type[Middleware]) -> None:
        self._bus.append_middleware(middleware)
