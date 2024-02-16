from expanse.asynchronous.foundation.http.middleware.middleware import Middleware
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.helpers import get
from expanse.asynchronous.routing.helpers import group
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.asynchronous.types.http.middleware import RequestHandler


class SimpleMiddleware(Middleware):
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        response = await next_call(request)

        response.headers["X-Foo"] = "bar"

        return response


def test_route_group_with_middlewares(client: TestClient, router: Router) -> None:
    api_group = group("api").middleware(SimpleMiddleware)
    api_group.add_route(get("/", lambda: Response("Hello world!")))
    router.add_group(api_group)

    response = client.get("/")

    assert response.headers["X-Foo"] == "bar"
