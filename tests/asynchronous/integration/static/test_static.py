from pathlib import Path

from expanse.asynchronous.http.helpers import view
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.route import Route
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.static.static_service_provider import StaticServiceProvider
from expanse.asynchronous.testing.client import TestClient
from expanse.asynchronous.view.view_service_provider import ViewServiceProvider


FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_endpoint_returns_static_content_successfully(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["static.paths"] = [FIXTURES_DIR]
    await client.app.register(provider)
    await provider.boot()

    response = client.get("/static/foo.txt")
    assert response.status_code == 200
    assert response.text.strip() == "Foo"


async def test_endpoint_is_not_set_up_if_not_debug_mode(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["app.debug"] = False
    client.app.config["static.paths"] = [FIXTURES_DIR]
    await client.app.register(provider)
    await provider.boot()

    response = client.get("/static/foo.txt")
    assert response.status_code == 404


async def test_view_static_function_is_registered_successfully(
    client: TestClient,
) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["static.paths"] = [FIXTURES_DIR]
    client.app.config["view.paths"] = [FIXTURES_DIR]
    await client.app.register(ViewServiceProvider(client.app.container))
    await client.app.register(provider)
    await provider.boot()

    async def foo() -> Response:
        return await view("foo")

    (await client.app.container.make(Router)).add_route(Route.get("/foo", foo))

    response = client.get("/foo")
    assert response.status_code == 200
    assert "/static/foo.txt" in response.text


async def test_static_url_includes_base_url(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["static.paths"] = [FIXTURES_DIR]
    client.app.config["static.prefix"] = "/assets"
    client.app.config["static.url"] = "https://assets.example.com"
    client.app.config["view.paths"] = [FIXTURES_DIR]
    await client.app.register(ViewServiceProvider(client.app.container))
    await client.app.register(provider)
    await provider.boot()

    async def foo() -> Response:
        return await view("foo")

    (await client.app.container.make(Router)).add_route(Route.get("/foo", foo))

    response = client.get("/foo")
    assert response.status_code == 200
    assert "https://assets.example.com/assets/foo.txt" in response.text
