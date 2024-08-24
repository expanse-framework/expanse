from pathlib import Path

from expanse.routing.route import Route
from expanse.routing.router import Router
from expanse.static.static_service_provider import StaticServiceProvider
from expanse.testing.client import TestClient
from expanse.view.view import View
from expanse.view.view_factory import ViewFactory
from expanse.view.view_service_provider import ViewServiceProvider


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_endpoint_returns_static_content_successfully(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["static.paths"] = [FIXTURES_DIR]
    client.app.register(provider)
    provider.boot()

    response = client.get("/static/foo.txt")
    assert response.status_code == 200
    assert response.text.strip() == "Foo"


def test_endpoint_is_not_set_up_if_not_debug_mode(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["app.debug"] = False
    client.app.config["static.paths"] = [FIXTURES_DIR]
    client.app.register(provider)
    provider.boot()

    response = client.get("/static/foo.txt")
    assert response.status_code == 404


def test_view_static_function_is_registered_successfully(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["static.paths"] = [FIXTURES_DIR]
    client.app.config["view.paths"] = [FIXTURES_DIR]
    client.app.register(ViewServiceProvider(client.app.container))
    client.app.register(provider)
    provider.boot()

    def foo(view: ViewFactory) -> View:
        return view.make("foo")

    client.app.container.make(Router).get("/foo", foo)

    response = client.get("/foo")
    assert response.status_code == 200
    assert "/static/foo.txt" in response.text


def test_static_url_includes_base_url(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["static.paths"] = [FIXTURES_DIR]
    client.app.config["static.prefix"] = "/assets"
    client.app.config["static.url"] = "https://assets.example.com"
    client.app.config["view.paths"] = [FIXTURES_DIR]
    client.app.register(ViewServiceProvider(client.app.container))
    client.app.register(provider)
    provider.boot()

    def foo(view: ViewFactory) -> View:
        return view.make("foo")

    client.app.container.make(Router).add_route(Route.get("/foo", foo))

    response = client.get("/foo")
    assert response.status_code == 200
    assert "https://assets.example.com/assets/foo.txt" in response.text
