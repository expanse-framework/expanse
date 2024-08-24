from expanse.routing.router import Router
from expanse.testing.client import TestClient
from expanse.view.view import View
from expanse.view.view_factory import ViewFactory


def simple_view(view: ViewFactory) -> View:
    return view.make("simple")


def test_simple_route_are_properly_registered(
    router: Router, client: TestClient
) -> None:
    router.get("/", simple_view)

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "This is a view" in response.text
