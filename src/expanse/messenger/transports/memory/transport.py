from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from expanse.contracts.messenger.asynchronous.transport import (
    Transport as TransportContract,
)
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp


if TYPE_CHECKING:
    from expanse.types.messenger import EncodedEnvelope


class MemoryTransport(TransportContract):
    def __init__(self, serializer: SerializerContract) -> None:
        self._serializer: SerializerContract = serializer
        self._current_id: int = 0
        self._sent: list[EncodedEnvelope] = []
        self._acknowledged: list[EncodedEnvelope] = []
        self._rejected: list[EncodedEnvelope] = []
        self._available_at: dict[int, datetime] = {}
        self._queue: dict[int, EncodedEnvelope] = {}
        self._in_flight: set[int] = set()

    @property
    def sent(self) -> list[Envelope]:
        return [self._serializer.decode(encoded) for encoded in self._sent.copy()]

    async def send(self, envelope: Envelope) -> Envelope:
        self._current_id += 1
        envelope = envelope.with_stamps(TransportMessageIdStamp(self._current_id))
        encoded_envelope = self._serializer.encode(envelope)
        self._sent.append(encoded_envelope)
        self._queue[self._current_id] = encoded_envelope

        delay_stamp = envelope.stamp(DelayStamp)
        if delay_stamp is not None:
            self._available_at[self._current_id] = datetime.now(UTC) + timedelta(
                milliseconds=delay_stamp.delay
            )

        return envelope

    async def receive(self) -> AsyncIterator[Envelope]:
        for message_id, encoded_envelope in list(self._queue.items()):
            if message_id in self._in_flight:
                # Already handed out to a consumer and not yet acknowledged
                # or rejected: skip it so concurrent consumers don't claim
                # the same message.
                continue

            if (
                message_id not in self._available_at
                or datetime.now(UTC) >= self._available_at[message_id]
            ):
                self._in_flight.add(message_id)

                yield self._serializer.decode(encoded_envelope).with_stamps(
                    TransportMessageIdStamp(message_id)
                )

    async def acknowledge(self, envelope: Envelope) -> None:
        encoded_envelope = self._serializer.encode(envelope)
        self._acknowledged.append(encoded_envelope)

        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            raise ValueError(
                "Envelope must have a TransportMessageIdStamp to be acknowledged."
            )

        self._queue.pop(message_id_stamp.id, None)
        self._available_at.pop(message_id_stamp.id, None)
        self._in_flight.discard(message_id_stamp.id)

    async def reject(self, envelope: Envelope) -> None:
        encoded_envelope = self._serializer.encode(envelope)
        self._rejected.append(encoded_envelope)

        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            raise ValueError(
                "Envelope must have a TransportMessageIdStamp to be rejected."
            )

        self._queue.pop(message_id_stamp.id, None)
        self._available_at.pop(message_id_stamp.id, None)
        self._in_flight.discard(message_id_stamp.id)

    async def close(self) -> None:
        self._sent.clear()
        self._acknowledged.clear()
        self._rejected.clear()
        self._available_at.clear()
        self._queue.clear()
        self._in_flight.clear()
