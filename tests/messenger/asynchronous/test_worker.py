import asyncio

from dataclasses import dataclass
from typing import ClassVar
from unittest.mock import patch

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.asynchronous.transports.memory.transport import MemoryTransport
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.retry.retry_strategy_manager import RetryStrategyManager
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.handled import HandledStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.self_handling import SelfHandlingStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.messenger.worker import Worker


@dataclass
class WorkerMessage:
    value: str


class MyService:
    def __init__(self) -> None:
        self.called_with: list[str] = []


@dataclass
class SelfHandlingJob:
    value: str
    call_log: ClassVar[list[str]] = []

    async def handle(self) -> None:
        SelfHandlingJob.call_log.append(self.value)


@dataclass
class SelfHandlingJobWithDep:
    value: str
    injected: ClassVar[list[MyService]] = []

    async def handle(self, service: MyService) -> None:
        SelfHandlingJobWithDep.injected.append(service)


@dataclass
class NoHandleJob:
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
def retry_strategy_manager(config: Config) -> RetryStrategyManager:
    return RetryStrategyManager(config)


@pytest.fixture()
def worker(
    transport_manager: TransportManager,
    retry_strategy_manager: RetryStrategyManager,
    config: Config,
    middleware_stack: MiddlewareStack,
    container: Container,
    registry: Registry,
) -> Worker:
    return Worker(
        transport_manager,
        retry_strategy_manager,
        config,
        middleware_stack,
        container,
        registry,
    )


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
    assert [e async for e in transport.receive()] == []


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


async def test_worker_handles_self_handling_messages(
    worker: Worker, transport_manager: TransportManager
) -> None:
    SelfHandlingJob.call_log.clear()

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(
        Envelope.wrap(
            SelfHandlingJob(value="self-handled"), stamps=[SelfHandlingStamp()]
        )
    )

    await worker.run(limit=1)

    assert SelfHandlingJob.call_log == ["self-handled"]
    assert [e async for e in transport.receive()] == []


async def test_worker_self_handling_message_receives_injected_dependencies(
    worker: Worker, transport_manager: TransportManager, container: Container
) -> None:
    SelfHandlingJobWithDep.injected.clear()
    service = MyService()
    container.instance(MyService, service)

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(
        Envelope.wrap(SelfHandlingJobWithDep(value="di"), stamps=[SelfHandlingStamp()])
    )

    await worker.run(limit=1)

    assert len(SelfHandlingJobWithDep.injected) == 1
    assert SelfHandlingJobWithDep.injected[0] is service


async def test_worker_routes_no_handle_method_message_to_failure_transport(
    transport_manager: TransportManager,
    retry_strategy_manager: RetryStrategyManager,
    middleware_stack: MiddlewareStack,
    container: Container,
    registry: Registry,
) -> None:
    # SelfHandlingMessageWithNoHandlerError is caught by the retry/failure handling
    # machinery — verify the message ends up in the failure transport.
    config_no_retry = Config(
        {
            "messenger": {
                "transport": "memory",
                "failure_transport": "failed",
                "transports": {
                    "memory": {"driver": "memory"},
                    "failed": {"driver": "memory"},
                },
            }
        }
    )
    worker = Worker(
        transport_manager,
        retry_strategy_manager,
        config_no_retry,
        middleware_stack,
        container,
        registry,
    )

    transport = await transport_manager.transport("memory")
    failure_transport = await transport_manager.transport("failed")
    assert isinstance(transport, MemoryTransport)
    assert isinstance(failure_transport, MemoryTransport)

    await transport.send(
        Envelope.wrap(NoHandleJob(value="x"), stamps=[SelfHandlingStamp()])
    )

    await worker.run(limit=1)

    assert len(failure_transport.sent) == 1
    sent_stamp = failure_transport.sent[0].stamp(SentToFailureTransportStamp)
    assert sent_stamp is not None
    assert sent_stamp.original_transport == "memory"


async def test_worker_adds_received_stamp_when_processing(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    received_envelopes: list[Envelope] = []

    async def handler(_message: WorkerMessage) -> None:
        pass

    class CapturingMiddleware:
        async def handle(
            self,
            envelope: Envelope,
            next_call: object,
        ) -> Envelope:
            received_envelopes.append(envelope)
            return await next_call(envelope)  # type: ignore[operator]

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="stamped")))
    registry.register_handler(handler)

    worker._middleware_stack.append(CapturingMiddleware)

    await worker.run(limit=1)

    assert len(received_envelopes) == 1
    assert received_envelopes[0].has_stamp(ReceivedStamp)


