from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.helpers import get
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.asynchronous.view.view_factory import ViewFactory


async def simple_view(view: ViewFactory) -> Response:
    return await view.make("globals")


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
