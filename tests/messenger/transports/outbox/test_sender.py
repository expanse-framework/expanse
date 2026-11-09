from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast
from typing import override

import pytest

from expanse.contracts.messenger.asynchronous.sender import Sender
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.memory.queue import MemoryQueue
from expanse.messenger.transports.memory.sender import MemorySender
from expanse.messenger.transports.outbox.sender import OutboxSender


if TYPE_CHECKING:
    from expanse.messenger.serializers.serializer import Serializer
    from expanse.messenger.transports.database.sender import DatabaseSender


@dataclass
class FooMessage:
    value: str


class RecordingSender(Sender):
    def __init__(self) -> None:
        self.sent: list[Envelope] = []
        self.closed: bool = False

    @override
    async def send(self, envelope: Envelope) -> Envelope:
        self.sent.append(envelope)

        return envelope

    @override
    async def close(self) -> None:
        self.closed = True


@pytest.fixture()
def target(serializer: Serializer) -> MemorySender:
    return MemorySender(MemoryQueue(serializer))


@pytest.fixture()
def outbox(serializer: Serializer) -> MemorySender:
    return MemorySender(MemoryQueue(serializer))


@pytest.fixture()
def sender(target: MemorySender, outbox: MemorySender) -> OutboxSender:
    return OutboxSender(
        target_sender=target,
        # The outbox is a database sender in practice: storing messages in memory
        # is enough to check how messages are routed.
        outbox_sender=cast("DatabaseSender", outbox),
        target_transport_name="target",
    )


def test_target_sender_returns_the_decorated_sender(
    sender: OutboxSender, target: MemorySender
) -> None:
    assert sender.target_sender is target


async def test_send_stores_new_messages_in_the_outbox(
    sender: OutboxSender, target: MemorySender, outbox: MemorySender
) -> None:
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    assert target.sent == []
    assert len(outbox.sent) == 1

    stored = outbox.sent[0]
    assert stored.open() == FooMessage(value="hello")
    assert stored.stamp(OutboxStamp) == OutboxStamp(target_transport_name="target")


async def test_send_returns_the_envelope_without_the_outbox_stamp(
    sender: OutboxSender,
) -> None:
    envelope = await sender.send(Envelope.wrap(FooMessage(value="hello")))

    assert not envelope.has_stamp(OutboxStamp)
    assert envelope.open() == FooMessage(value="hello")
    # The stamps added by the outbox sender itself are preserved
    assert envelope.stamp(TransportMessageIdStamp) == TransportMessageIdStamp(1)


async def test_send_keeps_existing_stamps_when_storing_in_the_outbox(
    sender: OutboxSender, outbox: MemorySender
) -> None:
    await sender.send(
        Envelope.wrap(FooMessage(value="hello")).with_stamps(DelayStamp(delay=5000))
    )

    stored = outbox.sent[0]
    assert stored.stamp(DelayStamp) == DelayStamp(delay=5000)
    assert stored.has_stamp(OutboxStamp)


async def test_send_relays_outboxed_messages_to_the_target_transport(
    sender: OutboxSender, target: MemorySender, outbox: MemorySender
) -> None:
    envelope = Envelope.wrap(FooMessage(value="hello")).with_stamps(
        OutboxStamp(target_transport_name="target")
    )

    await sender.send(envelope)

    assert outbox.sent == []
    assert len(target.sent) == 1
    assert target.sent[0].open() == FooMessage(value="hello")
    assert not target.sent[0].has_stamp(OutboxStamp)


async def test_send_strips_outbox_delivery_stamps_when_relaying(
    sender: OutboxSender, target: MemorySender
) -> None:
    envelope = Envelope.wrap(FooMessage(value="hello")).with_stamps(
        OutboxStamp(target_transport_name="target"),
        RedeliveryStamp(retry_count=2),
        DelayStamp(delay=5000),
        SentToFailureTransportStamp(original_transport="outbox"),
        TransportMessageIdStamp(42),
    )

    await sender.send(envelope)

    relayed = target.sent[0]
    assert not relayed.has_stamp(OutboxStamp)
    assert not relayed.has_stamp(RedeliveryStamp)
    assert not relayed.has_stamp(DelayStamp)
    assert not relayed.has_stamp(SentToFailureTransportStamp)
    # Only the identifier of the message in the target transport remains
    assert relayed.stamps(TransportMessageIdStamp) == [TransportMessageIdStamp(1)]


async def test_send_sends_redelivered_messages_directly_to_the_target_transport(
    sender: OutboxSender, target: MemorySender, outbox: MemorySender
) -> None:
    envelope = Envelope.wrap(FooMessage(value="retry")).with_stamps(
        RedeliveryStamp(retry_count=1), DelayStamp(delay=1000)
    )

    await sender.send(envelope)

    assert outbox.sent == []
    assert len(target.sent) == 1

    # Retry metadata must be preserved so the retry strategy keeps working
    relayed = target.sent[0]
    assert relayed.stamp(RedeliveryStamp) is not None
    assert relayed.stamp(RedeliveryStamp).retry_count == 1  # type: ignore[union-attr]
    assert relayed.stamp(DelayStamp) == DelayStamp(delay=1000)
    assert not relayed.has_stamp(OutboxStamp)


async def test_close_is_delegated_to_the_target_sender() -> None:
    target = RecordingSender()
    outbox = RecordingSender()
    sender = OutboxSender(
        target_sender=target,
        outbox_sender=cast("DatabaseSender", outbox),
        target_transport_name="target",
    )

    await sender.close()

    assert target.closed
    assert not outbox.closed
