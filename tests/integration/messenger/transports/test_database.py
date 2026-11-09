from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from sqlalchemy import text

from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import TransportError
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.database.config import DatabaseTransportConfig
from expanse.messenger.transports.database.receiver import DatabaseReceiver
from expanse.messenger.transports.database.sender import DatabaseSender
from tests.integration.messenger.fixtures.messages import DatabaseMessage


if TYPE_CHECKING:
    from expanse.core.application import Application
    from expanse.messenger.serializers.serializer import Serializer
    from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_sender_can_send_a_message(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        envelope = Envelope.wrap(DatabaseMessage(value="hello"))
        result = await sender.send(envelope)

    stamp = result.stamp(TransportMessageIdStamp)
    assert stamp is not None
    assert stamp.id is not None

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 1


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_receiver_can_receive_a_message(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)

    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        message = DatabaseMessage(value="receive-me")
        await sender.send(Envelope.wrap(message))

    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)
    envelopes = [e async for e in receiver.receive()]

    assert len(envelopes) == 1
    received = envelopes[0]
    assert isinstance(received.open(), DatabaseMessage)
    assert received.open().value == message.value

    stamp = received.stamp(TransportMessageIdStamp)
    assert stamp is not None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_receiver_does_not_receive_delayed_messages(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    delayed_envelope = Envelope.wrap(DatabaseMessage(value="delayed")).with_stamps(
        DelayStamp(delay=60_000)
    )

    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        await sender.send(delayed_envelope)

    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)
    received = [e async for e in receiver.receive()]

    assert received == []


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_receiver_can_acknowledge_a_message(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)

    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        await sender.send(Envelope.wrap(DatabaseMessage(value="ack-me")))

    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)
    envelopes = [e async for e in receiver.receive()]

    assert len(envelopes) == 1

    await receiver.acknowledge(envelopes[0])

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 0


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_receiver_can_reject_a_message(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)

    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)
        await sender.send(Envelope.wrap(DatabaseMessage(value="reject-me")))

    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)
    envelopes = [e async for e in receiver.receive()]
    assert len(envelopes) == 1

    await receiver.reject(envelopes[0])

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 0


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_receiver_keep_alive_updates_delivered_at(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        await sender.send(Envelope.wrap(DatabaseMessage(value="keep-alive")))

    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)
    envelopes = [e async for e in receiver.receive()]

    assert len(envelopes) == 1
    received = envelopes[0]

    stamp = received.stamp(TransportMessageIdStamp)
    assert stamp is not None

    # Record the delivered_at set during receive, then call keep_alive
    async with db.connection(name) as connection:
        delivered_before: datetime = (
            await connection.execute(
                text("SELECT delivered_at FROM messages WHERE id = :id"),
                {"id": stamp.id},
            )
        ).scalar_one()

    await receiver.keep_alive(received)

    async with db.connection(name) as connection:
        delivered_after: datetime = (
            await connection.execute(
                text("SELECT delivered_at FROM messages WHERE id = :id"),
                {"id": stamp.id},
            )
        ).scalar_one()

    # delivered_at must have been refreshed to a time >= the original
    assert delivered_after >= delivered_before


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_receiver_keep_alive_prevents_redelivery(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    """A message whose delivered_at has expired is redelivered, but keep_alive resets it."""
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    # Very short redelivery timeout so we can simulate expiry via a direct SQL update
    config = DatabaseTransportConfig(connection=name, redelivery_timeout=10)
    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        await sender.send(Envelope.wrap(DatabaseMessage(value="alive")))

    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)
    envelopes = [e async for e in receiver.receive()]

    assert len(envelopes) == 1
    received = envelopes[0]

    stamp = received.stamp(TransportMessageIdStamp)
    assert stamp is not None

    # Expire the message by pushing delivered_at into the past
    expired_at = datetime.now(UTC) - timedelta(seconds=20)
    async with db.connection(name) as connection:
        await connection.execute(
            text("UPDATE messages SET delivered_at = :dt WHERE id = :id"),
            {"dt": expired_at, "id": stamp.id},
        )
        await connection.commit()

    # Expired message is visible for redelivery
    redelivered = [e async for e in receiver.receive()]

    assert len(redelivered) == 1

    # Keep it alive (resets delivered_at to now)
    await receiver.keep_alive(redelivered[0])

    # Receive once more: the message must NOT appear (keep_alive prevented redelivery)
    still_in_flight = [e async for e in receiver.receive()]

    assert still_in_flight == []


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_receiver_keep_alive_raises_when_duration_exceeds_redelivery_timeout(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name, redelivery_timeout=60)
    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        await sender.send(Envelope.wrap(DatabaseMessage(value="too-long")))

    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)
    envelopes = [e async for e in receiver.receive()]

    assert len(envelopes) == 1

    with pytest.raises(TransportError, match="redelivery timeout"):
        await receiver.keep_alive(envelopes[0], duration=120)


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_receiver_keep_alive_is_noop_for_envelope_without_message_id_stamp(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        await sender.send(Envelope.wrap(DatabaseMessage(value="no-stamp")))

    # Envelope with no TransportMessageIdStamp — keep_alive must not raise or touch the DB
    bare_envelope = Envelope.wrap(DatabaseMessage(value="no-stamp"))
    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)
    await receiver.keep_alive(bare_envelope)

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 1


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_sender_stores_messages_as_part_of_the_current_transaction(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        await connection.begin()
        await sender.send(Envelope.wrap(DatabaseMessage(value="rolled-back")))
        await connection.rollback()

    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)

    assert [e async for e in receiver.receive()] == []


@pytest.mark.usefixtures("setup_databases")
# SQLite only allows a single writer at a time: the receiver could not write
# while the transaction of the sender holds the lock.
@pytest.mark.parametrize("name", ["postgresql", "mysql"])
async def test_receiver_settles_messages_independently_of_ongoing_transactions(
    app: Application, name: str, command_tester: CommandTester, serializer: Serializer
) -> None:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    receiver = DatabaseReceiver(config, db.configure_engine(name), serializer)

    async with db.connection(name) as connection:
        await DatabaseSender(config, connection, serializer).send(
            Envelope.wrap(DatabaseMessage(value="ack-me"))
        )

    async with db.connection(name) as connection:
        sender = DatabaseSender(config, connection, serializer)

        # A transaction is ongoing while the message is received and acknowledged,
        # as is the case when it is handled.
        await connection.begin()
        await sender.send(Envelope.wrap(DatabaseMessage(value="rolled-back")))

        envelopes = [e async for e in receiver.receive()]
        assert [e.open() for e in envelopes] == [DatabaseMessage(value="ack-me")]

        await receiver.acknowledge(envelopes[0])
        await connection.rollback()

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 0
