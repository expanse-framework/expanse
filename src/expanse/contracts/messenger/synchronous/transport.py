from abc import ABC
from abc import abstractmethod

from expanse.messenger.envelope import Envelope


class Transport(ABC):
    """
    A transport to which messages are sent synchronously.

    Synchronous transports only send messages: receiving them
    is the job of the asynchronous transports used by workers.
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
        Close the transport and release any resources it holds.
        """
