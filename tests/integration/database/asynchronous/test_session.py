from typing import Annotated

import pytest

from expanse.contracts.routing.router import Router
from expanse.database.session import AsyncSession
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.testing.client import TestClient


pytestmark = pytest.mark.db


async def default_session(session: AsyncSession) -> Response:
    return json(
        (
            await session.execute("SELECT id FROM my_table WHERE id = 'sqlite' LIMIT 1")
        ).scalar()
    )


def test_the_default_session_can_be_injected(
    router: Router, client: TestClient
) -> None:
    router.get("/default", default_session)

    response = client.get("/default")

    assert response.json() == "sqlite"


@pytest.mark.parametrize(
    "name",
    [
        "sqlite",
        "sqlite2",
        "postgresql",
        "postgresql_psycopg",
        "postgresql_asyncpg",
        # "mysql",
        # "mysql_asyncmy",
        # "mysql_aiomysql",
    ],
)
async def test_a_named_session_can_be_injected(
    router: Router, client: TestClient, name: str
) -> None:
    async def named_session(connection: Annotated[AsyncSession, name]) -> Response:
        return json(
            await connection.scalar(
                "SELECT id FROM my_table WHERE id = :id LIMIT 1", {"id": name}
            )
        )

    router.get("/named", named_session)

    response = client.get("/named")

    assert response.json() == name


def test_the_default_session_is_shared_when_requested_by_name(
    router: Router, client: TestClient
) -> None:
    async def sessions(
        session: AsyncSession,
        named: Annotated[AsyncSession, "sqlite"],
        other: Annotated[AsyncSession, "sqlite2"],
    ) -> Response:
        return json(
            {
                "same": named is session,
                "same_connection": named.bind is session.bind,
                "other_connection": other.bind is not session.bind,
            }
        )

    router.get("/sessions", sessions)

    response = client.get("/sessions")

    assert response.json() == {
        "same": True,
        "same_connection": True,
        "other_connection": True,
    }
