from typing import Annotated

import pytest

from expanse.contracts.routing.router import Router
from expanse.database.session import Session
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.testing.client import TestClient


pytestmark = pytest.mark.db


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
        "mysql",
        "mysql_pymysql",
        "mysql_mysqldb",
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


def test_the_default_session_is_shared_when_requested_by_name(
    router: Router, client: TestClient
) -> None:
    def sessions(
        session: Session,
        named: Annotated[Session, "sqlite"],
        other: Annotated[Session, "sqlite2"],
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
