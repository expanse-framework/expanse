from __future__ import annotations

from dataclasses import dataclass
from typing import override

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.jobs.stamps.job import JobStamp
from expanse.jobs.synchronous.job import Job
from expanse.jobs.synchronous.job_dispatcher import JobDispatcher
from expanse.messenger.asynchronous.message_bus import MessageBus as AsyncMessageBus
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport import TransportStamp
from expanse.messenger.synchronous.message_bus import MessageBus
from expanse.messenger.transports.memory.transport import MemoryTransport
from expanse.messenger.transports.transport_manager import TransportManager


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
class Payload:
    value: str


class MyJob(Job[Payload]):
    @override
    def execute(self) -> None:
        pass


def test_dispatch_sends_payload_through_bus(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(Payload("hello"))
    dispatcher.dispatch(job)

    sent = transport.sent
    assert len(sent) == 1
    assert sent[0].open() == Payload("hello")


def test_dispatch_sends_envelope_with_job_stamp(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(Payload("hello"))
    dispatcher.dispatch(job)

    sent = transport.sent
    assert len(sent) == 1
    assert sent[0].has_stamp(JobStamp)


def test_dispatch_job_stamp_identifies_job_class(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(Payload("hello"))
    dispatcher.dispatch(job)

    stamp = transport.sent[0].stamp(JobStamp)
    assert stamp is not None
    assert stamp.job.endswith("MyJob")


def test_dispatch_with_delay_adds_delay_stamp(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(Payload("delayed"))
    job.delay(30)
    dispatcher.dispatch(job)

    sent = transport.sent
    assert len(sent) == 1

    delay_stamp = sent[0].stamp(DelayStamp)
    assert delay_stamp is not None
    assert delay_stamp.delay == 30 * 1000


def test_dispatch_without_delay_sends_no_delay_stamp(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    job = MyJob(Payload("immediate"))
    dispatcher.dispatch(job)

    sent = transport.sent
    assert len(sent) == 1
    assert not sent[0].has_stamp(DelayStamp)


def test_prepare_with_via_includes_transport_stamp(
    dispatcher: JobDispatcher,
) -> None:
    job = MyJob(Payload("routed"))
    job.via("custom_transport")
    envelope = dispatcher.prepare(job)

    stamp = envelope.stamp(TransportStamp)
    assert stamp is not None
    assert stamp.name == "custom_transport"


def test_multiple_dispatches_send_separate_envelopes(
    dispatcher: JobDispatcher, transport: MemoryTransport
) -> None:
    dispatcher.dispatch(MyJob(Payload("first")))
    dispatcher.dispatch(MyJob(Payload("second")))

    sent = transport.sent
    assert len(sent) == 2
    assert sent[0].open() == Payload("first")
    assert sent[1].open() == Payload("second")
