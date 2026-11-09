from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp


if TYPE_CHECKING:
    from collections.abc import Iterator

    from expanse.types.messenger import EncodedEnvelope


class MemoryQueue:
    """
    Store messages in memory.

    It is shared by the sender and the receiver of a memory transport.
    """

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
        return self._decode(self._sent)

    @property
    def acknowledged(self) -> list[Envelope]:
        return self._decode(self._acknowledged)

    @property
    def rejected(self) -> list[Envelope]:
        return self._decode(self._rejected)

    def push(self, envelope: Envelope) -> Envelope:
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

    def pull(self) -> "Iterator[Envelope]":
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

    def acknowledge(self, envelope: Envelope) -> None:
        self._acknowledged.append(self._serializer.encode(envelope))

        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            raise ValueError(
                "Envelope must have a TransportMessageIdStamp to be acknowledged."
            )

        self._remove(message_id_stamp.id)

    def reject(self, envelope: Envelope) -> None:
        self._rejected.append(self._serializer.encode(envelope))

        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            raise ValueError(
                "Envelope must have a TransportMessageIdStamp to be rejected."
            )

        self._remove(message_id_stamp.id)

    def clear(self) -> None:
        self._sent.clear()
        self._acknowledged.clear()
        self._rejected.clear()
        self._available_at.clear()
        self._queue.clear()
        self._in_flight.clear()

    def _remove(self, message_id: int) -> None:
        self._queue.pop(message_id, None)
        self._available_at.pop(message_id, None)
        self._in_flight.discard(message_id)

    def _decode(self, encoded_envelopes: "list[EncodedEnvelope]") -> list[Envelope]:
        return [self._serializer.decode(encoded) for encoded in encoded_envelopes]
