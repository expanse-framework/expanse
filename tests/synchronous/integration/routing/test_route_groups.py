from expanse.foundation.http.middleware.middleware import Middleware
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


def test_route_group_with_middlewares(client: TestClient, router: Router) -> None:
    with router.group("api").middleware(SimpleMiddleware) as group:
        group.get("/", lambda: Response("Hello world!"))

    response = client.get("/")

    assert response.headers["X-Foo"] == "bar"
