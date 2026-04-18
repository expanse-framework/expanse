import os

from typing import TYPE_CHECKING
from typing import Annotated

import pytest

from expanse.core.application import Application
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.redis.synchronous.connections.connection import Connection
from expanse.routing.router import Router
from expanse.testing.client import TestClient


if TYPE_CHECKING:
    from expanse.configuration.config import Config


def default_connection(connection: Connection) -> Response:
    connection.set("test_key", "test_value")
    result = connection.get("test_key")
    return json(result)


def test_the_default_session_can_be_injected(
    router: Router, client: TestClient
) -> None:
    router.get("/default", default_connection)

    response = client.get("/default")

    assert response.json() == "test_value"


@pytest.mark.parametrize(
    "name",
    ["default", "no_backoff"],
)
def test_a_named_connection_can_be_injected(
    app: Application, router: Router, client: TestClient, name: str
) -> None:
    config: Config = app.config

    config["redis"] = {
        "default": "default",
        "connections": {
            "default": {
                "driver": "redis",
                "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/0",
            },
            "no_backoff": {
                "driver": "redis",
                "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/1",
                "backoff": None,
            },
        },
    }

    def named_connection(connection: Annotated[Connection, name]) -> Response:
        connection.set("test_key", name)
        result = connection.get("test_key")
        return json(result)

    router.get("/named", named_connection)

    response = client.get("/named")

    assert response.json() == name
