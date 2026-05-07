from abc import ABC
from abc import abstractmethod
from collections.abc import AsyncIterator

from expanse.messenger.envelope import Envelope


class Transport(ABC):
    @abstractmethod
    async def send(self, envelope: Envelope) -> Envelope:
        """
        Send the given envelope through the transport.
        :param envelope: The envelope to send.
        :return: The envelope, potentially modified or enriched by the transport.
        """
        ...

    @abstractmethod
    def receive(self) -> AsyncIterator[Envelope]:
        """
        Receive envelopes from the transport.
        :return: An async iterator of received envelopes.
        """

    @abstractmethod
    async def acknowledge(self, envelope: Envelope) -> None:
        """
        Acknowledge the successful processing of the given envelope.
        :param envelope: The envelope to acknowledge.
        """

    @abstractmethod
    async def reject(self, envelope: Envelope) -> None:
        """
        Reject the given envelope, indicating that it could not be processed.
        :param envelope: The envelope to reject.
        """
