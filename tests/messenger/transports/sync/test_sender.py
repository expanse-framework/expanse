from dataclasses import dataclass

from expanse.container.container import Container
from expanse.messenger.envelope import Envelope
from expanse.messenger.registry import Registry
from expanse.messenger.transports.sync.sender import SyncSender


@dataclass
class FooMessage:
    value: str


def make_sender(
    registry: Registry | None = None,
) -> tuple[SyncSender, Registry]:
    container = Container()
    reg = registry or Registry()
    return SyncSender(container, reg), reg


async def test_send_returns_envelope() -> None:
    sender, _ = make_sender()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    result = await sender.send(envelope)

    assert result is envelope


async def test_send_calls_registered_handler() -> None:
    registry = Registry()
    sender, _ = make_sender(registry)
    received: list[FooMessage] = []

    def handler(message: FooMessage) -> None:
        received.append(message)

    registry.register_handler(handler)
    envelope = Envelope.wrap(FooMessage(value="hello"))

    await sender.send(envelope)

    assert len(received) == 1
    assert received[0].value == "hello"


async def test_send_calls_multiple_handlers() -> None:
    registry = Registry()
    sender, _ = make_sender(registry)
    call_order: list[str] = []

    def first(message: FooMessage) -> None:
        call_order.append("first")

    def second(message: FooMessage) -> None:
        call_order.append("second")

    registry.register_handler(first)
    registry.register_handler(second)
    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    assert call_order == ["first", "second"]


async def test_send_with_no_handlers_returns_envelope() -> None:
    sender, _ = make_sender()
    envelope = Envelope.wrap(FooMessage(value="hello"))

    result = await sender.send(envelope)

    assert result is envelope
