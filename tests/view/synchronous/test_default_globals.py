from expanse.contracts.routing.router import Router
from expanse.testing.client import TestClient
from expanse.view.view import View
from expanse.view.view_factory import ViewFactory


def simple_view(view: ViewFactory) -> View:
    return view.make("globals")


def test_simple_route_are_properly_registered(
    router: Router, client: TestClient
) -> None:
    router.get("/", simple_view)
    router.get("/route/{foo}/{bar}", simple_view, name="some.route")

    response = client.get("/")

    # url global
    assert "/foo/bar" in response.text
    # route global
    assert "/route/bim/42" in response.text
