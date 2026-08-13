import asyncio
import logging

from collections.abc import AsyncIterator
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from typing import ClassVar
from typing import Protocol
from typing import cast
from typing import override
from unittest.mock import patch

import pytest

from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore
from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract
from expanse.contracts.messenger.asynchronous.keep_alive_transport import (
    KeepAliveTransport,
)
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.jobs.asynchronous.job import Job as AsyncJob
from expanse.jobs.stamps.job import JobStamp
from expanse.logging.context import Context
from expanse.logging.filters.context import ContextFilter
from expanse.logging.utils import _set_context
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.locks.unique import UniqueLock
from expanse.messenger.middleware.handle_failed_decoding import HandleFailedDecoding
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.middleware.propagate_context import PropagateContext
from expanse.messenger.registry import Registry
from expanse.messenger.retry.retry_strategy_manager import RetryStrategyManager
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.stamps.context import ContextStamp
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.handled import HandledStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.messenger.transports.memory.transport import MemoryTransport
from expanse.messenger.transports.transport_manager import TransportManager
from expanse.messenger.worker import Worker
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer
from expanse.serialization.serializers.pickle import PickleSerializer
from expanse.support._utils import class_to_name


class ContextLogRecord(Protocol):
    context: dict[str, Any]


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addFilter(ContextFilter())


class FakeKeepAliveTransport(KeepAliveTransport):
    def __init__(self) -> None:
        self._queue: list[Envelope] = []
        self.sent: list[Envelope] = []
        self.acknowledged: list[Envelope] = []
        self.rejected: list[Envelope] = []
        self.keep_alive_calls: list[tuple[Envelope, int | None]] = []
        self._next_id: int = 1
        self.closed: bool = False

    def enqueue(self, envelope: Envelope) -> Envelope:
        stamped = envelope.with_stamps(TransportMessageIdStamp(id=self._next_id))
        self._next_id += 1
        self._queue.append(stamped)
        return stamped

    async def send(self, envelope: Envelope) -> Envelope:
        stamped = envelope.with_stamps(TransportMessageIdStamp(id=self._next_id))
        self._next_id += 1
        self.sent.append(stamped)
        return stamped

    async def receive(self) -> AsyncIterator[Envelope]:
        while self._queue:
            yield self._queue.pop(0)

    async def acknowledge(self, envelope: Envelope) -> None:
        self.acknowledged.append(envelope)

    async def reject(self, envelope: Envelope) -> None:
        self.rejected.append(envelope)

    async def keep_alive(self, envelope: Envelope, duration: int | None = None) -> None:
        self.keep_alive_calls.append((envelope, duration))

    async def close(self) -> None:
        self.closed = True


class FlappingLeaseTransport(KeepAliveTransport):
    """A transport whose single message can become available again while
    still in flight, simulating a lease/redelivery-timeout expiring before
    a sibling consumer slot has finished handling it."""

    def __init__(self) -> None:
        self._envelope: Envelope | None = None
        self.available: bool = True
        self.acknowledged: list[Envelope] = []
        self.rejected: list[Envelope] = []
        self.keep_alive_calls: list[Envelope] = []

    def enqueue(self, envelope: Envelope) -> Envelope:
        stamped = envelope.with_stamps(TransportMessageIdStamp(id=1))
        self._envelope = stamped
        return stamped

    async def send(self, envelope: Envelope) -> Envelope:
        return envelope

    async def receive(self) -> AsyncIterator[Envelope]:
        if self._envelope is not None and self.available:
            self.available = False
            yield self._envelope

    async def acknowledge(self, envelope: Envelope) -> None:
        self.acknowledged.append(envelope)
        self._envelope = None

    async def reject(self, envelope: Envelope) -> None:
        self.rejected.append(envelope)
        self._envelope = None

    async def keep_alive(self, envelope: Envelope, duration: int | None = None) -> None:
        self.keep_alive_calls.append(envelope)

    async def close(self) -> None:
        pass


@dataclass
class WorkerMessage:
    value: str


class MyService:
    def __init__(self) -> None:
        self.called_with: list[str] = []


class ProcessJob(AsyncJob[WorkerMessage]):
    call_log: ClassVar[list[str]] = []

    @override
    async def execute(self) -> None:
        ProcessJob.call_log.append(self.payload.value)


