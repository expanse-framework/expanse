from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore
from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract
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
from expanse.messenger.locks.unique import UniqueLock
from expanse.messenger.registry import Registry
from expanse.messenger.stamps.transport import TransportStamp
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.messenger.stamps.unique_lock_acquired import UniqueLockAcquiredStamp
from expanse.messenger.transports.transport_manager import TransportManager


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from expanse.messenger.serializers.serializer import Serializer
    from expanse.types.messenger import Message


@dataclass
class MyMessage:
    foo: str


@dataclass
class MyOtherMessage:
    foo: str


class FakeAsyncMessageBus(MessageBusContract):
    def __init__(self) -> None:
        self.dispatched: list[Envelope] = []

    async def dispatch(self, message: Message | Envelope) -> Envelope:
        envelope = Envelope.wrap(message)
        self.dispatched.append(envelope)
        return envelope


class FakeUniqueMessageBus(MessageBusContract):
    """
    A fake bus acquiring the unique lock of messages, as the EnsureUnique middleware does.
    """

    def __init__(self, cache: Cache) -> None:
        self.dispatched: list[Envelope] = []
        self._lock: UniqueLock = UniqueLock(cache)

    async def dispatch(self, message: Message | Envelope) -> Envelope:
        envelope = Envelope.wrap(message)
        if not await self._lock.acquire(envelope):
            return envelope

        self.dispatched.append(envelope)

        return envelope.with_stamps(UniqueLockAcquiredStamp())


def _outboxed(message: Message) -> Envelope:
    return Envelope.wrap(message).with_stamps(TransportStamp("outboxed"))


def _unique_outboxed(message: Message) -> Envelope:
    return _outboxed(message).with_stamps(UniqueStamp())


async def _is_locked(cache: Cache, message: Message) -> bool:
    return not await UniqueLock(cache).acquire(Envelope(message, [UniqueStamp()]))


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
async def connection(engine: AsyncEngine) -> AsyncGenerator[AsyncConnection]:
    async with engine.connect() as connection:
        yield connection


@pytest.fixture()
async def connection_session(
    connection: AsyncConnection,
) -> AsyncGenerator[AsyncSession]:
    """
    A session sharing its connection with the outbox transport.
    """
    async with async_sessionmaker(connection, class_=AsyncSession)() as session:
        yield session


@pytest.fixture()
def fake_bus() -> FakeAsyncMessageBus:
    return FakeAsyncMessageBus()


@pytest.fixture()
def cache() -> Cache:
    return Cache("test", MemoryStore(SyncMemoryStore()))


@pytest.fixture()
def container(cache: Cache) -> Container:
    container = Container()
    container.instance(CacheContract, cache)

    return container


@pytest.fixture()
def transport_manager(
    serializer: Serializer, connection: AsyncConnection
) -> TransportManager:
    container = Container()
    container.instance(SerializerContract, serializer)
    container.instance(AsyncConnection, connection)
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
    connection_session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    message = MyMessage(foo="bar")

    async with connection_session.begin():
        envelope = await bus.dispatch(_outboxed(message))

        # The outbox stores the message as part of the current transaction,
        # so there is no need to wait for the commit.
        assert len(fake_bus.dispatched) == 1
        assert fake_bus.dispatched[0].open() == message
        assert envelope.open() == message
        assert bus._queued_messages == [[]]


async def test_outbox_dispatch_begins_the_session_transaction_on_its_connection(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    connection_session: AsyncSession,
    connection: AsyncConnection,
) -> None:
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    async with connection_session.begin():
        # The session has not used its connection yet
        assert not connection.in_transaction()

        await bus.dispatch(_outboxed(MyMessage(foo="bar")))

        # Otherwise, the outbox would commit the message on its own
        assert connection.in_transaction()


