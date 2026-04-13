from __future__ import annotations

from dataclasses import dataclass

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.messenger.asynchronous.message_bus import MessageBus
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.self_handling import SelfHandlingStamp
from expanse.messenger.transports.memory.transport import MemoryTransport
from expanse.messenger.transports.transport_manager import TransportManager
from expanse.queue.asynchronous.job_dispatcher import AsyncJobDispatcher
from expanse.queue.asynchronous.pending_job import AsyncPendingJob


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
def bus(container: Container, transport_manager: TransportManager) -> MessageBus:
    return MessageBus(transport_manager, container, MiddlewareStack().use([]))


@pytest.fixture()
def dispatcher(bus: MessageBus) -> AsyncJobDispatcher:
    return AsyncJobDispatcher(bus)


@pytest.fixture()
async def transport(transport_manager: TransportManager) -> MemoryTransport:
    transport = await transport_manager.transport("memory")
    assert isinstance(transport, MemoryTransport)
    return transport


@dataclass
class MyJob:
    value: str

    async def handle(self) -> None:
        pass


def test_prepare_returns_async_pending_job(dispatcher: AsyncJobDispatcher) -> None:
    job = MyJob(value="test")
    pending = dispatcher.prepare(job)

    assert isinstance(pending, AsyncPendingJob)


def test_prepare_wraps_job_with_self_handling_stamp(
    dispatcher: AsyncJobDispatcher,
) -> None:
    job = MyJob(value="test")
    pending = dispatcher.prepare(job)

    assert pending._job.has_stamp(SelfHandlingStamp)


def test_prepare_exposes_original_job(dispatcher: AsyncJobDispatcher) -> None:
    job = MyJob(value="test")
    pending = dispatcher.prepare(job)

    assert pending._job.open() is job


async def test_dispatch_sends_job_through_bus(
    dispatcher: AsyncJobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(value="hello")
    await dispatcher.dispatch(job)

    sent = transport.sent
    assert len(sent) == 1
    assert sent[0].open() == job


async def test_dispatch_sends_envelope_with_self_handling_stamp(
    dispatcher: AsyncJobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(value="hello")
    await dispatcher.dispatch(job)

    sent = transport.sent
    assert len(sent) == 1
    assert sent[0].has_stamp(SelfHandlingStamp)


async def test_prepare_delay_dispatch_sends_delayed_job(
    dispatcher: AsyncJobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(value="delayed")
    await dispatcher.prepare(job).delay(30).dispatch()

    sent = transport.sent
    assert len(sent) == 1

    delay_stamp = sent[0].stamp(DelayStamp)
    assert delay_stamp is not None
    assert delay_stamp.delay == 30 * 1000


async def test_prepare_without_delay_sends_no_delay_stamp(
    dispatcher: AsyncJobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(value="immediate")
    await dispatcher.prepare(job).dispatch()

    sent = transport.sent
    assert len(sent) == 1
    assert not sent[0].has_stamp(DelayStamp)


async def test_multiple_dispatches_send_separate_envelopes(
    dispatcher: AsyncJobDispatcher, transport: MemoryTransport
) -> None:
    await dispatcher.dispatch(MyJob(value="first"))
    await dispatcher.dispatch(MyJob(value="second"))

    sent = transport.sent
    assert len(sent) == 2
    assert sent[0].open() == MyJob(value="first")
    assert sent[1].open() == MyJob(value="second")
