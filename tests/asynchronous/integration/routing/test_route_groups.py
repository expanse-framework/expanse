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


def test_route_group_with_middlewares(client: TestClient, router: Router) -> None:
    with router.group("api") as group:
        group.middleware(SimpleMiddleware)
        group.get("/", lambda: Response("Hello world!"))

    response = client.get("/")

    assert response.headers["X-Foo"] == "bar"