class ProcessJobWithDep(AsyncJob[WorkerMessage]):
    injected: ClassVar[list[MyService]] = []

    @override
    async def execute(self, service: MyService) -> None:
        ProcessJobWithDep.injected.append(service)


class FakeScopedSession:
    pass


async def _create_fake_scoped_session() -> AsyncIterator[FakeScopedSession]:
    yield FakeScopedSession()
    # Simulates a failure while tearing down a scoped dependency, e.g. a
    # database session raising while being closed.
    raise RuntimeError("boom during scoped session teardown")


class ProcessJobWithScopedSession(AsyncJob[WorkerMessage]):
    call_log: ClassVar[list[str]] = []

    @override
    async def execute(self, session: FakeScopedSession) -> None:
        ProcessJobWithScopedSession.call_log.append(self.payload.value)


@dataclass
class NotAJob:
    payload: WorkerMessage
    instantiations: ClassVar[list[WorkerMessage]] = []

    def __post_init__(self) -> None:
        NotAJob.instantiations.append(self.payload)


def context_setter_handler(message: WorkerMessage, context: Context) -> None:
    context["foo"] = "baz"
    context["message_value"] = message.value

    logger.info("Setting log context")


def logging_handler(message: WorkerMessage) -> None:
    logger.info("Handling message with context.")


@pytest.fixture()
async def container() -> Container:
    from expanse.logging.logging_service_provider import LoggingServiceProvider

    container = Container()
    await LoggingServiceProvider(container).register()

    serialization_manager = SerializationManager()
    serialization_manager.register_serializer(DataclassSerializer())
    serialization_manager.register_serializer(
        PickleSerializer().restrict({class_to_name(MessageDecodingFailedError)})
    )
    container.instance(SerializerContract, Serializer(serialization_manager))

    return container


@pytest.fixture()
def middleware_stack() -> MiddlewareStack:
    return MiddlewareStack().use([])


@pytest.fixture()
def registry() -> Registry:
    registry = Registry()
    return registry


@pytest.fixture()
def context() -> Generator[Context]:
    context = Context()
    _set_context(context)

    yield context

    _set_context(None)


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
                        "delay": 1,
                        "multiplier": 2,
                        "jitter": 0.0,
                    }
                },
            }
        }
    )