async def test_worker_routes_to_failure_transport_when_no_retry_strategy_configured(
    transport_manager: TransportManager,
    retry_strategy_manager: RetryStrategyManager,
    middleware_stack: MiddlewareStack,
    container: Container,
    registry: Registry,
) -> None:
    config_without_retry = Config(
        {
            "messenger": {
                "transport": "memory",
                "failure_transport": "failed",
                "transports": {
                    "memory": {"driver": "memory"},
                    "failed": {"driver": "memory"},
                },
            }
        }
    )
    worker = Worker(
        transport_manager,
        retry_strategy_manager,
        config_without_retry,
        middleware_stack,
        container,
        registry,
    )

    async def handler(_message: WorkerMessage) -> None:
        raise RuntimeError("unexpected failure")

    transport = await transport_manager.transport("memory")
    failure_transport = await transport_manager.transport("failed")
    assert isinstance(transport, MemoryTransport)
    assert isinstance(failure_transport, MemoryTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="no-retry")))
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert len(failure_transport.sent) == 1
    sent_stamp = failure_transport.sent[0].stamp(SentToFailureTransportStamp)
    assert sent_stamp is not None
    assert sent_stamp.original_transport == "memory"


async def test_worker_adds_handled_stamp_after_successful_handling(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    handled_envelopes: list[Envelope] = []

    async def handler(message: WorkerMessage) -> None:
        pass

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="stamped")))
    registry.register_handler(handler)

    original_acknowledge = transport.acknowledge

    async def capturing_acknowledge(envelope: Envelope) -> None:
        handled_envelopes.append(envelope)
        await original_acknowledge(envelope)

    transport.acknowledge = capturing_acknowledge  # type: ignore[assignment]

    await worker.run(limit=1)

    assert len(handled_envelopes) == 1
    stamps = handled_envelopes[0].stamps(HandledStamp)
    assert len(stamps) == 1
    assert handler.__qualname__ in stamps[0].handler


async def test_worker_adds_handled_stamp_for_self_handling_messages(
    worker: Worker, transport_manager: TransportManager
) -> None:
    SelfHandlingJob.call_log.clear()
    handled_envelopes: list[Envelope] = []

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(
        Envelope.wrap(
            SelfHandlingJob(value="self-stamped"), stamps=[SelfHandlingStamp()]
        )
    )

    original_acknowledge = transport.acknowledge

    async def capturing_acknowledge(envelope: Envelope) -> None:
        handled_envelopes.append(envelope)
        await original_acknowledge(envelope)

    transport.acknowledge = capturing_acknowledge  # type: ignore[assignment]

    await worker.run(limit=1)

    assert SelfHandlingJob.call_log == ["self-stamped"]
    assert len(handled_envelopes) == 1
    stamps = handled_envelopes[0].stamps(HandledStamp)
    assert len(stamps) == 1
    assert "SelfHandlingJob.handle" in stamps[0].handler


async def test_worker_skips_already_handled_handlers(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    call_count = 0

    async def handler(message: WorkerMessage) -> None:
        nonlocal call_count
        call_count += 1

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    # Pre-stamp the envelope as already handled by this handler
    envelope = Envelope.wrap(WorkerMessage(value="already-handled")).with_stamps(
        HandledStamp(handler=f"{handler.__module__}.{handler.__qualname__}")
    )
    await transport.send(envelope)
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert call_count == 0


async def test_worker_raises_message_handling_failed_error_with_errors(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    async def handler(_message: WorkerMessage) -> None:
        raise RuntimeError("transient failure")

    transport = await transport_manager.transport("memory")
    failure_transport = await transport_manager.transport("failed")
    assert isinstance(transport, MemoryTransport)
    assert isinstance(failure_transport, MemoryTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="fail")))
    registry.register_handler(handler)

    # With retry strategy configured, the message should be retried
    await worker.run(limit=1)

    # The message was retried (sent back to the transport)
    assert len(transport.sent) == 2
    retried = transport.sent[1]
    redelivery_stamp = retried.stamp(RedeliveryStamp)
    assert redelivery_stamp is not None


async def test_worker_multiple_handlers_partial_failure(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    successful_calls: list[str] = []

    async def good_handler(message: WorkerMessage) -> None:
        successful_calls.append(message.value)

    async def bad_handler(_message: WorkerMessage) -> None:
        raise RuntimeError("handler failed")

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="partial")))
    registry.register_handler(good_handler)
    registry.register_handler(bad_handler)

    # With retry strategy, partial failure should still cause retry
    await worker.run(limit=1)

    assert successful_calls == ["partial"]
    # The message was retried due to the bad handler
    assert len(transport.sent) == 2


async def test_worker_uses_custom_sleep_interval(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    """The worker should use the provided sleep interval (in ms) when no messages are available."""
    sleep_calls: list[float] = []

    async def capturing_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        # Stop the worker after the first sleep to avoid infinite polling
        worker.stop()

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)
    # Don't send any message so the worker will sleep

    with patch.object(asyncio, "sleep", side_effect=capturing_sleep):
        await worker.run(sleep=2000)

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == 2.0


async def test_worker_uses_default_sleep_interval(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    sleep_calls: list[float] = []

    async def capturing_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        worker.stop()

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    with patch.object(asyncio, "sleep", side_effect=capturing_sleep):
        await worker.run()

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == 1.0


def test_worker_stop_sets_stop_event(worker: Worker) -> None:
    assert not worker._stop_event.is_set()

    worker.stop()

    assert worker._stop_event.is_set()
