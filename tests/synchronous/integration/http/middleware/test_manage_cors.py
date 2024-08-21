from typing import TYPE_CHECKING

import pytest

from expanse.core.application import Application
from expanse.core.http.gateway import Gateway
from expanse.http.middleware.manage_cors import ManageCors
from expanse.http.response import Response
from expanse.routing.responder import Responder
from expanse.testing.client import TestClient


if TYPE_CHECKING:
    from expanse.routing.router import Router


@pytest.fixture(autouse=True)
def setup_app(app: Application) -> None:
    gateway = app.container.make(Gateway)
    gateway.prepend_middleware(ManageCors)

    router: Router = app.container.make("router")

    def ping(responder: Responder) -> Response:
        return responder.json("pong")

    def error(responder: Responder) -> Response:
        return responder.abort(500)

    router.post("/api/ping", ping)
    router.post("/api/error", error)
    router.post("/web/ping", lambda: Response("pong", content_type="text/plain"))

    app.config["cors"] = {
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


def test_allow_all_origins(
    client: TestClient,
) -> None:
    client.app.config["cors"]["allowed_origins"] = ["*"]
    response = client.options(
        "/api/ping",
        headers={"Origin": "http://localhost", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "*"


def test_allow_exact_origin(
    client: TestClient,
) -> None:
    client.app.config["cors"]["allowed_origins"] = [
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


def test_allow_all_origins_wildcard(
    client: TestClient,
) -> None:
    client.app.config["cors"]["allowed_origins"] = ["*.python-expanse.org"]
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


def test_allowed_origins_wildcard_includes_nested_subdomain(
    client: TestClient,
) -> None:
    client.app.config["cors"]["allowed_origins"] = ["*.python-expanse.org"]
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


def test_allowed_origins_wildcard_no_match(
    client: TestClient,
) -> None:
    client.app.config["cors"]["allowed_origins"] = ["*.python-expanse.org"]
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


def test_method_allow_all_methods_allowed(
    client: TestClient,
) -> None:
    client.app.config["cors"]["allowed_methods"] = ["*"]

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


def test_allowed_headers_allow_wildcard(
    client: TestClient,
) -> None:
    client.app.config["cors"]["allowed_headers"] = ["*"]

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


def test_allowed_headers_wildcard(
    client: TestClient,
) -> None:
    client.app.config["cors"]["allowed_headers"] = ["*"]

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
    response = client.post(
        "/api/error",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 500
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost"


def test_supports_credentials(
    client: TestClient,
) -> None:
    client.app.config["cors"]["supports_credentials"] = True
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


def test_exposed_headers(
    client: TestClient,
) -> None:
    client.app.config["cors"]["exposed_headers"] = ["X-Foo"]
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
