from abc import ABC
from abc import abstractmethod

from expanse.messenger.envelope import Envelope


class Sender(ABC):
    """
    Send messages to a transport.
    """

    @abstractmethod
    async def send(self, envelope: Envelope) -> Envelope:
        """
        Send the given envelope through the transport.
        :param envelope: The envelope to send.
        :return: The envelope, potentially modified or enriched by the transport.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """
        Close the sender and release any resources it holds.
        """
