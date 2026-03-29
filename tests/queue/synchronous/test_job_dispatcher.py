from __future__ import annotations

from dataclasses import dataclass

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.messenger.asynchronous.message_bus import MessageBus as AsyncMessageBus
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.asynchronous.transports.memory.transport import MemoryTransport
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.self_handling import SelfHandlingStamp
from expanse.messenger.synchronous.message_bus import MessageBus
from expanse.queue.synchronous.job_dispatcher import JobDispatcher
from expanse.queue.synchronous.pending_job import PendingJob


@pytest.fixture()
def container() -> Container:
    return Container()


@pytest.fixture()
def config() -> Config:
    return Config(
        {
            "messenger": {
                "transport": "memory",
                "transports": {
                    "memory": {"driver": "memory"},
                },
            }
        }
    )


@pytest.fixture()
def transport_manager(container: Container, config: Config) -> TransportManager:
    return TransportManager(container, config, Registry())


@pytest.fixture()
def async_bus(
    container: Container, transport_manager: TransportManager
) -> AsyncMessageBus:
    return AsyncMessageBus(transport_manager, container, MiddlewareStack().use([]))


@pytest.fixture()
def bus(async_bus: AsyncMessageBus) -> MessageBus:
    return MessageBus(async_bus)


@pytest.fixture()
def dispatcher(bus: MessageBus) -> JobDispatcher:
    return JobDispatcher(bus)


@pytest.fixture()
async def transport(transport_manager: TransportManager) -> MemoryTransport:
    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)
    return transport


@dataclass
class MyJob:
    value: str

    def handle(self) -> None:
        pass


def test_prepare_returns_pending_job(dispatcher: JobDispatcher) -> None:
    job = MyJob(value="test")
    pending = dispatcher.prepare(job)

    assert isinstance(pending, PendingJob)


def test_prepare_wraps_job_with_self_handling_stamp(
    dispatcher: JobDispatcher,
) -> None:
    job = MyJob(value="test")
    pending = dispatcher.prepare(job)

    assert pending._job.has_stamp(SelfHandlingStamp)


def test_prepare_exposes_original_job(dispatcher: JobDispatcher) -> None:
    job = MyJob(value="test")
    pending = dispatcher.prepare(job)

    assert pending._job.open() is job


def test_dispatch_sends_job_through_bus(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(value="hello")
    dispatcher.dispatch(job)

    sent = transport.sent
    assert len(sent) == 1
    assert sent[0].open() == job


def test_dispatch_sends_envelope_with_self_handling_stamp(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(value="hello")
    dispatcher.dispatch(job)

    sent = transport.sent
    assert len(sent) == 1
    assert sent[0].has_stamp(SelfHandlingStamp)


def test_prepare_delay_dispatch_sends_delayed_job(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(value="delayed")
    dispatcher.prepare(job).delay(30).dispatch()

    sent = transport.sent
    assert len(sent) == 1

    delay_stamp = sent[0].stamp(DelayStamp)
    assert delay_stamp is not None
    assert delay_stamp.delay == 30 * 1000


def test_prepare_without_delay_sends_no_delay_stamp(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(value="immediate")
    dispatcher.prepare(job).dispatch()

    sent = transport.sent
    assert len(sent) == 1
    assert not sent[0].has_stamp(DelayStamp)


def test_multiple_dispatches_send_separate_envelopes(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    dispatcher.dispatch(MyJob(value="first"))
    dispatcher.dispatch(MyJob(value="second"))

    sent = transport.sent
    assert len(sent) == 2
    assert sent[0].open() == MyJob(value="first")
    assert sent[1].open() == MyJob(value="second")
