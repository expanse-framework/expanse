from typing import override

from asgiref.sync import async_to_sync

from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as AsyncMessageBusContract,
)
from expanse.contracts.messenger.synchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.messenger.envelope import Envelope
from expanse.types.messenger import Message


class MessageBus(MessageBusContract):
    def __init__(self, bus: AsyncMessageBusContract) -> None:
        self._bus: AsyncMessageBusContract = bus

    @override
    def dispatch(self, message: Message | Envelope) -> Envelope:
        """
        Dispatch a message through the bus, applying middleware and returning the final envelope.

        :param message: The message, or envelope, to dispatch.
        """
        return async_to_sync(self._bus.dispatch)(message)
