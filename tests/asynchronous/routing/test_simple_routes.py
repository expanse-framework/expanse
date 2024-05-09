import pytest

from expanse.asynchronous.core.http.middleware.middleware import Middleware
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.asynchronous.types.http.middleware import RequestHandler


class SimpleMiddleware(Middleware):
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        response = await next_call(request)

        response.headers["X-Foo"] = "bar"

        return response


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
def test_simple_routes_are_properly_registered(
    router: Router, client: TestClient, method: str
) -> None:
    getattr(router, method)("/", lambda: Response("Hello world!"))

    response = getattr(client, method)("/")

    assert response.text == "Hello world!"


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
def test_routes_with_middleware_are_properly_registered(
    router: Router, client: TestClient, method: str
) -> None:
    getattr(router, method)("/", lambda: Response("Hello world!")).middleware(
        SimpleMiddleware
    )

    response = getattr(client, method)("/")

    assert response.text == "Hello world!"
    assert response.headers["X-Foo"] == "bar"
