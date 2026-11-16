from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from sqlalchemy import Engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from expanse.cache.synchronous.cache import Cache
from expanse.cache.synchronous.stores.memory import MemoryStore
from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.cache.synchronous.cache import Cache as CacheContract
from expanse.contracts.messenger.synchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.database.synchronous.connection import Connection
from expanse.database.synchronous.session import Session
from expanse.messenger.envelope import Envelope
from expanse.messenger.registry import Registry
from expanse.messenger.stamps.transport import TransportStamp
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.messenger.stamps.unique_lock_acquired import UniqueLockAcquiredStamp
from expanse.messenger.synchronous.locks.unique import UniqueLock
from expanse.messenger.synchronous.transactional_message_bus import (
    TransactionalMessageBus,
)
from expanse.messenger.synchronous.transport_manager import TransportManager


if TYPE_CHECKING:
    from collections.abc import Generator

    from expanse.messenger.serializers.serializer import Serializer
    from expanse.types.messenger import Message


@dataclass
class MyMessage:
    foo: str


@dataclass
class MyOtherMessage:
    foo: str


class FakeMessageBus(MessageBusContract):
    def __init__(self) -> None:
        self.dispatched: list[Envelope] = []

    def dispatch(self, message: Message | Envelope) -> Envelope:
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

    def dispatch(self, message: Message | Envelope) -> Envelope:
        envelope = Envelope.wrap(message)
        if not self._lock.acquire(envelope):
            return envelope

        self.dispatched.append(envelope)

        return envelope.with_stamps(UniqueLockAcquiredStamp())


def _outboxed(message: Message) -> Envelope:
    return Envelope.wrap(message).with_stamps(TransportStamp("outboxed"))


def _unique_outboxed(message: Message) -> Envelope:
    return _outboxed(message).with_stamps(UniqueStamp())


def _is_locked(cache: Cache, message: Message) -> bool:
    return not UniqueLock(cache).acquire(Envelope(message, [UniqueStamp()]))


@pytest.fixture()
def engine() -> Engine:
    return create_engine("sqlite:///:memory:")


@pytest.fixture()
def session(engine: Engine) -> Generator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture()
def connection(engine: Engine) -> Generator[Connection]:
    with engine.connect() as connection:
        yield connection


@pytest.fixture()
def connection_session(connection: Connection) -> Generator[Session]:
    """
    A session sharing its connection with the outbox transport.
    """
    with sessionmaker(connection, class_=Session)() as session:
        yield session


@pytest.fixture()
def fake_bus() -> FakeMessageBus:
    return FakeMessageBus()


@pytest.fixture()
def cache() -> Cache:
    return Cache("test", MemoryStore())


@pytest.fixture()
def container(cache: Cache) -> Container:
    container = Container()
    container.instance(CacheContract, cache)

    return container


def _transport_manager(
    serializer: Serializer, connection: Connection, default: str = "memory"
) -> TransportManager:
    container = Container()
    container.instance(Connection, connection)
    config = Config(
        {
            "messenger": {
                "transport": default,
                "transports": {
                    "memory": {"driver": "memory"},
                    "outboxed": {"driver": "memory", "outbox": "outbox"},
                    "outbox": {"driver": "database"},
                },
            }
        }
    )

    return TransportManager(container, config, Registry(), serializer)


@pytest.fixture()
def transport_manager(
    serializer: Serializer, connection: Connection
) -> TransportManager:
    return _transport_manager(serializer, connection)


def test_dispatch_without_session_dispatches_immediately(
    fake_bus: FakeMessageBus, transport_manager: TransportManager
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus)

    message = MyMessage(foo="bar")
    envelope = bus.dispatch(message)

    assert [e.open() for e in fake_bus.dispatched] == [message]
    assert envelope.open() == message


