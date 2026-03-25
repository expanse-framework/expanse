from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.messenger.asynchronous.message_bus import MessageBus
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.asynchronous.transports.memory.transport import MemoryTransport
from expanse.messenger.envelope import Envelope
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry


@pytest.fixture()
def container() -> Container:
    return Container()


@pytest.fixture()
def config() -> Config:
    config = Config(
        {
            "messenger": {
                "transport": "memory",
                "transports": {
                    "memory": {"driver": "memory"},
                },
            }
        }
    )

    return config


@pytest.fixture()
def registry() -> Registry:
    return Registry()


@pytest.fixture()
def transport_manager(
    container: Container, config: Config, registry: Registry
) -> TransportManager:
    return TransportManager(container, config, registry)


@pytest.fixture()
def middleware_stack() -> MiddlewareStack:
    return MiddlewareStack()


@pytest.fixture()
def bus(
    container: Container,
    transport_manager: TransportManager,
    middleware_stack: MiddlewareStack,
) -> MessageBus:
    return MessageBus(transport_manager, container, middleware_stack)


@dataclass
class MyMessage:
    foo: str


async def test_dispatching_messages_calls_transport(
    bus: MessageBus, transport_manager: TransportManager
) -> None:
    message = MyMessage(foo="bar")
    await bus.dispatch(message)

    transport = transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport), (
        "Expected transport to be a MemoryTransport"
    )

    sent_envelopes = transport.sent
    assert len(sent_envelopes) == 1, "Expected exactly one envelope to be sent"
    assert sent_envelopes[0].open() == message, (
        "The sent envelope should contain the original message"
    )


async def test_dispatching_messages_calls_middleware(
    bus: MessageBus, middleware_stack: MiddlewareStack
) -> None:
    @dataclass
    class BeforeStamp:
        value: str

    @dataclass
    class AfterStamp:
        value: str

    class MyMiddleware:
        async def handle(
            self,
            envelope: Envelope,
            next_call: Callable[[Envelope], Awaitable[Envelope]],
        ) -> Envelope:
            result = await next_call(envelope.with_stamps(BeforeStamp(value="before")))

            return result.with_stamps(AfterStamp(value="after"))

    middleware_stack.append(MyMiddleware)

    message = MyMessage(foo="baz")
    envelope = await bus.dispatch(message)

    assert envelope.is_stamped(), "Expected the envelope to be stamped"
    before_stamp = envelope.stamp(BeforeStamp)
    assert before_stamp is not None, "Expected the envelope to have the MyStamp stamp"
    assert before_stamp.value == "before"
    after_stamp = envelope.stamp(AfterStamp)
    assert after_stamp is not None, "Expected the envelope to have the MyStamp stamp"
    assert after_stamp.value == "after"
