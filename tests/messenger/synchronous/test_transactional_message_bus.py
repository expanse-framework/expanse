from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from sqlalchemy import create_engine

from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.database.synchronous.session import Session
from expanse.messenger.asynchronous.transactional_message_bus import (
    TransactionalMessageBus,
)
from expanse.messenger.envelope import Envelope
from expanse.messenger.synchronous.message_bus import MessageBus


if TYPE_CHECKING:
    from collections.abc import Generator

    from expanse.types.messenger import Message


@dataclass
class MyMessage:
    foo: str


class FakeMessageBus(MessageBusContract):
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
def session(engine) -> Generator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture()
def fake_bus() -> FakeMessageBus:
    return FakeMessageBus()


@pytest.fixture()
def async_bus(fake_bus: FakeMessageBus) -> TransactionalMessageBus:
    return TransactionalMessageBus(fake_bus)


def test_dispatch_without_session_dispatches_immediately(
    fake_bus: FakeMessageBus, async_bus: TransactionalMessageBus
) -> None:
    bus = MessageBus(async_bus)

    message = MyMessage(foo="bar")
    envelope = bus.dispatch(message)

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message
    assert envelope.open() == message


def test_dispatch_with_out_of_transaction_session_dispatches_immediately(
    fake_bus: FakeMessageBus, async_bus: TransactionalMessageBus, session: Session
) -> None:
    bus = MessageBus(async_bus)
    async_bus.attach_session(session)

    message = MyMessage(foo="bar")
    envelope = bus.dispatch(message)

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message
    assert envelope.open() == message


def test_dispatch_with_in_transaction_session_queues_messages(
    fake_bus: FakeMessageBus, session: Session, async_bus: TransactionalMessageBus
) -> None:
    bus = MessageBus(async_bus)
    async_bus.attach_session(session)

    message = MyMessage(foo="bar")
    with session.begin():
        envelope = bus.dispatch(message)

        assert len(fake_bus.dispatched) == 0
        assert envelope.open() == message


def test_queued_messages_dispatched_on_commit(
    fake_bus: FakeMessageBus, session: Session, async_bus: TransactionalMessageBus
) -> None:
    bus = MessageBus(async_bus)
    async_bus.attach_session(session)

    msg1 = MyMessage(foo="first")
    msg2 = MyMessage(foo="second")
    with session.begin():
        bus.dispatch(msg1)
        bus.dispatch(msg2)

        assert len(fake_bus.dispatched) == 0

        session.commit()

        assert len(fake_bus.dispatched) == 2
        assert fake_bus.dispatched[0].open() == msg1
        assert fake_bus.dispatched[1].open() == msg2


def test_queued_messages_cleared_on_rollback(
    fake_bus: FakeMessageBus, async_bus: TransactionalMessageBus, session: Session
) -> None:
    bus = MessageBus(async_bus)
    async_bus.attach_session(session)

    with session.begin():
        bus.dispatch(MyMessage(foo="bar"))

        assert len(fake_bus.dispatched) == 0

        session.rollback()

        assert len(fake_bus.dispatched) == 0
        assert len(async_bus._queued_messages) == 0


def test_messages_after_session_transaction_ends_are_dispatched_at_once(
    fake_bus: FakeMessageBus, async_bus: TransactionalMessageBus, session: Session
) -> None:
    bus = MessageBus(async_bus)
    async_bus.attach_session(session)

    with session.begin():
        bus.dispatch(MyMessage(foo="first"))
        session.commit()

        assert len(fake_bus.dispatched) == 1

    bus.dispatch(MyMessage(foo="second"))

    assert len(fake_bus.dispatched) == 2


def test_dispatch_returns_envelope(
    fake_bus: FakeMessageBus, session: Session, async_bus: TransactionalMessageBus
) -> None:
    bus = MessageBus(async_bus)
    async_bus.attach_session(session)

    message = MyMessage(foo="bar")
    envelope = bus.dispatch(message)

    assert isinstance(envelope, Envelope)
    assert envelope.open() == message


def test_dispatch_with_envelope_input(
    fake_bus: FakeMessageBus, session: Session, async_bus: TransactionalMessageBus
) -> None:
    bus = MessageBus(async_bus)
    async_bus.attach_session(session)

    message = MyMessage(foo="bar")
    input_envelope = Envelope(message)
    result = bus.dispatch(input_envelope)

    assert result is input_envelope

    session.commit()

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message


def test_bus_keeps_track_of_transactions(
    fake_bus: FakeMessageBus, session: Session, async_bus: TransactionalMessageBus
) -> None:
    bus = MessageBus(async_bus)
    async_bus.attach_session(session)

    with session.begin():
        bus.dispatch(MyMessage(foo="first"))
        assert len(fake_bus.dispatched) == 0

        with session.begin_nested() as nested:
            bus.dispatch(MyMessage(foo="second"))
            nested.commit()
            assert len(fake_bus.dispatched) == 0

        # After nested transaction ends, messages should still not be dispatched
        # since the outer transaction is still active
        assert len(fake_bus.dispatched) == 0

        session.commit()
        assert len(fake_bus.dispatched) == 2
