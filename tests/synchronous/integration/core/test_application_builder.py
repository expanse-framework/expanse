import logging

from pathlib import Path

from _pytest.logging import LogCaptureFixture

from expanse.core.application import Application
from expanse.core.http.middleware.middleware_stack import MiddlewareStack
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from expanse.types.http.middleware import RequestHandler


logger = logging.getLogger(__name__)


class Middleware1:
    def handle(self, request: Request, next_call: RequestHandler) -> Response:
        logger.info("Middleware 1")

        response = next_call(request)

        response.headers["X-Middleware-1"] = "True"

        return response


class Middleware2:
    def handle(self, request: Request, next_call: RequestHandler) -> Response:
        logger.info("Middleware 2")

        response = next_call(request)

        response.headers["X-Middleware-2"] = "True"

        return response


class Middleware3:
    def handle(self, request: Request, next_call: RequestHandler) -> Response:
        logger.info("Middleware 3")

        response = next_call(request)

        response.headers["X-Middleware-3"] = "True"

        return response


def configure_middleware(stack: MiddlewareStack) -> None:
    stack.append(Middleware1, Middleware2, Middleware3)


def test_middleware_configuration(root: Path, caplog: LogCaptureFixture) -> None:
    app = Application.configure(root).with_middleware(configure_middleware).create()
    app.bootstrap()

    router: Router = app.container.make(Router)

    router.get("/", lambda: Response("Hello, World!"))

    client = TestClient(app, raise_server_exceptions=True)

    caplog.clear()
    caplog.set_level(logging.INFO)

    response = client.get("/")

    assert "X-Middleware-1" in response.headers
    assert "X-Middleware-2" in response.headers
    assert "X-Middleware-3" in response.headers

    assert caplog.messages[:3] == ["Middleware 1", "Middleware 2", "Middleware 3"]
