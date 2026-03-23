from abc import ABC
from abc import abstractmethod

from expanse.messenger.envelope import Envelope
from expanse.types.messenger import Message


class MessageBus(ABC):
    @abstractmethod
    async def dispatch(self, message: Message | Envelope) -> Envelope:
        """
        Dispatch a message through the bus, applying middleware and returning the final envelope.
        :param message: The message, or envelope, to dispatch.
        """
