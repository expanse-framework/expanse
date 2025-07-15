from expanse.contracts.routing.registrar import Registrar
from expanse.http.responses.response import Response
from expanse.testing.client import TestClient


def test_simple_response(router: Registrar, client: TestClient) -> None:
    router.get(
        "/test",
        lambda: Response("Hello, World!")
        .with_header("X-foo", "bar")
        .with_cookie("cookie_name", "cookie_value"),
    )
    response = client.get("/test")
    assert response.status_code == 200
    assert response.text == "Hello, World!"
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.headers["X-foo"] == "bar"
    assert response.cookies["cookie_name"] == "cookie_value"


def test_json_response(router: Registrar, client: TestClient) -> None:
    router.get("/test", lambda: {"message": "Hello, World!"})
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}
    assert response.headers["Content-Type"] == "application/json"
