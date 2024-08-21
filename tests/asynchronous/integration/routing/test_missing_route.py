from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient


async def endpoint() -> str:
    return ""


async def test_router_should_respond_with_405_http_error_routes_with_alternative_methods(
    router: Router, client: TestClient
) -> None:
    router.get("/test", endpoint)

    response = client.post("/test")

    assert response.status_code == 405
    assert response.headers["Allow"] == "GET, HEAD"


async def test_router_should_respond_to_options_requests(
    router: Router, client: TestClient
) -> None:
    router.get("/test", endpoint)
    router.post("/test", endpoint)
    router.delete("/test", endpoint)
    router.patch("/test", endpoint)
    router.put("/test", endpoint)

    response = client.options("/test")

    assert response.status_code == 200
    assert response.headers["Allow"] == "GET, HEAD, POST, DELETE, PATCH, PUT"
