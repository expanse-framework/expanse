from collections.abc import Callable
from dataclasses import dataclass

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.messenger.envelope import Envelope
from expanse.messenger.registry import Registry
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.synchronous.message_bus import MessageBus
from expanse.messenger.synchronous.middleware.middleware import Middleware
from expanse.messenger.synchronous.transport_manager import TransportManager
from expanse.messenger.synchronous.transports.memory import MemorySender
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer


@pytest.fixture()
def container() -> Container:
    return Container()


@pytest.fixture()
def serializer() -> Serializer:
    serialization_manager = SerializationManager()
    serialization_manager.register_serializer(DataclassSerializer())

    return Serializer(serialization_manager)


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
    registry = Registry()
    return registry


@pytest.fixture()
def transport_manager(
    container: Container, config: Config, registry: Registry, serializer: Serializer
) -> TransportManager:
    return TransportManager(container, config, registry, serializer)


@pytest.fixture()
def middleware() -> list[Middleware]:
    return []


@pytest.fixture()
def bus(
    transport_manager: TransportManager, middleware: list[Middleware]
) -> MessageBus:
    return MessageBus(transport_manager, middleware)


@pytest.fixture()
def transport(transport_manager: TransportManager) -> MemorySender:
    transport = transport_manager.sender("memory")

    assert isinstance(transport, MemorySender)

    return transport


@dataclass
class MyMessage:
    foo: str


def test_dispatching_messages_calls_transport(
    bus: MessageBus, transport: MemorySender
) -> None:
    message = MyMessage(foo="bar")
    bus.dispatch(message)

    sent_envelopes = transport.sent
    assert len(sent_envelopes) == 1, "Expected exactly one envelope to be sent"
    assert sent_envelopes[0].open() == message, (
        "The sent envelope should contain the original message"
    )


def test_dispatching_messages_calls_middleware(
    bus: MessageBus, middleware: list[Middleware]
) -> None:
    @dataclass
    class BeforeStamp:
        value: str

    @dataclass
    class AfterStamp:
        value: str

    class MyMiddleware:
        def handle(
            self,
            envelope: Envelope,
            next_call: Callable[[Envelope], Envelope],
        ) -> Envelope:
            result = next_call(envelope.with_stamps(BeforeStamp(value="before")))

            return result.with_stamps(AfterStamp(value="after"))

    middleware.append(MyMiddleware())

    message = MyMessage(foo="baz")
    envelope = bus.dispatch(message)

    assert envelope.is_stamped(), "Expected the envelope to be stamped"
    before_stamp = envelope.stamp(BeforeStamp)
    assert before_stamp is not None, "Expected the envelope to have the MyStamp stamp"
    assert before_stamp.value == "before"
    after_stamp = envelope.stamp(AfterStamp)
    assert after_stamp is not None, "Expected the envelope to have the MyStamp stamp"
    assert after_stamp.value == "after"
