from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import func
from sqlalchemy import select

from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.synchronous.transports.database import DatabaseTransport
from expanse.messenger.synchronous.transports.memory import MemoryTransport
from expanse.messenger.synchronous.transports.outbox import OutboxTransport
from expanse.messenger.transports.database.config import DatabaseTransportConfig


if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any

    from expanse.database.synchronous.connection import Connection
    from expanse.messenger.serializers.serializer import Serializer


@dataclass
class MyMessage:
    foo: str


metadata = MetaData()
messages = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("body", Text, nullable=False),
    Column("headers", Text, nullable=False),
    Column("queue_name", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("available_at", DateTime(timezone=True), nullable=False),
    Column("delivered_at", DateTime(timezone=True), nullable=True),
)


@pytest.fixture()
def connection() -> Generator[Connection]:
    engine = create_engine("sqlite:///:memory:")

    # pysqlite does not handle transactions, and so SAVEPOINTs, properly by itself.
    # See https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl
    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection: Any, connection_record: Any) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def do_begin(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN")

    metadata.create_all(engine)

    with engine.connect() as connection:
        yield connection


@pytest.fixture()
def transport(connection: Connection, serializer: Serializer) -> DatabaseTransport:
    return DatabaseTransport(DatabaseTransportConfig(), connection, serializer)


def _count(connection: Connection) -> int:
    return connection.scalar(select(func.count()).select_from(messages)) or 0


def test_send_stores_the_message(
    transport: DatabaseTransport, connection: Connection, serializer: Serializer
) -> None:
    envelope = transport.send(Envelope(MyMessage(foo="bar")))

    # The message is committed on its own
    assert not connection.in_transaction()

    stamp = envelope.stamp(TransportMessageIdStamp)
    assert stamp is not None

    row = connection.execute(select(messages)).one()
    assert row.id == stamp.id
    assert row.queue_name == "default"


def test_send_stores_the_message_as_part_of_the_current_transaction(
    transport: DatabaseTransport, connection: Connection
) -> None:
    with connection.begin() as transaction:
        transport.send(Envelope(MyMessage(foo="bar")))

        assert _count(connection) == 1

        transaction.rollback()

    assert _count(connection) == 0


def test_outbox_stores_messages_in_the_outbox(
    transport: DatabaseTransport, connection: Connection, serializer: Serializer
) -> None:
    target = MemoryTransport(serializer)
    outbox = OutboxTransport(target, transport, "target")

    envelope = outbox.send(Envelope(MyMessage(foo="bar")))

    assert not envelope.has_stamp(OutboxStamp)
    assert target.sent == []
    assert _count(connection) == 1
