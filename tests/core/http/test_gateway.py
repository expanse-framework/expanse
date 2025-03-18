from treat.mock import Mockery

from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.core.http.gateway import Gateway
from expanse.http.request import Request
from expanse.http.response import Response


async def test_gateway_prepares_response_before_sending_it_back(
    app: Application, router: Router, mockery: Mockery
) -> None:
    router.get("/", lambda: "Foo")

    request = Request.create("http://localhost:8000/")

    mockery.mock(Response).should_receive("prepare").with_(request).times(1)

    gateway = Gateway(app, router)

    response = await gateway.handle(request)

    assert response.status_code == 200


async def test_gateway_sets_secure_status_of_cookies_automatically(
    app: Application, router: Router, mockery: Mockery
) -> None:
    def foo(request: Request) -> Response:
        return (
            Response("Foo")
            .with_cookie("foo", "bar")
            .with_cookie("baz", "qux", secure=False)
        )

    router.get("/", foo)

    gateway = Gateway(app, router)

    request = Request.create("http://localhost:8000/")

    response = await gateway.handle(request)

    assert response.status_code == 200
    assert not response.cookies["foo"].is_secure()
    assert not response.cookies["baz"].is_secure()

    request = Request.create("https://localhost:8000/")

    response = await gateway.handle(request)

    assert response.status_code == 200
    assert response.cookies["foo"].is_secure()
    assert not response.cookies["baz"].is_secure()
