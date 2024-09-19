from expanse.asynchronous.http.helpers import respond
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.http.response_adapter import ResponseAdapter
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient


class CustomResponseType:
    def __init__(self, content: str) -> None:
        self.content = content


async def text_response() -> str:
    return "foo"


async def custom_response() -> CustomResponseType:
    return CustomResponseType("Custom response")


async def configure_adapter(adapter: ResponseAdapter) -> None:
    async def adapt_response(response: CustomResponseType) -> Response:
        return await (await respond()).text(response.content)

    adapter.register_adapter(CustomResponseType, adapt_response)


async def test_string_adapter_adapts_response(
    router: Router, client: TestClient
) -> None:
    router.get("/", text_response)

    response = client.get("/")

    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == "foo"


async def test_register_new_adapter(router: Router, client: TestClient) -> None:
    await client.app.container.on_resolved(ResponseAdapter, configure_adapter)

    router.get("/", custom_response)

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.text == "Custom response"
