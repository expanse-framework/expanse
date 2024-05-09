import pytest

from expanse.core.http.middleware.middleware import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from expanse.types.http.middleware import RequestHandler


class SimpleMiddleware(Middleware):
    def handle(self, request: Request, next_call: RequestHandler) -> Response:
        response = next_call(request)

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
