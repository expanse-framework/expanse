from expanse.http.response import Response
from expanse.routing.helpers import get
from expanse.routing.router import Router
from expanse.testing.test_client import TestClient
from expanse.view.view_factory import ViewFactory


def simple_view(view: ViewFactory) -> Response:
    return view.make("simple")


def test_simple_route_are_properly_registered(
    router: Router, client: TestClient
) -> None:
    router.add_route(get("/", simple_view))

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "This is a view" in response.text
