import pytest

from expanse.contracts.routing.router import Router
from expanse.core.http.middleware.middleware import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.helpers import delete
from expanse.routing.helpers import get
from expanse.routing.helpers import group
from expanse.routing.helpers import patch
from expanse.routing.helpers import post
from expanse.routing.helpers import put
from expanse.testing.client import TestClient
from expanse.types.http.middleware import RequestHandler


class SimpleMiddleware(Middleware):
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        response = await next_call(request)

        response.headers["X-Foo"] = "bar"

        return response


class MyController:
    @get("/foo", name="foo")
    def foo(self) -> Response:
        return Response("Hello world!")

    @get("/middleware", middleware=SimpleMiddleware)
    def middleware(self) -> Response:
        return Response("Middleware")

    @post("/post", name="post")
    def post(self) -> Response:
        return Response("POST")

    @put("/put", name="put")
    def put(self) -> Response:
        return Response("PUT")

    @patch("/patch", name="patch")
    def patch(self) -> Response:
        return Response("PATCH")

    @delete("/delete", name="delete")
    def delete(self) -> Response:
        return Response("DELETE")


@group("group", prefix="/group")
class MyGroupController(MyController): ...


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


def test_routes_can_be_registered_via_decorators(
    router: Router, client: TestClient
) -> None:
    @get("/foo", name="foo")
    def foo() -> Response:
        return Response("Hello world!")

    router.handler(foo)

    response = client.get("/foo")

    assert response.text == "Hello world!"


def test_routes_can_be_registered_via_decorators_on_controller(
    router: Router, client: TestClient
) -> None:
    router.controller(MyController)

    response = client.get("/foo")
    assert response.text == "Hello world!"

    response = client.get("/middleware")
    assert response.text == "Middleware"
    assert response.headers["X-Foo"] == "bar"

    response = client.post("/post")
    assert response.text == "POST"

    response = client.put("/put")
    assert response.text == "PUT"

    response = client.patch("/patch")
    assert response.text == "PATCH"

    response = client.delete("/delete")
    assert response.text == "DELETE"


def test_routes_can_be_registered_and_grouped_via_decorators_on_controller(
    router: Router, client: TestClient
) -> None:
    router.controller(MyGroupController)

    response = client.get("/group/foo")
    assert response.text == "Hello world!"

    response = client.get("/group/middleware")
    assert response.text == "Middleware"
    assert response.headers["X-Foo"] == "bar"

    response = client.post("/group/post")
    assert response.text == "POST"

    response = client.put("/group/put")
    assert response.text == "PUT"

    response = client.patch("/group/patch")
    assert response.text == "PATCH"

    response = client.delete("/group/delete")
    assert response.text == "DELETE"
