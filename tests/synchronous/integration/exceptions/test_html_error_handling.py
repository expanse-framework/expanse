from expanse.common.core.http.exceptions import HTTPException
from expanse.contracts.debug.exception_renderer import (
    ExceptionRenderer as BaseExceptionRenderer,
)
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient


class ExceptionRenderer(BaseExceptionRenderer):
    def __init__(self) -> None:
        self.rendered: bool = False

    def render(self, exception: Exception) -> str:
        self.rendered = True

        return "Rendered"


def error() -> Response:
    raise Exception("Internal error")


def forbidden() -> Response:
    raise HTTPException(403, "Forbidden")


def test_unhandled_exceptions_are_displayed_with_debug_information_if_debug_mode(
    router: Router, client: TestClient
) -> None:
    router.get("/error", error)

    with client.handle_exceptions():
        response = client.get("/error")

    assert response.status_code == 500
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "Internal error" in response.text


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

    response = client.get("/forbidden")

    assert response.status_code == 403
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "Forbidden" in response.text


def test_http_exception_are_displayed_via_renderer_if_configured(
    router, client: TestClient
) -> None:
    renderer = ExceptionRenderer()
    client.app.container.instance(BaseExceptionRenderer, renderer)

    router.get("/error", error)

    with client.handle_exceptions():
        response = client.get("/error")

    assert response.status_code == 500
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert response.text == "Rendered"
    assert renderer.rendered
