from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sqlalchemy import text

from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
from expanse.messenger.asynchronous.transports.database.transport import (
    DatabaseTransport,
)
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.database.config import DatabaseTransportConfig
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

    received = await transport.receive()

    assert received is not None
    assert isinstance(received.open(), DatabaseMessage)
    assert received.open().value == message.value  # type: ignore[union-attr]

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

    received = await transport.receive()

    assert received is None


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

    received = await transport.receive()
    assert received is not None

    await transport.acknowledge(received)

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

    received = await transport.receive()
    assert received is not None

    await transport.reject(received)

    async with db.connection(name) as connection:
        row_count = (
            await connection.execute(text("SELECT COUNT(*) FROM messages"))
        ).scalar()

    assert row_count == 0
