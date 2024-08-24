from typing import Annotated

import pytest

from expanse.database.session import Session
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient


def default_session(session: Session) -> Response:
    return json(
        (
            session.execute("SELECT id FROM my_table WHERE id = 'sqlite' LIMIT 1")
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
        "postgresql_psycopg2",
        "postgresql_pg8000",
    ],
)
def test_a_named_session_can_be_injected(
    router: Router, client: TestClient, name: str
) -> None:
    def named_session(session: Annotated[Session, name]) -> Response:
        return json(
            session.scalar(
                "SELECT id FROM my_table WHERE id = :id LIMIT 1", {"id": name}
            )
        )

    router.get("/named", named_session)

    response = client.get("/named")

    assert response.json() == name
