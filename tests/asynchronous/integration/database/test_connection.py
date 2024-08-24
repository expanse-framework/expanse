from typing import Annotated

import pytest

from expanse.asynchronous.database.connection import Connection
from expanse.asynchronous.http.helpers import json
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient


async def default_connection(connection: Connection) -> Response:
    return await json(
        (
            await connection.execute(
                "SELECT id FROM my_table WHERE id = 'sqlite' LIMIT 1"
            )
        ).scalar()
    )


def test_the_default_connection_can_be_injected(
    router: Router, client: TestClient
) -> None:
    router.get("/default", default_connection)

    response = client.get("/default")

    assert response.json() == "sqlite"


@pytest.mark.parametrize(
    "name",
    ["sqlite", "sqlite2", "postgresql", "postgresql_psycopg", "postgresql_asyncpg"],
)
def test_a_named_connection_can_be_injected(
    router: Router, client: TestClient, name: str
) -> None:
    async def named_connection(connection: Annotated[Connection, name]) -> Response:
        return await json(
            await connection.scalar(
                "SELECT id FROM my_table WHERE id = :id LIMIT 1", {"id": name}
            )
        )

    router.get("/named", named_connection)

    response = client.get("/named")

    assert response.json() == name
