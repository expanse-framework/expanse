from contextvars import ContextVar

from expanse.contracts.routing.router import Router
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.testing.client import TestClient
from expanse.types.http.middleware import RequestHandler


ctxvar: ContextVar[str] = ContextVar("ctxvar")


class TestMiddleware:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        ctxvar.set("Set by middleware")
        response = await next_call(request)
        assert ctxvar.get() == "Set by endpoint"
        return response


def test_contextvars_are_properly_propagated_with_async_endpoint(
    client: TestClient, router: Router
) -> None:
    async def test_contextvars() -> Response:
        assert ctxvar.get() == "Set by middleware"
        ctxvar.set("Set by endpoint")

        return Response("Response")

    router.get("/test", test_contextvars).middleware(TestMiddleware)

    response = client.get("/test")

    assert response.status_code == 200
    assert response.text == "Response"


def test_contextvars_are_properly_propagated_with_sync_endpoint(
    client: TestClient, router: Router
) -> None:
    def test_contextvars() -> Response:
        assert ctxvar.get() == "Set by middleware"
        ctxvar.set("Set by endpoint")

        return Response("Response")

    router.get("/test", test_contextvars).middleware(TestMiddleware)

    response = client.get("/test")

    assert response.status_code == 200
    assert response.text == "Response"
