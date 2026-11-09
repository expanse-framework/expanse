from __future__ import annotations

import asyncio

from dataclasses import dataclass

import pytest

from expanse.messenger.envelope import Envelope
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.memory.queue import MemoryQueue
from expanse.messenger.transports.memory.receiver import MemoryReceiver
from expanse.messenger.transports.memory.sender import MemorySender
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer


@dataclass
class FooMessage:
    value: str


def make_transport() -> tuple[MemorySender, MemoryReceiver]:
    serialization_manager = SerializationManager()
    serialization_manager.register_serializer(DataclassSerializer())

    queue = MemoryQueue(Serializer(serialization_manager))

    return MemorySender(queue), MemoryReceiver(queue)


async def test_send_stamps_envelope_with_transport_message_id() -> None:
    sender, _ = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    result = await sender.send(envelope)

    stamp = result.stamp(TransportMessageIdStamp)
    assert stamp is not None
    assert stamp.id == 1


async def test_send_increments_message_id() -> None:
    sender, _ = make_transport()

    first = await sender.send(Envelope.wrap(FooMessage(value="first")))
    second = await sender.send(Envelope.wrap(FooMessage(value="second")))

    first_stamp = first.stamp(TransportMessageIdStamp)
    second_stamp = second.stamp(TransportMessageIdStamp)

    assert first_stamp is not None
    assert second_stamp is not None

    assert first_stamp.id == 1
    assert second_stamp.id == 2


async def test_sent_returns_decoded_envelopes() -> None:
    sender, _ = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    sent = sender.sent

    assert len(sent) == 1

    message = sent[0].open()
    assert isinstance(message, FooMessage)
    assert message.value == "hello"


async def test_receive_returns_available_envelope() -> None:
    sender, receiver = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    envelopes = [e async for e in receiver.receive()]

    assert len(envelopes) == 1
    assert isinstance(envelopes[0].open(), FooMessage)


async def test_receive_returns_no_envelopes_when_queue_is_empty() -> None:
    _, receiver = make_transport()

    envelopes = [e async for e in receiver.receive()]

    assert envelopes == []


async def test_receive_skips_delayed_envelope() -> None:
    sender, receiver = make_transport()
    envelope = Envelope.wrap(FooMessage(value="delayed")).with_stamps(
        DelayStamp(delay=60_000)
    )
    await sender.send(envelope)

    result = [e async for e in receiver.receive()]

    assert result == []


async def test_receive_returns_envelope_after_delay_expires() -> None:
    sender, receiver = make_transport()
    envelope = Envelope.wrap(FooMessage(value="delayed")).with_stamps(
        DelayStamp(delay=100)
    )
    await sender.send(envelope)

    assert [e async for e in receiver.receive()] == []

    await asyncio.sleep(0.15)

    result = [e async for e in receiver.receive()]
    assert len(result) == 1
    assert isinstance(result[0].open(), FooMessage)


async def test_acknowledge_removes_envelope_from_queue() -> None:
    sender, receiver = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    envelopes = [e async for e in receiver.receive()]
    assert len(envelopes) == 1

    await receiver.acknowledge(envelopes[0])

    assert [e async for e in receiver.receive()] == []


async def test_acknowledge_raises_when_no_transport_message_id_stamp() -> None:
    _, receiver = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    with pytest.raises(ValueError, match="TransportMessageIdStamp"):
        await receiver.acknowledge(envelope)


async def test_reject_removes_envelope_from_queue() -> None:
    sender, receiver = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    envelopes = [e async for e in receiver.receive()]
    assert len(envelopes) == 1

    await receiver.reject(envelopes[0])

    assert [e async for e in receiver.receive()] == []


async def test_reject_raises_when_no_transport_message_id_stamp() -> None:
    _, receiver = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    with pytest.raises(ValueError, match="TransportMessageIdStamp"):
        await receiver.reject(envelope)


async def test_receive_does_not_return_in_flight_envelope_again() -> None:
    sender, receiver = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    first = [e async for e in receiver.receive()]
    assert len(first) == 1

    second = [e async for e in receiver.receive()]
    assert second == []


async def test_acknowledge_clears_in_flight_tracking() -> None:
    sender, receiver = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    first = [e async for e in receiver.receive()]
    assert len(first) == 1
    assert receiver.queue._in_flight

    await receiver.acknowledge(first[0])

    assert receiver.queue._in_flight == set()


async def test_reject_clears_in_flight_tracking() -> None:
    sender, receiver = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    first = [e async for e in receiver.receive()]
    assert len(first) == 1
    assert receiver.queue._in_flight

    await receiver.reject(first[0])

    assert receiver.queue._in_flight == set()


async def test_sender_and_receiver_sharing_a_queue_see_the_same_messages() -> None:
    sender, receiver = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    envelopes = [e async for e in receiver.receive()]
    await receiver.acknowledge(envelopes[0])

    assert len(sender.queue.sent) == 1
    assert len(receiver.queue.acknowledged) == 1
    assert receiver.queue.rejected == []


async def test_closing_clears_the_queue() -> None:
    sender, receiver = make_transport()
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    await receiver.close()

    assert sender.sent == []
    assert [e async for e in receiver.receive()] == []
