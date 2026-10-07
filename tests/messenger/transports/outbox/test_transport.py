from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import override

import pytest

from expanse.contracts.messenger.asynchronous.transport import Transport
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.memory.transport import MemoryTransport
from expanse.messenger.transports.outbox.transport import OutboxTransport


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from expanse.messenger.serializers.serializer import Serializer


@dataclass
class FooMessage:
    value: str


class RecordingTransport(Transport):
    def __init__(self, queue: list[Envelope] | None = None) -> None:
        self.queue: list[Envelope] = queue or []
        self.sent: list[Envelope] = []
        self.acknowledged: list[Envelope] = []
        self.rejected: list[Envelope] = []
        self.closed: bool = False

    @override
    async def send(self, envelope: Envelope) -> Envelope:
        self.sent.append(envelope)

        return envelope

    @override
    async def receive(self) -> AsyncIterator[Envelope]:
        while self.queue:
            yield self.queue.pop(0)

    @override
    async def acknowledge(self, envelope: Envelope) -> None:
        self.acknowledged.append(envelope)

    @override
    async def reject(self, envelope: Envelope) -> None:
        self.rejected.append(envelope)

    @override
    async def close(self) -> None:
        self.closed = True


@pytest.fixture()
def target(serializer: Serializer) -> MemoryTransport:
    return MemoryTransport(serializer)


@pytest.fixture()
def outbox(serializer: Serializer) -> MemoryTransport:
    return MemoryTransport(serializer)


@pytest.fixture()
def transport(target: MemoryTransport, outbox: MemoryTransport) -> OutboxTransport:
    return OutboxTransport(
        target_transport=target,
        outbox_transport=outbox,
        target_transport_name="target",
    )


def test_target_transport_returns_the_decorated_transport(
    transport: OutboxTransport, target: MemoryTransport
) -> None:
    assert transport.target_transport is target


async def test_send_stores_new_messages_in_the_outbox(
    transport: OutboxTransport, target: MemoryTransport, outbox: MemoryTransport
) -> None:
    await transport.send(Envelope.wrap(FooMessage(value="hello")))

    assert target.sent == []
    assert len(outbox.sent) == 1

    stored = outbox.sent[0]
    assert stored.open() == FooMessage(value="hello")
    assert stored.stamp(OutboxStamp) == OutboxStamp(target_transport_name="target")


async def test_send_returns_the_envelope_without_the_outbox_stamp(
    transport: OutboxTransport,
) -> None:
    envelope = await transport.send(Envelope.wrap(FooMessage(value="hello")))

    assert not envelope.has_stamp(OutboxStamp)
    assert envelope.open() == FooMessage(value="hello")
    # The stamps added by the outbox transport itself are preserved
    assert envelope.stamp(TransportMessageIdStamp) == TransportMessageIdStamp(1)


async def test_send_keeps_existing_stamps_when_storing_in_the_outbox(
    transport: OutboxTransport, outbox: MemoryTransport
) -> None:
    await transport.send(
        Envelope.wrap(FooMessage(value="hello")).with_stamps(DelayStamp(delay=5000))
    )

    stored = outbox.sent[0]
    assert stored.stamp(DelayStamp) == DelayStamp(delay=5000)
    assert stored.has_stamp(OutboxStamp)


async def test_send_relays_outboxed_messages_to_the_target_transport(
    transport: OutboxTransport, target: MemoryTransport, outbox: MemoryTransport
) -> None:
    envelope = Envelope.wrap(FooMessage(value="hello")).with_stamps(
        OutboxStamp(target_transport_name="target")
    )

    await transport.send(envelope)

    assert outbox.sent == []
    assert len(target.sent) == 1
    assert target.sent[0].open() == FooMessage(value="hello")
    assert not target.sent[0].has_stamp(OutboxStamp)


async def test_send_strips_outbox_delivery_stamps_when_relaying(
    transport: OutboxTransport, target: MemoryTransport
) -> None:
    envelope = Envelope.wrap(FooMessage(value="hello")).with_stamps(
        OutboxStamp(target_transport_name="target"),
        RedeliveryStamp(retry_count=2),
        DelayStamp(delay=5000),
        SentToFailureTransportStamp(original_transport="outbox"),
    )

    await transport.send(envelope)

    relayed = target.sent[0]
    assert not relayed.has_stamp(OutboxStamp)
    assert not relayed.has_stamp(RedeliveryStamp)
    assert not relayed.has_stamp(DelayStamp)
    assert not relayed.has_stamp(SentToFailureTransportStamp)


async def test_send_sends_redelivered_messages_directly_to_the_target_transport(
    transport: OutboxTransport, target: MemoryTransport, outbox: MemoryTransport
) -> None:
    envelope = Envelope.wrap(FooMessage(value="retry")).with_stamps(
        RedeliveryStamp(retry_count=1), DelayStamp(delay=1000)
    )

    await transport.send(envelope)

    assert outbox.sent == []
    assert len(target.sent) == 1

    # Retry metadata must be preserved so the retry strategy keeps working
    relayed = target.sent[0]
    assert relayed.stamp(RedeliveryStamp) is not None
    assert relayed.stamp(RedeliveryStamp).retry_count == 1  # type: ignore[union-attr]
    assert relayed.stamp(DelayStamp) == DelayStamp(delay=1000)
    assert not relayed.has_stamp(OutboxStamp)


async def test_receive_consumes_from_the_target_transport(
    transport: OutboxTransport, target: MemoryTransport, outbox: MemoryTransport
) -> None:
    await outbox.send(Envelope.wrap(FooMessage(value="in-outbox")))
    await target.send(Envelope.wrap(FooMessage(value="in-target")))

    received = [envelope.open() async for envelope in transport.receive()]

    assert received == [FooMessage(value="in-target")]


async def test_acknowledge_reject_and_close_are_delegated_to_the_target_transport() -> (
    None
):
    target = RecordingTransport()
    outbox = RecordingTransport()
    transport = OutboxTransport(
        target_transport=target,
        outbox_transport=outbox,
        target_transport_name="target",
    )

    acknowledged = Envelope.wrap(FooMessage(value="ack"))
    rejected = Envelope.wrap(FooMessage(value="reject"))

    await transport.acknowledge(acknowledged)
    await transport.reject(rejected)
    await transport.close()

    assert target.acknowledged == [acknowledged]
    assert target.rejected == [rejected]
    assert target.closed

    assert outbox.acknowledged == []
    assert outbox.rejected == []
    assert not outbox.closed
