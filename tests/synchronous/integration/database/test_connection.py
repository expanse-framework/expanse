from typing import Annotated

import pytest

from expanse.database.connection import Connection
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient


def default_connection(connection: Connection) -> Response:
    return json(
        (
            connection.execute("SELECT id FROM my_table WHERE id = 'sqlite' LIMIT 1")
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
    [
        "sqlite",
        "sqlite2",
        "postgresql",
        "postgresql_psycopg",
        "postgresql_psycopg2",
        "postgresql_pg8000",
    ],
)
def test_a_named_connection_can_be_injected(
    router: Router, client: TestClient, name: str
) -> None:
    def named_connection(connection: Annotated[Connection, name]) -> Response:
        return json(
            connection.scalar(
                "SELECT id FROM my_table WHERE id = :id LIMIT 1", {"id": name}
            )
        )

    router.get("/named", named_connection)

    response = client.get("/named")

    assert response.json() == name
