from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.database.asynchronous.connection import AsyncConnection
from expanse.database.asynchronous.session import AsyncSession
from expanse.messenger.asynchronous.transactional_message_bus import (
    TransactionalMessageBus,
)
from expanse.messenger.envelope import Envelope
from expanse.messenger.registry import Registry
from expanse.messenger.stamps.transport import TransportStamp
from expanse.messenger.transports.transport_manager import TransportManager


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from expanse.messenger.serializers.serializer import Serializer
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


@pytest.fixture()
def transport_manager(serializer: Serializer) -> TransportManager:
    container = Container()
    container.instance(SerializerContract, serializer)
    # Database transports do not touch the connection until they are used
    container.instance(AsyncConnection, MagicMock(spec=AsyncConnection))
    config = Config(
        {
            "messenger": {
                "transport": "memory",
                "transports": {
                    "memory": {"driver": "memory"},
                    "outboxed": {"driver": "memory", "outbox": "outbox"},
                    "outbox": {"driver": "database"},
                },
            }
        }
    )

    return TransportManager(container, config, Registry())


async def test_dispatch_without_session_dispatches_immediately(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message
    assert envelope.open() == message


async def test_dispatch_with_out_of_transaction_session_dispatches_immediately(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert len(fake_bus.dispatched) == 1
    assert envelope.open() == message


async def test_dispatch_with_in_transaction_session_queues_messages(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    message = MyMessage(foo="bar")
    async with session.begin():
        envelope = await bus.dispatch(message)

        assert len(fake_bus.dispatched) == 0
        assert envelope.open() == message


async def test_queued_messages_dispatched_on_commit(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

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
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    async with session.begin():
        bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

        await bus.dispatch(MyMessage(foo="bar"))

        assert len(fake_bus.dispatched) == 0

        await session.rollback()

        assert len(fake_bus.dispatched) == 0
        assert len(bus._queued_messages) == 0


async def test_messages_after_session_transaction_ends_are_dispatched_at_once(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(MyMessage(foo="first"))
        await session.commit()

        assert len(fake_bus.dispatched) == 1

    await bus.dispatch(MyMessage(foo="second"))

    assert len(fake_bus.dispatched) == 2


async def test_attach_session_after_creation(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus)

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
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    message = MyMessage(foo="bar")
    envelope = await bus.dispatch(message)

    assert isinstance(envelope, Envelope)
    assert envelope.open() == message


async def test_dispatch_with_envelope_input(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    message = MyMessage(foo="bar")
    input_envelope = Envelope(message)
    result = await bus.dispatch(input_envelope)

    assert result is input_envelope

    await session.commit()

    assert len(fake_bus.dispatched) == 1
    assert fake_bus.dispatched[0].open() == message


async def test_bus_keeps_track_of_transactions(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(MyMessage(foo="first"))
        assert len(fake_bus.dispatched) == 0

        async with session.begin_nested() as nested:
            await bus.dispatch(MyMessage(foo="second"))
            await nested.commit()
            assert len(fake_bus.dispatched) == 0

        async with session.begin_nested() as nested2:
            await bus.dispatch(MyMessage(foo="third"))
            await bus.dispatch(MyMessage(foo="fourth"))
            await nested2.rollback()

        # After nested transaction ends, messages should still not be dispatched
        # since the outer transaction is still active
        assert len(fake_bus.dispatched) == 0

        await session.commit()
        assert len(fake_bus.dispatched) == 2


async def test_messages_for_outbox_transports_are_dispatched_immediately_in_a_transaction(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    message = MyMessage(foo="bar")

    async with session.begin():
        envelope = await bus.dispatch(
            Envelope.wrap(message).with_stamps(TransportStamp("outboxed"))
        )

        # The outbox stores the message as part of the current transaction,
        # so there is no need to wait for the commit.
        assert len(fake_bus.dispatched) == 1
        assert fake_bus.dispatched[0].open() == message
        assert envelope.open() == message
        assert bus._queued_messages == [[]]


async def test_messages_for_outbox_transports_are_not_dispatched_again_on_commit(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(
            Envelope.wrap(MyMessage(foo="outboxed")).with_stamps(
                TransportStamp("outboxed")
            )
        )
        await bus.dispatch(MyMessage(foo="queued"))

        assert [e.open() for e in fake_bus.dispatched] == [MyMessage(foo="outboxed")]

        await session.commit()

    assert [e.open() for e in fake_bus.dispatched] == [
        MyMessage(foo="outboxed"),
        MyMessage(foo="queued"),
    ]


async def test_messages_for_outbox_default_transport_are_dispatched_immediately(
    fake_bus: FakeAsyncMessageBus,
    serializer: Serializer,
    session: AsyncSession,
) -> None:
    container = Container()
    container.instance(SerializerContract, serializer)
    container.instance(AsyncConnection, MagicMock(spec=AsyncConnection))
    config = Config(
        {
            "messenger": {
                "transport": "outboxed",
                "transports": {
                    "outboxed": {"driver": "memory", "outbox": "outbox"},
                    "outbox": {"driver": "database"},
                },
            }
        }
    )
    transport_manager = TransportManager(container, config, Registry())
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(MyMessage(foo="bar"))

        assert len(fake_bus.dispatched) == 1


async def test_messages_for_outbox_transports_are_dispatched_even_if_rolled_back(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    """
    Discarding outboxed messages on rollback is the responsibility of the
    database transaction itself, not of the transactional bus.
    """
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(
            Envelope.wrap(MyMessage(foo="outboxed")).with_stamps(
                TransportStamp("outboxed")
            )
        )
        await bus.dispatch(MyMessage(foo="queued"))

        await session.rollback()

    assert [e.open() for e in fake_bus.dispatched] == [MyMessage(foo="outboxed")]
