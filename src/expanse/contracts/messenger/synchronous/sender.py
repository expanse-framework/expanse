from abc import ABC
from abc import abstractmethod

from expanse.messenger.envelope import Envelope


class Sender(ABC):
    """
    Send messages to a transport synchronously.

    Receiving messages is the job of the asynchronous receivers used by workers.
    """

    @abstractmethod
    def send(self, envelope: Envelope) -> Envelope:
        """
        Send the given envelope through the transport.
        :param envelope: The envelope to send.
        :return: The envelope, potentially modified or enriched by the transport.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """
        Close the sender and release any resources it holds.
        """