@pytest.fixture()
def transport_manager(
    container: Container,
    config: Config,
    registry: Registry,
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
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
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
    assert caplog.messages[0] == "Message WorkerMessage handled successfully."


async def test_worker_sends_unrecoverable_failures_to_failure_transport(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)

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

    assert caplog.messages[:2] == [
        "Message handling failed with an unrecoverable error, removing from transport. Error: Message handling failed for message <class 'method'>: bad payload",
        "Sending rejected message to failure transport: failed",
    ]


async def test_worker_retries_message_when_retry_strategy_allows_it(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    caplog: LogCaptureFixture,
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
    assert delay_stamp.delay == 1

    assert (
        caplog.messages[0]
        == "Message handling failed, sending for retry 1 with a delay of 1s. Error: Message handling failed for message <class 'method'>: transient failure"
    )


async def test_worker_routes_to_failure_transport_when_retries_are_exhausted(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    caplog: LogCaptureFixture,
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

    assert (
        caplog.messages[0]
        == "Message handling failed after 3 retries. Error: Message handling failed for message <class 'method'>: permanent failure"
    )


async def test_worker_handles_job_messages(
    worker: Worker, transport_manager: TransportManager
) -> None:
    ProcessJob.call_log.clear()

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    payload = WorkerMessage(value="processed")
    await transport.send(
        Envelope.wrap(payload, stamps=[JobStamp(class_to_name(ProcessJob))])
    )

    await worker.run(limit=1)

    assert ProcessJob.call_log == ["processed"]
    assert [e async for e in transport.receive()] == []


async def test_worker_job_receives_injected_dependencies(
    worker: Worker, transport_manager: TransportManager, container: Container
) -> None:
    ProcessJobWithDep.injected.clear()
    service = MyService()
    container.instance(MyService, service)

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    payload = WorkerMessage(value="di")
    await transport.send(
        Envelope.wrap(payload, stamps=[JobStamp(class_to_name(ProcessJobWithDep))])
    )

    await worker.run(limit=1)

    assert len(ProcessJobWithDep.injected) == 1
    assert ProcessJobWithDep.injected[0] is service


async def test_worker_does_not_retry_job_when_only_scope_teardown_fails(
    worker: Worker,
    transport_manager: TransportManager,
    container: Container,
    caplog: LogCaptureFixture,
) -> None:
    """A failure while tearing down a scoped dependency (e.g. closing a
    database session) must not be mistaken for the job itself having
    failed -- otherwise an already-successful job gets retried and its
    side effects run again."""
    caplog.set_level(logging.ERROR)
    ProcessJobWithScopedSession.call_log.clear()
    container.scoped(FakeScopedSession, _create_fake_scoped_session)

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(
        Envelope.wrap(
            WorkerMessage(value="once"),
            stamps=[JobStamp(class_to_name(ProcessJobWithScopedSession))],
        )
    )

    await worker.run(limit=1)

    assert ProcessJobWithScopedSession.call_log == ["once"]
    assert len(transport._acknowledged) == 1
    assert transport._rejected == []
    assert "Error while terminating the scoped container" in caplog.text


async def test_worker_routes_invalid_job_class_to_failure_transport(
    transport_manager: TransportManager,
    retry_strategy_manager: RetryStrategyManager,
    middleware_stack: MiddlewareStack,
    container: Container,
    registry: Registry,
) -> None:
    # A JobStamp pointing to a class that is not a Job subclass raises TypeError,
    # which is caught by the failure machinery and sent to the failure transport.
    NotAJob.instantiations.clear()

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

    payload = WorkerMessage(value="x")
    await transport.send(
        Envelope.wrap(payload, stamps=[JobStamp(class_to_name(NotAJob))])
    )

    await worker.run(limit=1)

    assert NotAJob.instantiations == []

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

    transport.acknowledge = capturing_acknowledge  # type: ignore[method-assign]

    await worker.run(limit=1)

    assert len(handled_envelopes) == 1
    stamps = handled_envelopes[0].stamps(HandledStamp)
    assert len(stamps) == 1
    assert handler.__qualname__ in stamps[0].handler


async def test_worker_adds_handled_stamp_for_job_messages(
    worker: Worker, transport_manager: TransportManager
) -> None:
    ProcessJob.call_log.clear()
    handled_envelopes: list[Envelope] = []

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    payload = WorkerMessage(value="stamped")
    await transport.send(
        Envelope.wrap(payload, stamps=[JobStamp(class_to_name(ProcessJob))])
    )

    original_acknowledge = transport.acknowledge

    async def capturing_acknowledge(envelope: Envelope) -> None:
        handled_envelopes.append(envelope)
        await original_acknowledge(envelope)

    transport.acknowledge = capturing_acknowledge  # type: ignore[method-assign]

    await worker.run(limit=1)

    assert ProcessJob.call_log == ["stamped"]
    assert len(handled_envelopes) == 1
    stamps = handled_envelopes[0].stamps(HandledStamp)
    assert len(stamps) == 1
    assert "ProcessJob.execute" in stamps[0].handler


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


def _make_keep_alive_worker(
    container: Container,
    middleware_stack: MiddlewareStack,
    registry: Registry,
    fake_transport: FakeKeepAliveTransport,
    *,
    with_retry: bool = False,
) -> tuple[Worker, TransportManager]:
    transports_config: dict[str, Any] = {
        "keep_alive": {"driver": "memory"},
        "failed": {"driver": "memory"},
    }
    retry_strategies: dict[str, Any] = {}
    if with_retry:
        transports_config["keep_alive"]["retry_strategy"] = "default"
        retry_strategies["default"] = {
            "type": "multiplier",
            "max_retries": 3,
            "delay": 10,
            "multiplier": 2,
            "jitter": 0.0,
        }

    cfg = Config(
        {
            "messenger": {
                "transport": "keep_alive",
                "failure_transport": "failed",
                "transports": transports_config,
                "retry_strategies": retry_strategies,
            }
        }
    )
    tm = TransportManager(container, cfg, registry)
    tm._transports["keep_alive"] = fake_transport
    worker = Worker(
        tm,
        RetryStrategyManager(cfg),
        cfg,
        middleware_stack,
        container,
        registry,
    )
    return worker, tm


async def test_worker_tracks_keep_alives_for_keep_alive_transport(
    container: Container,
    middleware_stack: MiddlewareStack,
    registry: Registry,
) -> None:
    fake_transport = FakeKeepAliveTransport()
    worker, _ = _make_keep_alive_worker(
        container, middleware_stack, registry, fake_transport
    )

    captured: dict[int, tuple[str, Envelope]] = {}

    async def handler(message: WorkerMessage) -> None:
        captured.update(worker._keep_alives)

    envelope = fake_transport.enqueue(Envelope.wrap(WorkerMessage(value="tracked")))
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert len(captured) == 1
    transport_name, tracked_envelope = next(iter(captured.values()))
    assert transport_name == "keep_alive"
    assert tracked_envelope is envelope


async def test_worker_clears_keep_alives_after_successful_handling(
    container: Container,
    middleware_stack: MiddlewareStack,
    registry: Registry,
) -> None:
    fake_transport = FakeKeepAliveTransport()
    worker, _ = _make_keep_alive_worker(
        container, middleware_stack, registry, fake_transport
    )

    async def handler(_message: WorkerMessage) -> None:
        pass

    fake_transport.enqueue(Envelope.wrap(WorkerMessage(value="ok")))
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert worker._keep_alives == {}


async def test_worker_clears_keep_alives_after_retry(
    container: Container,
    middleware_stack: MiddlewareStack,
    registry: Registry,
) -> None:
    fake_transport = FakeKeepAliveTransport()
    worker, _ = _make_keep_alive_worker(
        container, middleware_stack, registry, fake_transport, with_retry=True
    )

    async def handler(_message: WorkerMessage) -> None:
        raise RuntimeError("transient")

    fake_transport.enqueue(Envelope.wrap(WorkerMessage(value="retry")))
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert worker._keep_alives == {}


async def test_worker_clears_keep_alives_after_unrecoverable_failure(
    container: Container,
    middleware_stack: MiddlewareStack,
    registry: Registry,
) -> None:
    fake_transport = FakeKeepAliveTransport()
    worker, _ = _make_keep_alive_worker(
        container, middleware_stack, registry, fake_transport
    )

    async def handler(_message: WorkerMessage) -> None:
        raise UnrecoverableMessageHandlingError("bad")

    fake_transport.enqueue(Envelope.wrap(WorkerMessage(value="unrecoverable")))
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert worker._keep_alives == {}


async def test_worker_clears_keep_alives_after_rejection_without_retry(
    container: Container,
    middleware_stack: MiddlewareStack,
    registry: Registry,
) -> None:
    fake_transport = FakeKeepAliveTransport()
    # No retry strategy configured → failure goes straight to failure transport
    worker, _ = _make_keep_alive_worker(
        container, middleware_stack, registry, fake_transport, with_retry=False
    )

    async def handler(_message: WorkerMessage) -> None:
        raise RuntimeError("no retry configured")

    fake_transport.enqueue(Envelope.wrap(WorkerMessage(value="no-retry")))
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert worker._keep_alives == {}


async def test_worker_does_not_track_keep_alives_for_regular_transport(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    async def handler(_message: WorkerMessage) -> None:
        pass

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)
    assert not isinstance(transport, KeepAliveTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="plain")))
    registry.register_handler(handler)

    await worker.run(limit=1)

    assert worker._keep_alives == {}


async def test_worker_keep_alive_calls_transport_keep_alive(
    worker: Worker, transport_manager: TransportManager
) -> None:
    fake_transport = FakeKeepAliveTransport()
    transport_manager._transports["keep_alive"] = fake_transport

    envelope = Envelope.wrap(WorkerMessage(value="alive")).with_stamps(
        TransportMessageIdStamp(id=42)
    )
    worker._keep_alives[id(envelope.open())] = ("keep_alive", envelope)

    await worker.keep_alive()

    assert len(fake_transport.keep_alive_calls) == 1
    assert fake_transport.keep_alive_calls[0] == (envelope, None)


async def test_worker_keep_alive_passes_duration_to_transport(
    worker: Worker, transport_manager: TransportManager
) -> None:
    fake_transport = FakeKeepAliveTransport()
    transport_manager._transports["keep_alive"] = fake_transport

    envelope = Envelope.wrap(WorkerMessage(value="duration")).with_stamps(
        TransportMessageIdStamp(id=7)
    )
    worker._keep_alives[id(envelope.open())] = ("keep_alive", envelope)

    await worker.keep_alive(duration=30)

    assert fake_transport.keep_alive_calls[0] == (envelope, 30)


async def test_log_context_is_not_shared_between_handlers(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    caplog: pytest.LogCaptureFixture,
    context: Context,
) -> None:
    caplog.set_level(logging.INFO)
    message1 = WorkerMessage(value="message1")
    message2 = WorkerMessage(value="message2")

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    registry.register_handler(context_setter_handler)
    registry.register_handler(logging_handler)

    await transport.send(Envelope.wrap(message1))
    await transport.send(Envelope.wrap(message2))

    context["foo"] = "bar"

    await worker.run(limit=2)

    logs = cast(
        "list[ContextLogRecord]",
        [
            log
            for log in caplog.records
            if log.message in ("Setting log context", "Handling message with context.")
        ],
    )
    assert logs[0].context["foo"] == "baz"
    assert logs[0].context["message_value"] == "message1"
    assert logs[1].context["foo"] == "bar"
    assert not hasattr(logs[1].context, "message_value")
    assert logs[2].context["foo"] == "baz"
    assert logs[2].context["message_value"] == "message2"
    assert logs[3].context["foo"] == "bar"
    assert not hasattr(logs[3].context, "message_value")


async def test_log_context_is_not_shared_between_messages(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    caplog: pytest.LogCaptureFixture,
    middleware_stack: MiddlewareStack,
    context: Context,
) -> None:
    caplog.set_level(logging.INFO)

    middleware_stack.append(PropagateContext)

    message1 = WorkerMessage(value="message1")
    message2 = WorkerMessage(value="message2")
    message3 = WorkerMessage(value="message3")

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    registry.register_handler(logging_handler)

    await transport.send(
        Envelope.wrap(message1).with_stamps(ContextStamp({"request_id": "123456"}))
    )
    await transport.send(
        Envelope.wrap(message2).with_stamps(ContextStamp({"request_id": "987654"}))
    )
    await transport.send(Envelope.wrap(message3))

    await worker.run(limit=3)

    logs = cast(
        "list[ContextLogRecord]",
        [
            log
            for log in caplog.records
            if log.message == "Handling message with context."
        ],
    )
    assert logs[0].context["request_id"] == "123456"
    assert logs[1].context["request_id"] == "987654"
    assert not hasattr(logs[2].context, "context")


@pytest.fixture()
def cache() -> Cache:
    return Cache("test", MemoryStore(SyncMemoryStore()))


async def test_worker_releases_unique_lock_after_successful_handling(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    container: Container,
    cache: Cache,
) -> None:
    container.instance(CacheContract, cache)

    async def handler(_message: WorkerMessage) -> None:
        pass

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    envelope = Envelope.wrap(WorkerMessage(value="unique"), stamps=[UniqueStamp()])
    lock = UniqueLock(cache)
    assert await lock.acquire(envelope) is True

    await transport.send(envelope)
    registry.register_handler(handler)

    await worker.run(limit=1)

    # The lock should have been released, so it can be acquired again.
    other = UniqueLock(cache)
    assert await other.acquire(envelope) is True


async def test_worker_releases_unique_lock_on_unrecoverable_failure(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    container: Container,
    cache: Cache,
) -> None:
    container.instance(CacheContract, cache)

    async def handler(_message: WorkerMessage) -> None:
        raise UnrecoverableMessageHandlingError("permanent failure")

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    envelope = Envelope.wrap(WorkerMessage(value="unique"), stamps=[UniqueStamp()])
    lock = UniqueLock(cache)
    assert await lock.acquire(envelope) is True

    await transport.send(envelope)
    registry.register_handler(handler)

    await worker.run(limit=1)

    # An unrecoverable failure discards the message for good, so the lock
    # must be released rather than left orphaned.
    other = UniqueLock(cache)
    assert await other.acquire(envelope) is True


async def test_worker_does_not_release_unique_lock_on_retry(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    container: Container,
    cache: Cache,
) -> None:
    container.instance(CacheContract, cache)

    async def handler(_message: WorkerMessage) -> None:
        raise RuntimeError("transient")

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    envelope = Envelope.wrap(WorkerMessage(value="unique"), stamps=[UniqueStamp()])
    lock = UniqueLock(cache)
    assert await lock.acquire(envelope) is True

    await transport.send(envelope)
    registry.register_handler(handler)

    await worker.run(limit=1)

    # The retry strategy re-sends the envelope, so the lock is not released
    # while the message is still in-flight.
    other = UniqueLock(cache)
    assert await other.acquire(envelope) is False


async def test_worker_releases_unique_lock_when_retries_are_exhausted(
    transport_manager: TransportManager,
    retry_strategy_manager: RetryStrategyManager,
    middleware_stack: MiddlewareStack,
    container: Container,
    registry: Registry,
    cache: Cache,
) -> None:
    container.instance(CacheContract, cache)

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
        raise RuntimeError("no retry configured")

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    envelope = Envelope.wrap(WorkerMessage(value="unique"), stamps=[UniqueStamp()])
    lock = UniqueLock(cache)
    assert await lock.acquire(envelope) is True

    await transport.send(envelope)
    registry.register_handler(handler)

    await worker.run(limit=1)

    other = UniqueLock(cache)
    assert await other.acquire(envelope) is True


async def test_worker_processes_messages_concurrently(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    concurrency = 3
    active = 0
    all_active = asyncio.Event()

    async def handler(_message: WorkerMessage) -> None:
        nonlocal active
        active += 1
        if active == concurrency:
            all_active.set()

        # Only returns once every slot has a message in flight at the same
        # time, which is only possible if the worker actually runs
        # `concurrency` handlers concurrently rather than one at a time.
        await asyncio.wait_for(all_active.wait(), timeout=5)

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    for i in range(concurrency):
        await transport.send(Envelope.wrap(WorkerMessage(value=str(i))))

    registry.register_handler(handler)

    await worker.run(limit=concurrency, concurrency=concurrency)

    assert active == concurrency


async def test_worker_concurrency_respects_limit(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    handled: list[str] = []

    async def handler(message: WorkerMessage) -> None:
        handled.append(message.value)

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    for i in range(5):
        await transport.send(Envelope.wrap(WorkerMessage(value=str(i))))

    registry.register_handler(handler)

    await worker.run(limit=3, concurrency=3)

    assert len(handled) == 3


async def test_worker_keep_alive_dict_safe_under_concurrency(
    container: Container,
    middleware_stack: MiddlewareStack,
    registry: Registry,
) -> None:
    fake_transport = FakeKeepAliveTransport()
    worker, _ = _make_keep_alive_worker(
        container, middleware_stack, registry, fake_transport
    )

    concurrency = 3
    active = 0
    all_active = asyncio.Event()
    release = asyncio.Event()

    async def handler(_message: WorkerMessage) -> None:
        nonlocal active
        active += 1
        if active == concurrency:
            all_active.set()

        await asyncio.wait_for(release.wait(), timeout=5)

    for i in range(concurrency):
        fake_transport.enqueue(Envelope.wrap(WorkerMessage(value=str(i))))

    registry.register_handler(handler)

    async def trigger_keep_alive() -> None:
        await asyncio.wait_for(all_active.wait(), timeout=5)
        # Every slot has an envelope in flight at this point, so this
        # exercises `keep_alive()` iterating `_keep_alives` while other
        # tasks may still be inserting/popping from it.
        await worker.keep_alive()
        release.set()

    await asyncio.gather(
        worker.run(limit=concurrency, concurrency=concurrency),
        trigger_keep_alive(),
    )

    assert len(fake_transport.keep_alive_calls) == concurrency


async def test_worker_scoped_container_does_not_leak_between_concurrent_messages(
    worker: Worker, registry: Registry, transport_manager: TransportManager
) -> None:
    concurrency = 2
    active = 0
    all_active = asyncio.Event()
    resolved_values: list[str] = []

    async def handler(message: WorkerMessage, resolved: WorkerMessage) -> None:
        nonlocal active
        active += 1
        if active == concurrency:
            all_active.set()

        await asyncio.wait_for(all_active.wait(), timeout=5)

        # `resolved` is injected from the container rather than passed
        # directly; if messages being handled concurrently shared a
        # container, one handler could resolve the other's message here.
        resolved_values.append(resolved.value)
        assert resolved.value == message.value

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="a")))
    await transport.send(Envelope.wrap(WorkerMessage(value="b")))
    registry.register_handler(handler)

    await worker.run(limit=concurrency, concurrency=concurrency)

    assert sorted(resolved_values) == ["a", "b"]


