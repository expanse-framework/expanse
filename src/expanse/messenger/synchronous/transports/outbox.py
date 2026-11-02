from typing import override

from expanse.contracts.messenger.synchronous.transport import (
    Transport as TransportContract,
)
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.synchronous.transports.database import DatabaseTransport


class OutboxTransport(TransportContract):
    """
    Store messages in an outbox, from which workers relay them to the target transport.
    """

    def __init__(
        self,
        target_transport: TransportContract,
        outbox_transport: DatabaseTransport,
        target_transport_name: str,
    ) -> None:
        self._target_transport: TransportContract = target_transport
        self._outbox_transport: DatabaseTransport = outbox_transport
        self._target_transport_name: str = target_transport_name

    @property
    def target_transport(self) -> TransportContract:
        return self._target_transport

    @property
    def outbox_transport(self) -> DatabaseTransport:
        return self._outbox_transport

    @override
    def send(self, envelope: Envelope) -> Envelope:
        return self._outbox_transport.send(
            envelope.with_stamps(
                OutboxStamp(target_transport_name=self._target_transport_name)
            )
        ).without_stamps(OutboxStamp)

    @override
    def close(self) -> None:
        self._target_transport.close()
