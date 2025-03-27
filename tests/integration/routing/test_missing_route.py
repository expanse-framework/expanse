from expanse.contracts.routing.router import Router
from expanse.testing.client import TestClient


async def endpoint() -> str:
    return "Foo"


async def endpoint2(foo: int) -> str:
    return "Foo"


async def test_router_should_respond_with_404_http_error_when_route_is_not_found(
    router: Router, client: TestClient
) -> None:
    response = client.get("/test")

    assert response.status_code == 404


async def test_router_should_respond_with_405_http_error_routes_with_alternative_methods(
    router: Router, client: TestClient
) -> None:
    router.get("/test", endpoint)

    response = client.post("/test")

    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"


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
    assert response.headers["Allow"] == "GET, POST, DELETE, PATCH, PUT"


def test_router_should_respond_to_head_requests(
    router: Router, client: TestClient
) -> None:
    router.get("/test", endpoint)
    router.get("/test/{foo}", endpoint)

    response = client.head("/test")

    assert response.status_code == 200
    assert response.text == ""

    response = client.head("/test/42")

    assert response.status_code == 200
    assert response.text == ""
