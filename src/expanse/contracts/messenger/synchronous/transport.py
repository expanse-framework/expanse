from collections.abc import Iterable
from typing import Protocol

from expanse.messenger.envelope import Envelope


class Transport(Protocol):
    def send(self, envelope: Envelope) -> Envelope:
        """
        Send the given envelope through the transport.
        :param envelope: The envelope to send.
        :return: The envelope, potentially modified or enriched by the transport.
        """
        ...

    def receive(self) -> Iterable[Envelope]:
        """
        Receive envelopes from the transport.
        :return: An iterable of received envelopes.
        """
        ...

    def acknowledge(self, envelope: Envelope) -> None:
        """
        Acknowledge the successful processing of the given envelope.
        :param envelope: The envelope to acknowledge.
        """
        ...

    def reject(self, envelope: Envelope) -> None:
        """
        Reject the given envelope, indicating that it could not be processed.
        :param envelope: The envelope to reject.
        """
        ...