async def test_worker_does_not_reprocess_message_reclaimed_by_own_slot(
    container: Container,
    middleware_stack: MiddlewareStack,
    registry: Registry,
) -> None:
    """If a lease-based transport (database, redis, ...) considers a
    message eligible for redelivery again while one of this worker's own
    concurrent slots is still actively handling it -- e.g. because its
    keep-alive refresh hasn't run yet -- a sibling slot must not process
    it a second time."""
    fake_transport = FlappingLeaseTransport()
    cfg = Config(
        {
            "messenger": {
                "transport": "flapping",
                "failure_transport": "failed",
                "transports": {
                    "flapping": {"driver": "memory"},
                    "failed": {"driver": "memory"},
                },
            }
        }
    )
    tm = TransportManager(container, cfg, registry)
    tm._transports["flapping"] = fake_transport
    worker = Worker(
        tm, RetryStrategyManager(cfg), cfg, middleware_stack, container, registry
    )

    call_count = 0

    async def handler(_message: WorkerMessage) -> None:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)

    fake_transport.enqueue(Envelope.wrap(WorkerMessage(value="once")))
    registry.register_handler(handler)

    async def flapper() -> None:
        # Simulates the transport's lease/redelivery-timeout repeatedly
        # elapsing while the message is still being handled.
        for _ in range(20):
            await asyncio.sleep(0.005)
            fake_transport.available = True

    async def stopper() -> None:
        await asyncio.sleep(0.2)
        worker.stop()

    flap_task = asyncio.ensure_future(flapper())
    stop_task = asyncio.ensure_future(stopper())
    try:
        await worker.run(concurrency=3, sleep=1)
    finally:
        flap_task.cancel()
        stop_task.cancel()

    assert call_count == 1
    assert len(fake_transport.acknowledged) == 1


