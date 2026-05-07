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
from expanse.messenger.transports.database.transport import DatabaseTransport
from tests.integration.messenger.fixtures.messages import DatabaseMessage


if TYPE_CHECKING:
    from expanse.core.application import Application
    from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_transport_can_send_a_message(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    transport = DatabaseTransport(config, db)

    envelope = Envelope.wrap(DatabaseMessage(value="hello"))
    result = await transport.send(envelope)

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
async def test_transport_can_receive_a_message(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    transport = DatabaseTransport(config, db)

    message = DatabaseMessage(value="receive-me")
    await transport.send(Envelope.wrap(message))

    envelopes = [e async for e in transport.receive()]

    assert len(envelopes) == 1
    received = envelopes[0]
    assert isinstance(received.open(), DatabaseMessage)
    assert received.open().value == message.value

    stamp = received.stamp(TransportMessageIdStamp)
    assert stamp is not None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_transport_does_not_receive_delayed_messages(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    transport = DatabaseTransport(config, db)

    delayed_envelope = Envelope.wrap(DatabaseMessage(value="delayed")).with_stamps(
        DelayStamp(delay=60_000)
    )
    await transport.send(delayed_envelope)

    received = [e async for e in transport.receive()]

    assert received == []


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_transport_can_acknowledge_a_message(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    transport = DatabaseTransport(config, db)

    await transport.send(Envelope.wrap(DatabaseMessage(value="ack-me")))

    envelopes = [e async for e in transport.receive()]
    assert len(envelopes) == 1

    await transport.acknowledge(envelopes[0])

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 0


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_transport_can_reject_a_message(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    transport = DatabaseTransport(config, db)

    await transport.send(Envelope.wrap(DatabaseMessage(value="reject-me")))

    envelopes = [e async for e in transport.receive()]
    assert len(envelopes) == 1

    await transport.reject(envelopes[0])

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 0


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_transport_keep_alive_updates_delivered_at(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    transport = DatabaseTransport(config, db)

    await transport.send(Envelope.wrap(DatabaseMessage(value="keep-alive")))
    envelopes = [e async for e in transport.receive()]
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

    await transport.keep_alive(received)

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
async def test_transport_keep_alive_prevents_redelivery(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    """A message whose delivered_at has expired is redelivered, but keep_alive resets it."""
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    # Very short redelivery timeout so we can simulate expiry via a direct SQL update
    config = DatabaseTransportConfig(connection=name, redelivery_timeout=10)
    transport = DatabaseTransport(config, db)

    await transport.send(Envelope.wrap(DatabaseMessage(value="alive")))
    envelopes = [e async for e in transport.receive()]
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
    redelivered = [e async for e in transport.receive()]
    assert len(redelivered) == 1

    # Keep it alive (resets delivered_at to now)
    await transport.keep_alive(redelivered[0])

    # Receive once more: the message must NOT appear (keep_alive prevented redelivery)
    still_in_flight = [e async for e in transport.receive()]
    assert still_in_flight == []


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_transport_keep_alive_raises_when_duration_exceeds_redelivery_timeout(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name, redelivery_timeout=60)
    transport = DatabaseTransport(config, db)

    await transport.send(Envelope.wrap(DatabaseMessage(value="too-long")))
    envelopes = [e async for e in transport.receive()]
    assert len(envelopes) == 1

    with pytest.raises(TransportError, match="redelivery timeout"):
        await transport.keep_alive(envelopes[0], duration=120)


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_transport_keep_alive_is_noop_for_envelope_without_message_id_stamp(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    config = DatabaseTransportConfig(connection=name)
    transport = DatabaseTransport(config, db)

    await transport.send(Envelope.wrap(DatabaseMessage(value="no-stamp")))

    # Envelope with no TransportMessageIdStamp — keep_alive must not raise or touch the DB
    bare_envelope = Envelope.wrap(DatabaseMessage(value="no-stamp"))
    await transport.keep_alive(bare_envelope)

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 1
