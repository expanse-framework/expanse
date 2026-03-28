from dataclasses import dataclass

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.asynchronous.transports.memory.transport import MemoryTransport
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.messenger.worker import Worker


@dataclass
class WorkerMessage:
    value: str


@pytest.fixture()
def container() -> Container:
    return Container()


@pytest.fixture()
def middleware_stack() -> MiddlewareStack:
    return MiddlewareStack().use([])


@pytest.fixture()
def registry() -> Registry:
    return Registry()


@pytest.fixture()
def config() -> Config:
    return Config(
        {
            "messenger": {
                "transport": "memory",
                "failure_transport": "failed",
                "transports": {
                    "memory": {
                        "driver": "memory",
                        "retry_strategy": "default",
                    },
                    "failed": {
                        "driver": "memory",
                    },
                },
                "retry_strategies": {
                    "default": {
                        "type": "multiplier",
                        "max_retries": 3,
                        "delay": 10,
                        "multiplier": 2,
                        "jitter": 0.0,
                    }
                },
            }
        }
    )


@pytest.fixture()
def transport_manager(
    container: Container, config: Config, registry: Registry
) -> TransportManager:
    return TransportManager(container, config, registry)


@pytest.fixture()
def worker(
    transport_manager: TransportManager,
    config: Config,
    middleware_stack: MiddlewareStack,
    container: Container,
    registry: Registry,
) -> Worker:
    return Worker(transport_manager, config, middleware_stack, container, registry)


async def test_worker_handles_messages(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    called_values: list[str] = []

    async def handler(message: WorkerMessage) -> None:
        value = getattr(message, "value", None)
        assert isinstance(value, str)
        called_values.append(value)

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    message = WorkerMessage(value="ok")
    await transport.send(Envelope.wrap(message))
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert called_values == [message.value]
    assert await transport.receive() is None


async def test_worker_sends_unrecoverable_failures_to_failure_transport(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    async def handler(_message: WorkerMessage) -> None:
        raise UnrecoverableMessageHandlingError("bad payload")

    transport = await transport_manager.transport("memory")
    failure_transport = await transport_manager.transport("failed")
    assert isinstance(transport, MemoryTransport)
    assert isinstance(failure_transport, MemoryTransport)

    message = WorkerMessage(value="boom")
    await transport.send(Envelope.wrap(message))
    registry.register_handler(handler)

    await worker.run(limit=1)

    sent_to_failure = failure_transport.sent
    assert len(sent_to_failure) == 1
    stamp = sent_to_failure[0].stamp(SentToFailureTransportStamp)
    assert stamp is not None
    assert stamp.original_transport == "memory"


async def test_worker_retries_message_when_retry_strategy_allows_it(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    async def handler(_message: WorkerMessage) -> None:
        raise RuntimeError("transient failure")

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="retry")))
    registry.register_handler(handler)

    await worker.run(limit=1)

    sent = transport.sent
    assert len(sent) == 2

    retried_envelope = sent[1]
    redelivery_stamp = retried_envelope.stamp(RedeliveryStamp)
    assert redelivery_stamp is not None
    assert redelivery_stamp.retry_count == 1

    delay_stamp = retried_envelope.stamp(DelayStamp)
    assert delay_stamp is not None
    assert delay_stamp.delay == 10


async def test_worker_routes_to_failure_transport_when_retries_are_exhausted(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    async def handler(_message: WorkerMessage) -> None:
        raise RuntimeError("permanent failure")

    transport = await transport_manager.transport("memory")
    failure_transport = await transport_manager.transport("failed")
    assert isinstance(transport, MemoryTransport)
    assert isinstance(failure_transport, MemoryTransport)

    redelivered = Envelope.wrap(WorkerMessage(value="done")).with_stamps(
        RedeliveryStamp(retry_count=3)
    )
    await transport.send(redelivered)
    registry.register_handler(handler)

    await worker.run(limit=1)

    failed = failure_transport.sent
    assert len(failed) == 1
    sent_stamp = failed[0].stamp(SentToFailureTransportStamp)
    assert sent_stamp is not None
    assert sent_stamp.original_transport == "memory"
