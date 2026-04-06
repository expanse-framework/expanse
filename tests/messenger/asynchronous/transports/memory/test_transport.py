from __future__ import annotations

from dataclasses import dataclass

import pytest

from expanse.messenger.asynchronous.transports.memory.transport import MemoryTransport
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp


@dataclass
class FooMessage:
    value: str


def make_transport() -> MemoryTransport:
    return MemoryTransport()


async def test_send_stamps_envelope_with_transport_message_id() -> None:
    transport = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    result = await transport.send(envelope)

    stamp = result.stamp(TransportMessageIdStamp)
    assert stamp is not None
    assert stamp.id == 1


async def test_send_increments_message_id() -> None:
    transport = make_transport()

    first = await transport.send(Envelope.wrap(FooMessage(value="first")))
    second = await transport.send(Envelope.wrap(FooMessage(value="second")))

    assert first.stamp(TransportMessageIdStamp).id == 1  # type: ignore[union-attr]
    assert second.stamp(TransportMessageIdStamp).id == 2  # type: ignore[union-attr]


async def test_sent_returns_decoded_envelopes() -> None:
    transport = make_transport()
    await transport.send(Envelope.wrap(FooMessage(value="hello")))

    sent = transport.sent

    assert len(sent) == 1
    assert isinstance(sent[0].open(), FooMessage)
    assert sent[0].open().value == "hello"  # type: ignore[union-attr]


async def test_receive_returns_available_envelope() -> None:
    transport = make_transport()
    await transport.send(Envelope.wrap(FooMessage(value="hello")))

    envelopes = [e async for e in transport.receive()]

    assert len(envelopes) == 1
    assert isinstance(envelopes[0].open(), FooMessage)


async def test_receive_returns_no_envelopes_when_queue_is_empty() -> None:
    transport = make_transport()

    envelopes = [e async for e in transport.receive()]

    assert envelopes == []


async def test_receive_skips_delayed_envelope() -> None:
    transport = make_transport()
    envelope = Envelope.wrap(FooMessage(value="delayed")).with_stamps(
        DelayStamp(delay=60_000)
    )
    await transport.send(envelope)

    result = [e async for e in transport.receive()]

    assert result == []


async def test_receive_returns_envelope_after_delay_expires() -> None:
    import time

    transport = make_transport()
    envelope = Envelope.wrap(FooMessage(value="delayed")).with_stamps(
        DelayStamp(delay=100)
    )
    await transport.send(envelope)

    assert [e async for e in transport.receive()] == []

    time.sleep(0.15)

    result = [e async for e in transport.receive()]
    assert len(result) == 1
    assert isinstance(result[0].open(), FooMessage)


async def test_acknowledge_removes_envelope_from_queue() -> None:
    transport = make_transport()
    await transport.send(Envelope.wrap(FooMessage(value="hello")))

    envelopes = [e async for e in transport.receive()]
    assert len(envelopes) == 1

    await transport.acknowledge(envelopes[0])

    assert [e async for e in transport.receive()] == []


async def test_acknowledge_raises_when_no_transport_message_id_stamp() -> None:
    transport = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    with pytest.raises(ValueError, match="TransportMessageIdStamp"):
        await transport.acknowledge(envelope)


async def test_reject_removes_envelope_from_queue() -> None:
    transport = make_transport()
    await transport.send(Envelope.wrap(FooMessage(value="hello")))

    envelopes = [e async for e in transport.receive()]
    assert len(envelopes) == 1

    await transport.reject(envelopes[0])

    assert [e async for e in transport.receive()] == []


async def test_reject_raises_when_no_transport_message_id_stamp() -> None:
    transport = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    with pytest.raises(ValueError, match="TransportMessageIdStamp"):
        await transport.reject(envelope)
