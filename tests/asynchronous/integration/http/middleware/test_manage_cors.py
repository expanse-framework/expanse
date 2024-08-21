from typing import TYPE_CHECKING

import pytest

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.core.http.gateway import Gateway
from expanse.asynchronous.http.middleware.manage_cors import ManageCors
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.responder import Responder
from expanse.asynchronous.testing.client import TestClient


if TYPE_CHECKING:
    from expanse.asynchronous.routing.router import Router


@pytest.fixture(autouse=True)
async def setup_app(app: Application) -> None:
    (await app.container.make(Gateway)).prepend_middleware(ManageCors)

    router: Router = await app.container.make("router")

    async def ping(responder: Responder) -> Response:
        return await responder.json("pong")

    async def error(responder: Responder) -> Response:
        return await responder.abort(500)

    router.post("/api/ping", ping)
    router.post("/api/error", error)
    router.post("/web/ping", lambda: Response("pong", content_type="text/plain"))

    (await app.container.make("config"))["cors"] = {
        "paths": ["api/*"],
        "supports_credentials": False,
        "allowed_origins": ["http://localhost"],
        "allowed_headers": ["X-Custom-1", "X-Custom-2"],
        "allowed_methods": ["GET", "POST"],
        "exposed_headers": [],
        "max_age": 0,
    }


def test_it_should_return_access_control_allow_origin_when_no_origin_on_request(
    client: TestClient,
) -> None:
    response = client.options(
        "/api/ping", headers={"Access-Control-Request-Method": "POST"}
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"


def test_it_should_return_access_control_allow_origin_with_origin_specified(
    client: TestClient,
) -> None:
    response = client.options(
        "/api/ping",
        headers={"Origin": "http://localhost", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"


async def test_allow_all_origins(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["allowed_origins"] = ["*"]
    response = client.options(
        "/api/ping",
        headers={"Origin": "http://localhost", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "*"


async def test_allow_exact_origin(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["allowed_origins"] = [
        "http://localhost",
        "http://localhost2",
    ]
    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://localhost2",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost2"


async def test_allow_all_origins_wildcard(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["allowed_origins"] = [
        "*.python-expanse.org"
    ]
    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://test.python-expanse.org",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert (
        response.headers["Access-Control-Allow-Origin"]
        == "http://test.python-expanse.org"
    )


async def test_allowed_origins_wildcard_includes_nested_subdomain(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["allowed_origins"] = [
        "*.python-expanse.org"
    ]
    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://foo.bar.test.python-expanse.org",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert (
        response.headers["Access-Control-Allow-Origin"]
        == "http://foo.bar.test.python-expanse.org"
    )


async def test_allowed_origins_wildcard_no_match(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["allowed_origins"] = [
        "*.python-expanse.org"
    ]
    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://test.python-poetry.org",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert "Access-Control-Allow-Origin" not in response.headers


def test_options_allowed_origins_non_existing_route(
    client: TestClient,
) -> None:
    response = client.options(
        "/api/missing",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"


def test_options_origin_not_allowed(
    client: TestClient,
) -> None:
    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://notlocalhost",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"


def test_method_allowed(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Methods" not in response.headers
    assert response.json() == "pong"


def test_method_not_allowed(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "PUT",
        },
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Methods" not in response.headers


async def test_method_allow_all_methods_allowed(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["allowed_methods"] = ["*"]

    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "PUT",
        },
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Methods"] == "PUT"


def test_allowed_headers_allow_options(
    client: TestClient,
) -> None:
    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Custom-1, X-Custom-2",
        },
    )

    assert response.status_code == 204
    assert (
        response.headers["Access-Control-Allow-Headers"]
        == "X-Custom-1, X-Custom-2".lower()
    )
    assert response.text == ""


async def test_allowed_headers_allow_wildcard(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["allowed_headers"] = ["*"]

    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Custom-3",
        },
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Headers"] == "X-Custom-3"
    assert response.text == ""


def test_allowed_headers_not_allowed(
    client: TestClient,
) -> None:
    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Custom-3",
        },
    )

    assert response.status_code == 204
    assert (
        response.headers["Access-Control-Allow-Headers"]
        == "X-Custom-1, X-Custom-2".lower()
    )
    assert response.text == ""


def test_allowed_headers_allowed(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Headers": "X-Custom-1, X-Custom-2",
        },
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Headers" not in response.headers
    assert response.json() == "pong"


async def test_allowed_headers_wildcard(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["allowed_headers"] = ["*"]

    response = client.post(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Headers": "X-Custom-3",
        },
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Headers" not in response.headers
    assert response.json() == "pong"


def test_allowed_headers_post_not_allowed(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Headers": "X-Custom-3",
        },
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Headers" not in response.headers


def test_error(
    client: TestClient,
) -> None:
    client = TestClient(client.app, raise_server_exceptions=False)
    response = client.post(
        "/api/error",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 500
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"


async def test_supports_credentials(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["supports_credentials"] = True
    response = client.options(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_no_matching_path(
    client: TestClient,
) -> None:
    response = client.post(
        "/web/ping",
        headers={"Origin": "http://localhost", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
    assert response.text == "pong"


async def test_exposed_headers(
    client: TestClient,
) -> None:
    (await client.app.container.make("config"))["cors"]["exposed_headers"] = ["X-Foo"]
    response = client.post(
        "/api/ping",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"
    assert response.headers["Access-Control-Expose-Headers"] == "X-Foo"
