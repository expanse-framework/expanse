from collections.abc import AsyncIterator
from typing import override

from expanse.contracts.messenger.asynchronous.transport import (
    Transport as TransportContract,
)
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)


class OutboxTransport(TransportContract):
    def __init__(
        self,
        target_transport: TransportContract,
        outbox_transport: TransportContract,
        target_transport_name: str,
    ) -> None:
        self._target_transport: TransportContract = target_transport
        self._outbox_transport: TransportContract = outbox_transport
        self._target_transport_name: str = target_transport_name

    @property
    def target_transport(self) -> TransportContract:
        return self._target_transport

    @override
    async def send(self, envelope: Envelope) -> Envelope:
        if envelope.has_stamp(OutboxStamp):
            # If the envelope has an OutboxStamp, send it to the target transport
            return await self._target_transport.send(
                envelope.without_stamps(
                    OutboxStamp,
                    RedeliveryStamp,
                    DelayStamp,
                    SentToFailureTransportStamp,
                )
            )

        if envelope.has_stamp(RedeliveryStamp):
            return await self._target_transport.send(envelope)

        return (
            await self._outbox_transport.send(
                envelope.with_stamps(
                    OutboxStamp(target_transport_name=self._target_transport_name)
                )
            )
        ).without_stamps(OutboxStamp)

    @override
    def receive(self) -> AsyncIterator[Envelope]:
        return self._target_transport.receive()

    @override
    async def acknowledge(self, envelope: Envelope) -> None:
        return await self._target_transport.acknowledge(envelope)

    @override
    async def reject(self, envelope: Envelope) -> None:
        return await self._target_transport.reject(envelope)

    @override
    async def close(self) -> None:
        return await self._target_transport.close()