async def test_worker_does_not_release_when_envelope_has_no_unique_stamp(
    worker: Worker,
    registry: Registry,
    transport_manager: TransportManager,
    container: Container,
) -> None:
    # If the Cache is never resolved from the container, no exception is raised,
    # which means the worker did not attempt to release a lock.
    async def handler(_message: WorkerMessage) -> None:
        pass

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)

    await transport.send(Envelope.wrap(WorkerMessage(value="no-unique")))
    registry.register_handler(handler)

    # Note: no Cache bound in the container. If _release_unique_lock is invoked
    # for this envelope, container.get(Cache) would raise.
    await worker.run(limit=1)


async def test_worker_can_handle_message_decoding_errors(
    worker: Worker,
    transport_manager: TransportManager,
    mocker: MockerFixture,
    middleware_stack: MiddlewareStack,
    container: Container,
) -> None:
    serializer = await container.get(SerializerContract)

    _ = mocker.patch.object(
        serializer,
        "decode",
        wraps=serializer.decode,
        side_effect=[
            MessageDecodingFailedError(
                "Failed to decode",
                {
                    "body": b"",
                    "headers": {"stamps": []},
                },
            ).as_envelope(),
            *[mocker.DEFAULT] * 11,
        ],
    )

    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)
    failure_transport = await transport_manager.transport("failed")
    assert isinstance(failure_transport, MemoryTransport)

    _ = await transport.send(Envelope.wrap(WorkerMessage(value="foo")))

    middleware_stack.use([HandleFailedDecoding])
    await worker.run(limit=1)

    # The message has been sent back to the transport
    assert len(transport.sent) == 2

    # Exhaust retries
    await worker.run(limit=3, sleep=0)

    # The message has been discarded
    assert await anext(transport.receive(), None) is None
    # and send to the failure transport
    assert len(failure_transport.sent) == 1

    # The envelope should contain the original decoding error
    envelope = failure_transport.sent[0]
    error = envelope.open()
    assert isinstance(error, MessageDecodingFailedError)
    assert str(error) == "Failed to decode"
    assert error.encoded_envelope == {
        "body": b"",
        "headers": {"stamps": []},
    }