async def test_messages_for_outbox_transports_are_not_dispatched_again_on_commit(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    connection_session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    async with connection_session.begin():
        await bus.dispatch(_outboxed(MyMessage(foo="outboxed")))
        await bus.dispatch(MyMessage(foo="queued"))

        assert [e.open() for e in fake_bus.dispatched] == [MyMessage(foo="outboxed")]

        await connection_session.commit()

    assert [e.open() for e in fake_bus.dispatched] == [
        MyMessage(foo="outboxed"),
        MyMessage(foo="queued"),
    ]


async def test_messages_for_outbox_default_transport_are_dispatched_immediately(
    fake_bus: FakeAsyncMessageBus,
    serializer: Serializer,
    connection: AsyncConnection,
    connection_session: AsyncSession,
) -> None:
    container = Container()
    container.instance(SerializerContract, serializer)
    container.instance(AsyncConnection, connection)
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
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    async with connection_session.begin():
        await bus.dispatch(MyMessage(foo="bar"))

        assert len(fake_bus.dispatched) == 1


async def test_messages_for_outbox_transports_are_dispatched_even_if_rolled_back(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    connection_session: AsyncSession,
) -> None:
    """
    Outboxed messages are stored as part of the session transaction,
    so they are discarded by the rollback of the transaction itself.
    """
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    async with connection_session.begin():
        await bus.dispatch(_outboxed(MyMessage(foo="outboxed")))
        await bus.dispatch(MyMessage(foo="queued"))

        await connection_session.rollback()

    assert [e.open() for e in fake_bus.dispatched] == [MyMessage(foo="outboxed")]


async def test_messages_for_outbox_transports_are_queued_if_the_outbox_does_not_share_the_session_connection(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    """
    The outbox cannot be part of the transaction of a session using another connection,
    so messages are only stored in the outbox once the transaction is committed.
    """
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(_outboxed(MyMessage(foo="outboxed")))

        assert fake_bus.dispatched == []

        await session.commit()

    assert [e.open() for e in fake_bus.dispatched] == [MyMessage(foo="outboxed")]


async def test_messages_for_outbox_transports_are_discarded_on_rollback_if_the_outbox_does_not_share_the_session_connection(
    fake_bus: FakeAsyncMessageBus,
    transport_manager: TransportManager,
    session: AsyncSession,
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    async with session.begin():
        await bus.dispatch(_outboxed(MyMessage(foo="outboxed")))
        await session.rollback()

    assert fake_bus.dispatched == []


async def test_unique_locks_of_outboxed_messages_are_released_on_rollback(
    transport_manager: TransportManager,
    connection_session: AsyncSession,
    container: Container,
    cache: Cache,
) -> None:
    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    async with connection_session.begin():
        envelope = await bus.dispatch(_unique_outboxed(MyMessage(foo="bar")))

        assert envelope.has_stamp(UniqueLockAcquiredStamp)
        assert await _is_locked(cache, MyMessage(foo="bar"))

        await connection_session.rollback()

    assert not await _is_locked(cache, MyMessage(foo="bar"))


async def test_unique_locks_of_outboxed_messages_are_kept_on_commit(
    transport_manager: TransportManager,
    connection_session: AsyncSession,
    container: Container,
    cache: Cache,
) -> None:
    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    async with connection_session.begin():
        await bus.dispatch(_unique_outboxed(MyMessage(foo="bar")))

    # The lock is released by the worker, once the message has been handled
    assert await _is_locked(cache, MyMessage(foo="bar"))


async def test_unique_locks_not_acquired_by_the_dispatch_are_not_released_on_rollback(
    transport_manager: TransportManager,
    connection_session: AsyncSession,
    container: Container,
    cache: Cache,
) -> None:
    # The lock is held by a message which is already in the outbox
    await UniqueLock(cache).acquire(Envelope(MyMessage(foo="bar"), [UniqueStamp()]))

    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    async with connection_session.begin():
        envelope = await bus.dispatch(_unique_outboxed(MyMessage(foo="bar")))

        assert not envelope.has_stamp(UniqueLockAcquiredStamp)

        await connection_session.rollback()

    assert await _is_locked(cache, MyMessage(foo="bar"))


async def test_unique_locks_of_outboxed_messages_are_released_on_nested_rollback(
    transport_manager: TransportManager,
    connection_session: AsyncSession,
    container: Container,
    cache: Cache,
) -> None:
    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    async with connection_session.begin():
        await bus.dispatch(_unique_outboxed(MyMessage(foo="outer")))

        async with connection_session.begin_nested() as nested:
            await bus.dispatch(_unique_outboxed(MyOtherMessage(foo="nested")))
            await nested.rollback()

        assert await _is_locked(cache, MyMessage(foo="outer"))
        assert not await _is_locked(cache, MyOtherMessage(foo="nested"))


async def test_unique_locks_of_nested_outboxed_messages_are_released_on_outer_rollback(
    transport_manager: TransportManager,
    connection_session: AsyncSession,
    container: Container,
    cache: Cache,
) -> None:
    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    async with connection_session.begin():
        async with connection_session.begin_nested():
            await bus.dispatch(_unique_outboxed(MyMessage(foo="nested")))

        assert await _is_locked(cache, MyMessage(foo="nested"))

        await connection_session.rollback()

    assert not await _is_locked(cache, MyMessage(foo="nested"))
