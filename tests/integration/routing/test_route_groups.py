from typing import AsyncGenerator

from expanse.foundation.http.middleware.base import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.helpers import group
from expanse.routing.router import Router
from expanse.testing.test_client import TestClient


class SimpleMiddleware(Middleware):
    async def handle(
        self, request: Request
    ) -> AsyncGenerator[Response | None, Response]:
        response = yield

        response.headers["X-Foo"] = "bar"


def test_route_group_with_middlewares(client: TestClient, router: Router) -> None:
    api_group = group("api", middlewares=[SimpleMiddleware])
    api_group.get("/", lambda: Response("Hello world!"))
    router.add_group(api_group)

    response = client.get("/")

    assert response.headers["X-Foo"] == "bar"
