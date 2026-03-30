from __future__ import annotations

import asyncio

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.messenger.asynchronous.transactional_message_bus import (
    TransactionalMessageBus,
)
from expanse.messenger.envelope import Envelope


if TYPE_CHECKING:
    from expanse.types.messenger import Message


@dataclass
class MyMessage:
    foo: str


class FakeAsyncMessageBus(MessageBusContract):
    def __init__(self) -> None:
        self.dispatched: list[Envelope] = []

    async def dispatch(self, message: Message | Envelope) -> Envelope:
        envelope = Envelope.wrap(message)
        self.dispatched.append(envelope)
        return envelope


@pytest.fixture()
def engine():
    return create_engine("sqlite:///:memory:")


@pytest.fixture()
def session(engine) -> Session:
    with Session(engine) as session:
        yield session


@pytest.fixture()
def fake_bus() -> FakeAsyncMessageBus:
    return FakeAsyncMessageBus()


async def _commit_in_thread(session: Session) -> None:
    """Run session.commit() in a thread to allow async_to_sync to work."""
    await asyncio.to_thread(session.commit)


async def test_dispatch_without_session_dispatches_immediately(
    fake_bus: FakeAsyncMessageBus,
) -> None:
    bus = TransactionalMessageBus(fake_bus)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message
    assert envelope.open() == message


async def test_dispatch_with_session_queues_messages(
    fake_bus: FakeAsyncMessageBus, session: Session
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert len(fake_bus.dispatched) == 0
    assert envelope.open() == message


async def test_queued_messages_dispatched_on_commit(
    fake_bus: FakeAsyncMessageBus, session: Session
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    msg1 = MyMessage(foo="first")
    msg2 = MyMessage(foo="second")
    await bus.dispatch(msg1)
    await bus.dispatch(msg2)

    assert len(fake_bus.dispatched) == 0

    await _commit_in_thread(session)

    assert len(fake_bus.dispatched) == 2
    assert fake_bus.dispatched[0].open() == msg1
    assert fake_bus.dispatched[1].open() == msg2


async def test_queued_messages_cleared_on_rollback(
    fake_bus: FakeAsyncMessageBus, engine
) -> None:
    with Session(engine) as session:
        session.begin()

        bus = TransactionalMessageBus(fake_bus, session=session)

        await bus.dispatch(MyMessage(foo="bar"))

        assert len(fake_bus.dispatched) == 0

        session.rollback()

        assert len(fake_bus.dispatched) == 0
        assert len(bus._queued_messages) == 0


async def test_messages_after_commit_are_still_queued(
    fake_bus: FakeAsyncMessageBus, session: Session
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    await bus.dispatch(MyMessage(foo="first"))
    await _commit_in_thread(session)

    assert len(fake_bus.dispatched) == 1

    await bus.dispatch(MyMessage(foo="second"))

    assert len(fake_bus.dispatched) == 1

    await _commit_in_thread(session)

    assert len(fake_bus.dispatched) == 2


async def test_attach_session_after_creation(
    fake_bus: FakeAsyncMessageBus, session: Session
) -> None:
    bus = TransactionalMessageBus(fake_bus)

    # Without session, dispatches immediately
    await bus.dispatch(MyMessage(foo="immediate"))
    assert len(fake_bus.dispatched) == 1

    # Attach session, now messages are queued
    bus.attach_session(session)
    await bus.dispatch(MyMessage(foo="queued"))
    assert len(fake_bus.dispatched) == 1

    await _commit_in_thread(session)
    assert len(fake_bus.dispatched) == 2


async def test_dispatch_returns_envelope(
    fake_bus: FakeAsyncMessageBus, session: Session
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert isinstance(envelope, Envelope)
    assert envelope.open() == message


async def test_dispatch_with_envelope_input(
    fake_bus: FakeAsyncMessageBus, session: Session
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    message = MyMessage(foo="bar")
    input_envelope = Envelope(message)
    result = await bus.dispatch(input_envelope)

    assert result is input_envelope

    await _commit_in_thread(session)

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message
