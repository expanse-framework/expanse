from expanse.contracts.routing.router import Router
from expanse.core.http.middleware.middleware import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.testing.client import TestClient
from expanse.types.http.middleware import RequestHandler


class SimpleMiddleware(Middleware):
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        response = await next_call(request)

        response.headers["X-Foo"] = "bar"

        return response


def test_route_group_with_middlewares(client: TestClient, router: Router) -> None:
    with router.group("api") as group:
        group.middleware(SimpleMiddleware)
        group.get("/", lambda: Response("Hello world!"))

    response = client.get("/")

    assert response.headers["X-Foo"] == "bar"


def test_nested_groups(client: TestClient, router: Router) -> None:
    with router.group("api") as group:
        group.get("/", lambda: Response("Hello world!"))

        with group.group("v1", prefix="/v1") as v1:
            v1.get("", lambda: Response("Hello world (V1)!"))

    response = client.get("/")

    assert response.text == "Hello world!"

    response = client.get("/v1")

    assert response.text == "Hello world (V1)!"
