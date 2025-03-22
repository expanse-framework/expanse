from expanse.contracts.routing.router import Router
from expanse.http.response import Response
from expanse.testing.client import TestClient


async def handler() -> Response:
    return Response("Hello, world!").with_cookie("foo", "bar")


def test_cookies_are_encrypted(client: TestClient, router: Router) -> None:
    client.app.config["session.store"] = "dictionary"

    router.get("/", handler).middleware("web")

    response = client.get("/")
    assert response.status_code == 200

    cookie = response.cookies.get("foo")
    assert cookie is not None
    assert cookie != "bar"
