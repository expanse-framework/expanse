from typing import TYPE_CHECKING

from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.contracts.messenger.synchronous.transport import (
    Transport as TransportContract,
)
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp


if TYPE_CHECKING:
    from expanse.types.messenger import EncodedEnvelope


class MemoryTransport(TransportContract):
    def __init__(self, serializer: SerializerContract) -> None:
        self._serializer: SerializerContract = serializer
        self._current_id: int = 0
        self._sent: list[EncodedEnvelope] = []

    @property
    def sent(self) -> list[Envelope]:
        return [self._serializer.decode(encoded) for encoded in self._sent.copy()]

    def send(self, envelope: Envelope) -> Envelope:
        self._current_id += 1
        envelope = envelope.with_stamps(TransportMessageIdStamp(self._current_id))
        self._sent.append(self._serializer.encode(envelope))

        return envelope

    def close(self) -> None:
        self._sent.clear()
