from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from sqlalchemy.ext.asyncio import async_sessionmaker

from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.database._utils import create_engine
from expanse.database.asynchronous.engine import AsyncEngine
from expanse.database.asynchronous.session import AsyncSession
from expanse.messenger.asynchronous.transactional_message_bus import (
    TransactionalMessageBus,
)
from expanse.messenger.envelope import Envelope


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

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
def engine() -> AsyncEngine:
    return AsyncEngine(create_engine("sqlite+aiosqlite:///:memory:"))


@pytest.fixture()
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession)


@pytest.fixture()
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture()
def fake_bus() -> FakeAsyncMessageBus:
    return FakeAsyncMessageBus()


async def test_dispatch_without_session_dispatches_immediately(
    fake_bus: FakeAsyncMessageBus,
) -> None:
    bus = TransactionalMessageBus(fake_bus)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message
    assert envelope.open() == message


async def test_dispatch_with_out_of_transaction_session_dispatches_immediately(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert len(fake_bus.dispatched) == 1
    assert envelope.open() == message


async def test_dispatch_with_in_transaction_session_queues_messages(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    message = MyMessage(foo="bar")
    async with session.begin():
        envelope = await bus.dispatch(message)

        assert len(fake_bus.dispatched) == 0
        assert envelope.open() == message


async def test_queued_messages_dispatched_on_commit(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    msg1 = MyMessage(foo="first")
    msg2 = MyMessage(foo="second")

    async with session.begin():
        await bus.dispatch(msg1)
        await bus.dispatch(msg2)

        assert len(fake_bus.dispatched) == 0

        await session.commit()

        assert len(fake_bus.dispatched) == 2
        assert fake_bus.dispatched[0].open() == msg1
        assert fake_bus.dispatched[1].open() == msg2


async def test_queued_messages_cleared_on_rollback(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    async with session.begin():
        bus = TransactionalMessageBus(fake_bus, session=session)

        await bus.dispatch(MyMessage(foo="bar"))

        assert len(fake_bus.dispatched) == 0

        await session.rollback()

        assert len(fake_bus.dispatched) == 0
        assert len(bus._queued_messages) == 0


async def test_messages_after_session_transaction_ends_are_dispatched_at_once(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(MyMessage(foo="first"))
        await session.commit()

        assert len(fake_bus.dispatched) == 1

    await bus.dispatch(MyMessage(foo="second"))

    assert len(fake_bus.dispatched) == 2


async def test_attach_session_after_creation(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    bus = TransactionalMessageBus(fake_bus)

    # Without session, dispatches immediately
    await bus.dispatch(MyMessage(foo="immediate"))
    assert len(fake_bus.dispatched) == 1

    # Attach session, now messages are queued
    async with session.begin():
        bus.attach_session(session)
        await bus.dispatch(MyMessage(foo="queued"))
        assert len(fake_bus.dispatched) == 1

        await session.commit()
        assert len(fake_bus.dispatched) == 2


async def test_dispatch_returns_envelope(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert isinstance(envelope, Envelope)
    assert envelope.open() == message


async def test_dispatch_with_envelope_input(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    message = MyMessage(foo="bar")
    input_envelope = Envelope(message)
    result = await bus.dispatch(input_envelope)

    assert result is input_envelope

    await session.commit()

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message


async def test_bus_keeps_track_of_transactions(
    fake_bus: FakeAsyncMessageBus, session: AsyncSession
) -> None:
    bus = TransactionalMessageBus(fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(MyMessage(foo="first"))
        assert len(fake_bus.dispatched) == 0

        async with session.begin_nested() as nested:
            await bus.dispatch(MyMessage(foo="second"))
            await nested.commit()
            assert len(fake_bus.dispatched) == 0

        # After nested transaction ends, messages should still not be dispatched
        # since the outer transaction is still active
        assert len(fake_bus.dispatched) == 0

        await session.commit()
        assert len(fake_bus.dispatched) == 2
