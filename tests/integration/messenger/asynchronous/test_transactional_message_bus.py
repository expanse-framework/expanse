from dataclasses import dataclass

import pytest

from expanse.contracts.messenger.asynchronous.message_bus import MessageBus
from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
from expanse.database.asynchronous.session import AsyncSession
from expanse.http.request import Request
from expanse.http.responses.response import Response
from expanse.routing.helpers import get
from expanse.testing.client import TestClient
from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@dataclass
class TestMessage:
    content: str


@get("/test")
async def route(session: AsyncSession, request: Request, bus: MessageBus) -> Response:
    await bus.dispatch(TestMessage("test message"))

    return Response("ok")


@get("/test-commit")
async def commit_route(
    session: AsyncSession, request: Request, bus: MessageBus
) -> Response:
    await bus.dispatch(TestMessage("test message"))
    await session.commit()

    return Response("ok")


@get("/test-rollback")
async def rollback_route(
    session: AsyncSession, request: Request, bus: MessageBus
) -> Response:
    await bus.dispatch(TestMessage("test message"))
    await session.rollback()
    await bus.dispatch(TestMessage("message after rollback"))
    await session.commit()

    return Response("ok")


@pytest.mark.usefixtures("setup_databases")
async def test_messages_are_not_dispatched_if_transaction_is_not_committed(
    app: Application, router: Router, client: TestClient, command_tester: CommandTester
) -> None:
    app.config["messenger"] = {
        "transport": "db",
        "transports": {
            "db": {
                "driver": "database",
                "connection": "sqlite",
                "table_name": "messages",
            }
        },
    }
    command_tester.command("db migrate").run()

    router.handler(route)

    response = client.get("/test")

    assert response.status_code == 200
    assert response.text == "ok"

    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection("sqlite") as connection:
        result = await connection.execute("SELECT * FROM messages")
        messages = result.fetchall()

        assert len(messages) == 0


@pytest.mark.usefixtures("setup_databases")
async def test_messages_are_dispatched_after_transaction_is_committed(
    app: Application, router: Router, client: TestClient, command_tester: CommandTester
) -> None:
    app.config["messenger"] = {
        "transport": "db",
        "transports": {
            "db": {
                "driver": "database",
                "connection": "sqlite",
                "table_name": "messages",
            }
        },
    }
    command_tester.command("db migrate").run()

    router.handler(commit_route)

    response = client.get("/test-commit")

    assert response.status_code == 200
    assert response.text == "ok"

    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection("sqlite") as connection:
        result = await connection.execute("SELECT * FROM messages")
        messages = result.fetchall()

        assert len(messages) == 1
        assert (
            messages[0].body
            == '{"data": "{\\"content\\":\\"test message\\"}", "type": "tests.integration.messenger.asynchronous.test_transactional_message_bus.TestMessage"}'
        )


@pytest.mark.usefixtures("setup_databases")
async def test_messages_are_cleared_after_transaction_is_rolled_back(
    app: Application, router: Router, client: TestClient, command_tester: CommandTester
) -> None:
    app.config["messenger"] = {
        "transport": "db",
        "transports": {
            "db": {
                "driver": "database",
                "connection": "sqlite",
                "table_name": "messages",
            }
        },
    }
    command_tester.command("db migrate").run()

    router.handler(rollback_route)

    response = client.get("/test-rollback")

    assert response.status_code == 200
    assert response.text == "ok"

    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection("sqlite") as connection:
        result = await connection.execute("SELECT * FROM messages")
        messages = result.fetchall()

        assert len(messages) == 1
        assert (
            messages[0].body
            == '{"data": "{\\"content\\":\\"message after rollback\\"}", "type": "tests.integration.messenger.asynchronous.test_transactional_message_bus.TestMessage"}'
        )
