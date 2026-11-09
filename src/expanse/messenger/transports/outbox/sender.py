from typing import override

from expanse.contracts.messenger.asynchronous.sender import Sender as SenderContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.database.sender import DatabaseSender


class OutboxSender(SenderContract):
    """
    Store messages in an outbox, from which workers relay them to the target transport.

    Messages are received from the target transport directly:
    an outbox has no receiver of its own.
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
    async def send(self, envelope: Envelope) -> Envelope:
        if envelope.has_stamp(OutboxStamp):
            # If the envelope has an OutboxStamp, it is relayed from the outbox:
            # send it to the target transport without the stamps tied to its stay
            # in the outbox.
            return await self._target_sender.send(
                envelope.without_stamps(
                    OutboxStamp,
                    RedeliveryStamp,
                    DelayStamp,
                    SentToFailureTransportStamp,
                    TransportMessageIdStamp,
                )
            )

        if envelope.has_stamp(RedeliveryStamp):
            # Messages are received from the target transport,
            # so they are retried on it as well.
            return await self._target_sender.send(envelope)

        return (
            await self._outbox_sender.send(
                envelope.with_stamps(
                    OutboxStamp(target_transport_name=self._target_transport_name)
                )
            )
        ).without_stamps(OutboxStamp)

    @override
    async def close(self) -> None:
        await self._target_sender.close()
