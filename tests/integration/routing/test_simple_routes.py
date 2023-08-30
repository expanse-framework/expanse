from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.http.response import Response
from expanse.routing import helpers


if TYPE_CHECKING:
    from expanse.routing.router import Router
    from expanse.testing.test_client import TestClient


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
def test_simple_routes_are_properly_registered(
    router: Router, client: TestClient, method: str
) -> None:
    router.add_route(getattr(helpers, method)("/", lambda: Response("Hello world!")))

    response = getattr(client, method)("/")

    assert response.text == "Hello world!"
