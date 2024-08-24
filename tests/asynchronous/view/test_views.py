from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.asynchronous.view.view import View
from expanse.asynchronous.view.view_factory import ViewFactory


async def simple_view(view: ViewFactory) -> View:
    return await view.make("simple")


def test_simple_route_are_properly_registered(
    router: Router, client: TestClient
) -> None:
    router.get("/", simple_view)

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "This is a view" in response.text
