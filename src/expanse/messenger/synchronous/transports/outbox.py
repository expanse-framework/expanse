from typing import override

from expanse.contracts.messenger.synchronous.sender import Sender as SenderContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.synchronous.transports.database import DatabaseSender


class OutboxSender(SenderContract):
    """
    Store messages in an outbox, from which workers relay them to the target transport.
    """

    def __init__(
        self,
        target_sender: SenderContract,
        outbox_sender: DatabaseSender,
        target_transport_name: str,
    ) -> None:
        self._target_sender: SenderContract = target_sender
        self._outbox_sender: DatabaseSender = outbox_sender
        self._target_transport_name: str = target_transport_name

    @property
    def target_sender(self) -> SenderContract:
        return self._target_sender

    @property
    def outbox_sender(self) -> DatabaseSender:
        return self._outbox_sender

    @override
    def send(self, envelope: Envelope) -> Envelope:
        return self._outbox_sender.send(
            envelope.with_stamps(
                OutboxStamp(target_transport_name=self._target_transport_name)
            )
        ).without_stamps(OutboxStamp)

    @override
    def close(self) -> None:
        self._target_sender.close()
