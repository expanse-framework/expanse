import logging

from pathlib import Path

from _pytest.logging import LogCaptureFixture

from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.core.http.middleware.middleware_stack import MiddlewareStack
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.testing.client import TestClient
from expanse.types.http.middleware import RequestHandler


logger = logging.getLogger(__name__)


class Middleware1:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        logger.info("Middleware 1")

        response = await next_call(request)

        response.headers["X-Middleware-1"] = "True"

        return response


class Middleware2:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        logger.info("Middleware 2")

        response = await next_call(request)

        response.headers["X-Middleware-2"] = "True"

        return response


class Middleware3:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        logger.info("Middleware 3")

        response = await next_call(request)

        response.headers["X-Middleware-3"] = "True"

        return response


class Middleware4:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        logger.info("Middleware 4")

        response = await next_call(request)

        response.headers["X-Middleware-4"] = "True"

        return response


async def configure_middleware(stack: MiddlewareStack) -> None:
    stack.use([Middleware1, Middleware2, Middleware3])

    stack.group("group1").append(Middleware4)


async def test_middleware_configuration(root: Path, caplog: LogCaptureFixture) -> None:
    app = Application.configure(root).with_middleware(configure_middleware).create()
    await app.bootstrap()

    router: Router = await app.container.get(Router)

    router.get("/", lambda: Response("Hello, World!"))

    client = TestClient(app, raise_server_exceptions=True)

    caplog.clear()
    caplog.set_level(logging.INFO)

    response = client.get("/")

    assert "X-Middleware-1" in response.headers
    assert "X-Middleware-2" in response.headers
    assert "X-Middleware-3" in response.headers

    assert caplog.messages[:3] == ["Middleware 1", "Middleware 2", "Middleware 3"]


async def test_middleware_group_configuration(
    root: Path, caplog: LogCaptureFixture
) -> None:
    app = Application.configure(root).with_middleware(configure_middleware).create()
    await app.bootstrap()

    router: Router = await app.container.get(Router)

    router.get("/", lambda: Response("Hello, World!"))
    with router.group("group1", prefix="/group1") as group1:
        group1.middleware("group1")
        group1.get("", lambda: Response("Group 1"))

    client = TestClient(app, raise_server_exceptions=True)

    response = client.get("/")

    assert "X-Middleware-1" in response.headers
    assert "X-Middleware-2" in response.headers
    assert "X-Middleware-3" in response.headers
    assert "X-Middleware-4" not in response.headers

    response = client.get("/group1")

    assert "X-Middleware-1" in response.headers
    assert "X-Middleware-2" in response.headers
    assert "X-Middleware-3" in response.headers
    assert "X-Middleware-4" in response.headers
