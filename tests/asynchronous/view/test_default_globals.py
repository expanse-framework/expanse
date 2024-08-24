from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.asynchronous.view.view import View
from expanse.asynchronous.view.view_factory import ViewFactory


async def simple_view(view: ViewFactory) -> View:
    return await view.make("globals")


def test_simple_route_are_properly_registered(
    router: Router, client: TestClient
) -> None:
    router.get("/", simple_view)
    router.get("/route/{param1:int}", simple_view, name="some.route")

    response = client.get("/")

    # url global
    assert "/foo/bim/42" in response.text
    # route global
    assert "/route/42" in response.text
