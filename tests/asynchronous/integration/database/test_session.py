from typing import Annotated

import pytest

from expanse.asynchronous.contracts.database.session import Session
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.helpers import get
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient


async def default_session(session: Session) -> Response:
    return Response.json(
        (
            await session.execute("SELECT id FROM my_table WHERE id = 'sqlite' LIMIT 1")
        ).scalar()
    )


def test_the_default_session_can_be_injected(
    router: Router, client: TestClient
) -> None:
    router.add_route(get("/default", default_session))

    response = client.get("/default")

    assert response.json() == "sqlite"


@pytest.mark.parametrize(
    "name",
    ["sqlite", "sqlite2", "postgresql", "postgresql_psycopg", "postgresql_asyncpg"],
)
def test_a_named_session_can_be_injected(
    router: Router, client: TestClient, name: str
) -> None:
    async def named_session(connection: Annotated[Session, name]) -> Response:
        return Response.json(
            await connection.scalar(
                "SELECT id FROM my_table WHERE id = :id LIMIT 1", {"id": name}
            )
        )

    router.add_route(get("/named", named_session))

    response = client.get("/named")

    assert response.json() == name
