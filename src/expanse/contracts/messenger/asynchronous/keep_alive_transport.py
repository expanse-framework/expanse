from abc import ABC
from abc import abstractmethod

from expanse.contracts.messenger.asynchronous.transport import Transport
from expanse.messenger.envelope import Envelope


class KeepAliveTransport(Transport, ABC):
    """
    A transport that keeps the worker alive without actually sending or receiving messages.
    This can be useful for testing or for keeping the worker running when there are no messages to process.
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
