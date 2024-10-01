from pathlib import Path

from pydantic import HttpUrl

from expanse.http.helpers import view
from expanse.http.response import Response
from expanse.routing.route import Route
from expanse.routing.router import Router
from expanse.static.static_service_provider import StaticServiceProvider
from expanse.testing.client import TestClient
from expanse.view.view_service_provider import ViewServiceProvider


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

    (await client.app.container.get(Router)).add_route(Route.get("/foo", foo))

    response = client.get("/foo")
    assert response.status_code == 200
    assert "/static/foo.txt" in response.text


async def test_static_url_includes_base_url(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["static.paths"] = [FIXTURES_DIR]
    client.app.config["static.prefix"] = "/assets/"
    client.app.config["static.url"] = HttpUrl("https://assets.example.com/")
    client.app.config["view.paths"] = [FIXTURES_DIR]
    await client.app.register(ViewServiceProvider(client.app.container))
    await client.app.register(provider)
    await provider.boot()

    async def foo() -> Response:
        return await view("foo")

    (await client.app.container.get(Router)).add_route(Route.get("/foo", foo))

    response = client.get("/foo")
    assert response.status_code == 200
    assert "https://assets.example.com/assets/foo.txt" in response.text


async def test_static_url_with_empty_prefix(client: TestClient) -> None:
    provider = StaticServiceProvider(client.app.container)

    client.app.config["app.debug"] = False
    client.app.config["static.paths"] = [FIXTURES_DIR]
    client.app.config["static.prefix"] = ""
    client.app.config["static.url"] = HttpUrl("https://assets.example.com/")
    client.app.config["view.paths"] = [FIXTURES_DIR]
    await client.app.register(ViewServiceProvider(client.app.container))
    await client.app.register(provider)
    await provider.boot()

    async def foo() -> Response:
        return await view("foo")

    (await client.app.container.get(Router)).add_route(Route.get("/foo", foo))

    response = client.get("/foo")
    assert response.status_code == 200
    assert "https://assets.example.com/foo.txt" in response.text
