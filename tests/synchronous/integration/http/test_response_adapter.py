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


def test_string_adapter_adapts_response_based_on_request_acceptable_type(
    router: Router, client: TestClient
) -> None:
    router.get("/", text_response)

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.text == "foo"

    response = client.get("/", headers={"Accept": "application/json"})

    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == "foo"


def test_register_new_adapter(router: Router, client: TestClient) -> None:
    adapter = client.app.container.make(ResponseAdapter)
    adapter.register_adapter(
        CustomResponseType, lambda response: respond().text(response.content)
    )

    router.get("/", custom_response)

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.text == "Custom response"
