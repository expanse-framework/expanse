from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.common.core.http.exceptions import HTTPException


async def error() -> Response:
    raise Exception("Internal error")


async def forbidden() -> Response:
    raise HTTPException(403, "Forbidden")


def test_unhandled_exceptions_are_displayed_with_debug_information_if_debug_mode(
    router: Router, client: TestClient
) -> None:
    router.get("/error", error)

    with client.handle_exceptions():
        response = client.get("/error")

    assert response.status_code == 500
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.text == f"Exception: Internal error in {__file__} at line 8"


def test_unhandled_exceptions_are_displayed_with_basic_information_if_not_debug_mode(
    router: Router, client: TestClient
) -> None:
    client.app.config["app.debug"] = False

    router.get("/error", error)

    with client.handle_exceptions():
        response = client.get("/error")

    assert response.status_code == 500
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "Server Error" in response.text


def test_http_exceptions_are_displayed_via_a_dedicated_html_page(
    router: Router, client: TestClient
) -> None:
    router.get("/forbidden", forbidden)

    with client.handle_exceptions():
        response = client.get("/forbidden")

    assert response.status_code == 403
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "Forbidden" in response.text