def test_dispatch_with_out_of_transaction_session_dispatches_immediately(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    message = MyMessage(foo="bar")
    envelope = bus.dispatch(message)

    assert [e.open() for e in fake_bus.dispatched] == [message]
    assert envelope.open() == message


def test_dispatch_with_in_transaction_session_queues_messages(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    message = MyMessage(foo="bar")
    with session.begin():
        envelope = bus.dispatch(message)

        assert fake_bus.dispatched == []
        assert envelope.open() == message


def test_queued_messages_dispatched_on_commit(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    msg1 = MyMessage(foo="first")
    msg2 = MyMessage(foo="second")
    with session.begin():
        bus.dispatch(msg1)
        bus.dispatch(msg2)

        assert fake_bus.dispatched == []

        session.commit()

        assert [e.open() for e in fake_bus.dispatched] == [msg1, msg2]


def test_queued_messages_cleared_on_rollback(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    with session.begin():
        bus.dispatch(MyMessage(foo="bar"))

        session.rollback()

        assert fake_bus.dispatched == []
        assert bus._queued_messages == []


def test_messages_after_session_transaction_ends_are_dispatched_at_once(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    with session.begin():
        bus.dispatch(MyMessage(foo="first"))
        session.commit()

        assert len(fake_bus.dispatched) == 1

    bus.dispatch(MyMessage(foo="second"))

    assert len(fake_bus.dispatched) == 2


def test_attach_session_after_creation(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus)

    assert not bus.has_attached_session()

    bus.attach_session(session)

    assert bus.has_attached_session()

    with session.begin():
        bus.dispatch(MyMessage(foo="bar"))

        assert fake_bus.dispatched == []

    assert len(fake_bus.dispatched) == 1


def test_dispatch_with_envelope_input(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    message = MyMessage(foo="bar")
    input_envelope = Envelope(message)
    result = bus.dispatch(input_envelope)

    assert result is input_envelope

    session.commit()

    assert [e.open() for e in fake_bus.dispatched] == [message]


def test_bus_keeps_track_of_transactions(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    with session.begin():
        bus.dispatch(MyMessage(foo="first"))
        assert fake_bus.dispatched == []

        with session.begin_nested() as nested:
            bus.dispatch(MyMessage(foo="second"))
            nested.commit()
            assert fake_bus.dispatched == []

        # After nested transaction ends, messages should still not be dispatched
        # since the outer transaction is still active
        assert fake_bus.dispatched == []

        session.commit()
        assert len(fake_bus.dispatched) == 2


def test_messages_for_outbox_transports_are_dispatched_immediately_in_a_transaction(
    fake_bus: FakeMessageBus,
    transport_manager: TransportManager,
    connection_session: Session,
) -> None:
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    message = MyMessage(foo="bar")

    with connection_session.begin():
        envelope = bus.dispatch(_outboxed(message))

        # The outbox stores the message as part of the current transaction,
        # so there is no need to wait for the commit.
        assert [e.open() for e in fake_bus.dispatched] == [message]
        assert envelope.open() == message
        assert bus._queued_messages == [[]]


def test_outbox_dispatch_begins_the_session_transaction_on_its_connection(
    fake_bus: FakeMessageBus,
    transport_manager: TransportManager,
    connection_session: Session,
    connection: Connection,
) -> None:
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    with connection_session.begin():
        # The session has not used its connection yet
        assert not connection.in_transaction()

        bus.dispatch(_outboxed(MyMessage(foo="bar")))

        # Otherwise, the outbox would commit the message on its own
        assert connection.in_transaction()


def test_messages_for_outbox_transports_are_not_dispatched_again_on_commit(
    fake_bus: FakeMessageBus,
    transport_manager: TransportManager,
    connection_session: Session,
) -> None:
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    with connection_session.begin():
        bus.dispatch(_outboxed(MyMessage(foo="outboxed")))
        bus.dispatch(MyMessage(foo="queued"))

        assert [e.open() for e in fake_bus.dispatched] == [MyMessage(foo="outboxed")]

        connection_session.commit()

    assert [e.open() for e in fake_bus.dispatched] == [
        MyMessage(foo="outboxed"),
        MyMessage(foo="queued"),
    ]


def test_messages_for_outbox_default_transport_are_dispatched_immediately(
    fake_bus: FakeMessageBus,
    serializer: Serializer,
    connection: Connection,
    connection_session: Session,
) -> None:
    transport_manager = _transport_manager(serializer, connection, default="outboxed")
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    with connection_session.begin():
        bus.dispatch(MyMessage(foo="bar"))

        assert len(fake_bus.dispatched) == 1


def test_messages_for_outbox_transports_are_dispatched_even_if_rolled_back(
    fake_bus: FakeMessageBus,
    transport_manager: TransportManager,
    connection_session: Session,
) -> None:
    """
    Outboxed messages are stored as part of the session transaction,
    so they are discarded by the rollback of the transaction itself.
    """
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session
    )

    with connection_session.begin():
        bus.dispatch(_outboxed(MyMessage(foo="outboxed")))
        bus.dispatch(MyMessage(foo="queued"))

        connection_session.rollback()

    assert [e.open() for e in fake_bus.dispatched] == [MyMessage(foo="outboxed")]


def test_messages_for_outbox_transports_are_queued_if_the_outbox_does_not_share_the_session_connection(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    """
    The outbox cannot be part of the transaction of a session using another connection,
    so messages are only stored in the outbox once the transaction is committed.
    """
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    with session.begin():
        bus.dispatch(_outboxed(MyMessage(foo="outboxed")))

        assert fake_bus.dispatched == []

    assert [e.open() for e in fake_bus.dispatched] == [MyMessage(foo="outboxed")]


def test_messages_for_outbox_transports_are_discarded_on_rollback_if_the_outbox_does_not_share_the_session_connection(
    fake_bus: FakeMessageBus, transport_manager: TransportManager, session: Session
) -> None:
    bus = TransactionalMessageBus(transport_manager, fake_bus, session=session)

    with session.begin():
        bus.dispatch(_outboxed(MyMessage(foo="outboxed")))
        session.rollback()

    assert fake_bus.dispatched == []


def test_unique_locks_of_outboxed_messages_are_released_on_rollback(
    transport_manager: TransportManager,
    connection_session: Session,
    container: Container,
    cache: Cache,
) -> None:
    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    with connection_session.begin():
        envelope = bus.dispatch(_unique_outboxed(MyMessage(foo="bar")))

        assert envelope.has_stamp(UniqueLockAcquiredStamp)
        assert _is_locked(cache, MyMessage(foo="bar"))

        connection_session.rollback()

    assert not _is_locked(cache, MyMessage(foo="bar"))


def test_unique_locks_of_outboxed_messages_are_kept_on_commit(
    transport_manager: TransportManager,
    connection_session: Session,
    container: Container,
    cache: Cache,
) -> None:
    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    with connection_session.begin():
        bus.dispatch(_unique_outboxed(MyMessage(foo="bar")))

    # The lock is released by the worker, once the message has been handled
    assert _is_locked(cache, MyMessage(foo="bar"))


def test_unique_locks_not_acquired_by_the_dispatch_are_not_released_on_rollback(
    transport_manager: TransportManager,
    connection_session: Session,
    container: Container,
    cache: Cache,
) -> None:
    # The lock is held by a message which is already in the outbox
    UniqueLock(cache).acquire(Envelope(MyMessage(foo="bar"), [UniqueStamp()]))

    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    with connection_session.begin():
        envelope = bus.dispatch(_unique_outboxed(MyMessage(foo="bar")))

        assert not envelope.has_stamp(UniqueLockAcquiredStamp)

        connection_session.rollback()

    assert _is_locked(cache, MyMessage(foo="bar"))


def test_unique_locks_of_outboxed_messages_are_released_on_nested_rollback(
    transport_manager: TransportManager,
    connection_session: Session,
    container: Container,
    cache: Cache,
) -> None:
    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    with connection_session.begin():
        bus.dispatch(_unique_outboxed(MyMessage(foo="outer")))

        with connection_session.begin_nested() as nested:
            bus.dispatch(_unique_outboxed(MyOtherMessage(foo="nested")))
            nested.rollback()

        assert _is_locked(cache, MyMessage(foo="outer"))
        assert not _is_locked(cache, MyOtherMessage(foo="nested"))


def test_unique_locks_of_nested_outboxed_messages_are_released_on_outer_rollback(
    transport_manager: TransportManager,
    connection_session: Session,
    container: Container,
    cache: Cache,
) -> None:
    fake_bus = FakeUniqueMessageBus(cache)
    bus = TransactionalMessageBus(
        transport_manager, fake_bus, session=connection_session, container=container
    )

    with connection_session.begin():
        with connection_session.begin_nested():
            bus.dispatch(_unique_outboxed(MyMessage(foo="nested")))

        assert _is_locked(cache, MyMessage(foo="nested"))

        connection_session.rollback()

    assert not _is_locked(cache, MyMessage(foo="nested"))
