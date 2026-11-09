from abc import ABC
from abc import abstractmethod

from expanse.contracts.messenger.asynchronous.receiver import Receiver
from expanse.messenger.envelope import Envelope


class KeepAliveReceiver(Receiver, ABC):
    """
    A receiver that can be told that a message is still being processed,
    so that it is not redelivered in the meantime.
    """

    @abstractmethod
    async def keep_alive(self, envelope: Envelope, duration: int | None = None) -> None:
        """
        Inform the transport that the worker is still alive and processing the message.

        :param envelope: The envelope being processed.
        :param duration: The duration in seconds to keep the message alive.

        :raises TransportError: If the transport encounters an error while trying to keep the message alive.
        """
        ...
