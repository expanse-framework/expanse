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


async def test_string_adapter_adapts_response_based_on_request_acceptable_type(
    router: Router, client: TestClient
) -> None:
    router.get("/", text_response)

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.text == "foo"

    response = client.get("/", headers={"Accept": "application/json"})

    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == "foo"


async def test_register_new_adapter(router: Router, client: TestClient) -> None:
    async def adapt_response(response: CustomResponseType) -> Response:
        return await (await respond()).text(response.content)

    adapter = await client.app.container.make(ResponseAdapter)
    adapter.register_adapter(CustomResponseType, adapt_response)

    router.get("/", custom_response)

    response = client.get("/")

    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.text == "Custom response"
