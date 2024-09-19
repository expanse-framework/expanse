from expanse.http.helpers import respond
from expanse.http.response_adapter import ResponseAdapter
from expanse.routing.router import Router
from expanse.testing.client import TestClient


class CustomResponseType:
    def __init__(self, content: str) -> None:
        self.content = content


def text_response() -> str:
    return "foo"


def custom_response() -> CustomResponseType:
    return CustomResponseType("Custom response")


def configure_adapter(adapter: ResponseAdapter) -> None:
    adapter.register_adapter(
        CustomResponseType, lambda response: respond().text(response.content)
    )


def test_string_adapter_adapts_response(router: Router, client: TestClient) -> None:
    router.get("/", text_response)

    response = client.get("/")

    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == "foo"


def test_register_new_adapter(router: Router, client: TestClient) -> None:
    client.app.container.on_resolved(ResponseAdapter, configure_adapter)

    router.get("/", custom_response)

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.text == "Custom response"
