from typing import Annotated

import pytest

from expanse.database.session import AsyncSession
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.routing.router import Router
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
