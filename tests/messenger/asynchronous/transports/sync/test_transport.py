from dataclasses import dataclass

import pytest

from expanse.container.container import Container
from expanse.messenger.asynchronous.transports.sync.transport import SyncTransport
from expanse.messenger.envelope import Envelope
from expanse.messenger.registry import Registry


@dataclass
class FooMessage:
    value: str


def make_transport(
    registry: Registry | None = None,
) -> tuple[SyncTransport, Registry]:
    container = Container()
    reg = registry or Registry()
    return SyncTransport(container, reg), reg


async def test_send_returns_envelope() -> None:
    transport, _ = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    result = await transport.send(envelope)

    assert result is envelope


async def test_send_calls_registered_handler() -> None:
    registry = Registry()
    transport, _ = make_transport(registry)
    received: list[FooMessage] = []

    def handler(message: FooMessage) -> None:
        received.append(message)

    registry.register_handler(handler)
    envelope = Envelope.wrap(FooMessage(value="hello"))

    await transport.send(envelope)

    assert len(received) == 1
    assert received[0].value == "hello"


async def test_send_calls_multiple_handlers() -> None:
    registry = Registry()
    transport, _ = make_transport(registry)
    call_order: list[str] = []

    def first(message: FooMessage) -> None:
        call_order.append("first")

    def second(message: FooMessage) -> None:
        call_order.append("second")

    registry.register_handler(first)
    registry.register_handler(second)
    await transport.send(Envelope.wrap(FooMessage(value="hello")))

    assert call_order == ["first", "second"]


async def test_send_with_no_handlers_returns_envelope() -> None:
    transport, _ = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    result = await transport.send(envelope)

    assert result is envelope


async def test_receive_raises_not_implemented() -> None:
    transport, _ = make_transport()

    with pytest.raises(NotImplementedError):
        await transport.receive()


async def test_acknowledge_raises_not_implemented() -> None:
    transport, _ = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    with pytest.raises(NotImplementedError):
        await transport.acknowledge(envelope)


async def test_reject_raises_not_implemented() -> None:
    transport, _ = make_transport()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    with pytest.raises(NotImplementedError):
        await transport.reject(envelope)
