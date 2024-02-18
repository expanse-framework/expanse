from expanse.http.response import Response
from expanse.routing.helpers import get
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from expanse.view.view_factory import ViewFactory


def simple_view(view: ViewFactory) -> Response:
    return view.make("globals")


def test_simple_route_are_properly_registered(
    router: Router, client: TestClient
) -> None:
    router.add_route(get("/", simple_view))
    router.add_route(get("/route/{param1:int}", simple_view, name="some.route"))

    response = client.get("/")

    # url global
    assert "/foo/bim/42" in response.text
    # route global
    assert "/route/42" in response.text
