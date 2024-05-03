from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.common.foundation.http.exceptions import HTTPException


async def error() -> Response:
    raise Exception("Internal error")


async def forbidden() -> Response:
    raise HTTPException(403, "Forbidden")


def test_unhandled_exceptions_are_returned_with_debug_information_if_debug_mode(
    router: Router, client: TestClient
) -> None:
    router.get("/error", error)

    with client.handle_exceptions():
        response = client.get("/error", headers=[("Accept", "application/json")])

    assert response.status_code == 500
    assert response.json() == {
        "message": "Internal error",
        "exception": "Exception",
        "file": str(__file__),
        "line": 8,
    }


def test_unhandled_exceptions_are_returned_with_basic_information_if_not_debug_mode(
    router: Router, client: TestClient
) -> None:
    client.app.config["app.debug"] = False

    router.get("/error", error)

    with client.handle_exceptions():
        response = client.get("/error", headers=[("Accept", "application/json")])

    assert response.status_code == 500
    assert response.json() == {"message": "Server error"}


def test_http_exceptions_are_displayed_as_json(
    router: Router, client: TestClient
) -> None:
    client.app.config["app.debug"] = False

    router.get("/forbidden", forbidden)

    response = client.get("/forbidden", headers=[("Accept", "application/json")])

    assert response.status_code == 403
    assert response.json() == {"message": "Forbidden"}
