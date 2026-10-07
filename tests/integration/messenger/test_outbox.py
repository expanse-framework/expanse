import pytest

from sqlalchemy import text

from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.message_bus import MessageBus
from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
from expanse.database.asynchronous.session import AsyncSession
from expanse.http.responses.response import Response
from expanse.messenger.registry import Registry
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.transports.memory.transport import MemoryTransport
from expanse.messenger.transports.outbox.transport import OutboxTransport
from expanse.messenger.transports.transport_manager import TransportManager
from expanse.messenger.worker import Worker
from expanse.routing.helpers import get
from expanse.testing.client import TestClient
from expanse.testing.command_tester import CommandTester
from tests.integration.messenger.fixtures.messages import DatabaseMessage


pytestmark = pytest.mark.db


async def _target_transport(container: Container) -> MemoryTransport:
    transport_manager = await container.get(TransportManager)
    transport = await transport_manager.transport("memory")
    assert isinstance(transport, OutboxTransport)

    target = transport.target_transport
    assert isinstance(target, MemoryTransport)

    return target


async def _begin(session: AsyncSession) -> None:
    # Make the session start its transaction on the underlying connection,
    # as it would when loading or flushing models, so that the outbox
    # insert joins it.
    await session.execute(text("SELECT 1"))


@get("/outbox-commit")
async def commit_route(
    session: AsyncSession, bus: MessageBus, container: Container
) -> Response:
    async with session.begin():
        await _begin(session)
        await bus.dispatch(DatabaseMessage(value="hello"))

    target = await _target_transport(container)

    return Response(str(len(target.sent)))


@get("/outbox-rollback")
async def rollback_route(
    session: AsyncSession, bus: MessageBus, container: Container
) -> Response:
    async with session.begin():
        await _begin(session)
        await bus.dispatch(DatabaseMessage(value="hello"))
        await session.rollback()

    target = await _target_transport(container)

    return Response(str(len(target.sent)))


@get("/outbox-dispatch-first")
async def dispatch_first_route(session: AsyncSession, bus: MessageBus) -> Response:
    async with session.begin():
        await bus.dispatch(DatabaseMessage(value="hello"))

    return Response("ok")


@pytest.fixture(params=["sqlite", "postgresql"])
def connection_name(
    request: pytest.FixtureRequest,
    setup_databases: None,
    app: Application,
    router: Router,
    command_tester: CommandTester,
) -> str:
    name: str = request.param
    app.config["database"]["default"] = name
    app.config["messenger"] = {
        "transport": "memory",
        "transports": {
            "memory": {"driver": "memory", "outbox": "outbox"},
            "outbox": {
                "driver": "database",
                "connection": name,
                "table_name": "messages",
            },
        },
    }

    command_tester.command("db migrate").run()

    router.handler(commit_route)
    router.handler(rollback_route)
    router.handler(dispatch_first_route)

    return name


async def _count_outbox_messages(app: Application, connection_name: str) -> int:
    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection(connection_name) as connection:
        result = await connection.execute(text("SELECT COUNT(*) FROM messages"))

        return int(result.scalar_one())


async def test_messages_are_stored_in_the_outbox_when_the_transaction_is_committed(
    app: Application, client: TestClient, connection_name: str
) -> None:
    response = client.get("/outbox-commit")

    assert response.status_code == 200
    # Nothing is sent to the target transport directly
    assert response.text == "0"
    assert await _count_outbox_messages(app, connection_name) == 1


async def test_messages_are_not_stored_in_the_outbox_when_the_transaction_is_rolled_back(
    app: Application,
    client: TestClient,
    connection_name: str,
    request: pytest.FixtureRequest,
) -> None:
    if connection_name == "sqlite":
        request.applymarker(
            pytest.mark.xfail(
                strict=True,
                reason=(
                    "The SQLite driver does not emit BEGIN before the outbox"
                    " savepoint, so releasing it commits the message."
                ),
            )
        )

    response = client.get("/outbox-rollback")

    assert response.status_code == 200
    assert response.text == "0"
    assert await _count_outbox_messages(app, connection_name) == 0


async def test_outboxed_messages_are_relayed_to_and_handled_from_the_target_transport(
    app: Application, client: TestClient, connection_name: str
) -> None:
    handled: list[DatabaseMessage] = []

    def handler(message: DatabaseMessage) -> None:
        handled.append(message)

    registry = await app.container.get(Registry)
    registry.register(DatabaseMessage, handler)

    client.get("/outbox-commit")

    assert await _count_outbox_messages(app, connection_name) == 1

    async with app.container.create_scoped_container() as container:
        worker = await container.get(Worker)

        # Relay the message from the outbox to the target transport
        await worker.run("outbox", limit=1)

        assert handled == []
        assert await _count_outbox_messages(app, connection_name) == 0

        target = await _target_transport(container)
        assert len(target.sent) == 1
        assert target.sent[0].open() == DatabaseMessage(value="hello")
        assert not target.sent[0].has_stamp(OutboxStamp)

        # Handle the message from the target transport
        await worker.run("memory", limit=1)

        assert handled == [DatabaseMessage(value="hello")]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "When the outbox insert is the first statement of the session transaction,"
        " it begins its own transaction on the shared connection, which the"
        " session commit does not commit."
    ),
)
async def test_messages_are_stored_in_the_outbox_when_dispatching_first_in_a_transaction(
    app: Application, client: TestClient, connection_name: str
) -> None:
    if connection_name == "sqlite":
        pytest.skip(
            "SQLite implicitly commits the outbox savepoint outside a transaction"
        )

    response = client.get("/outbox-dispatch-first")

    assert response.status_code == 200
    assert await _count_outbox_messages(app, connection_name) == 1
