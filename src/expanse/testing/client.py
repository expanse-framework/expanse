from __future__ import annotations

import contextlib
import sys

from io import BytesIO
from typing import TYPE_CHECKING
from typing import Any

import httpx

from httpx import Request
from httpx import Response
from httpx._transports.wsgi import WSGIByteStream

from expanse.common.testing.client import TestClient as BaseTestClient
from expanse.contracts.debug.exception_handler import ExceptionHandler
from expanse.core.application import Application
from expanse.exceptions.handler import ExceptionHandler as ConcreteExceptionHandler


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator

    from _typeshed import OptExcInfo


class WSGITransport(httpx.WSGITransport):
    def handle_request(self, request: Request) -> Response:
        request.read()
        wsgi_input = BytesIO(request.content)

        port = request.url.port or {"http": 80, "https": 443}[request.url.scheme]
        environ = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": request.url.scheme,
            "wsgi.input": wsgi_input,
            "wsgi.errors": self.wsgi_errors or sys.stderr,
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "REQUEST_METHOD": request.method,
            "SCRIPT_NAME": self.script_name,
            "PATH_INFO": request.url.path,
            "QUERY_STRING": request.url.query.decode("ascii"),
            "SERVER_NAME": request.url.host,
            "SERVER_PORT": str(port),
            "SERVER_PROTOCOL": "HTTP/1.1",
            "REMOTE_ADDR": self.remote_addr,
        }
        for header_key, header_value in request.headers.raw:
            key = header_key.decode("ascii").upper().replace("-", "_")
            if key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                key = "HTTP_" + key
            environ[key] = header_value.decode("ascii")

        seen_status = None
        seen_response_headers = None
        seen_exc_info = None

        def start_response(
            status: str,
            response_headers: list[tuple[str, str]],
            exc_info: OptExcInfo | None = None,
        ) -> Callable[[bytes], Any]:
            nonlocal seen_status, seen_response_headers, seen_exc_info
            seen_status = status
            seen_response_headers = response_headers
            seen_exc_info = exc_info
            return lambda _: None

        assert isinstance(self.app, Application)

        if not self.app.container.has(ExceptionHandler):
            self.app.container.singleton(ExceptionHandler, ConcreteExceptionHandler)

        handler: ExceptionHandler = self.app.container.make(ExceptionHandler)
        with handler.raise_unhandled_exceptions(self.raise_app_exceptions):
            result = self.app(environ, start_response)

        stream = WSGIByteStream(result)

        assert seen_status is not None
        assert seen_response_headers is not None
        if seen_exc_info and seen_exc_info[0] and self.raise_app_exceptions:
            raise seen_exc_info[1]

        status_code = int(seen_status.split()[0])
        headers = [
            (key.encode("ascii"), value.encode("ascii"))
            for key, value in seen_response_headers
        ]

        return Response(status_code, headers=headers, stream=stream)


class TestClient(BaseTestClient[Application]):
    def __init__(
        self,
        app: Application,
        base_url: str = "http://testserver",
        cookies: httpx._client.CookieTypes = None,
        headers: dict[str, str] | None = None,
        raise_server_exceptions: bool = False,
    ) -> None:
        if headers is None:
            headers = {}

        self._transport: WSGITransport | None = None
        self.raise_server_exceptions = raise_server_exceptions

        headers.setdefault("user-agent", "testclient")
        super().__init__(
            app=app,
            base_url=base_url,
            headers=headers,
            follow_redirects=True,
            cookies=cookies,
        )

    @property
    def transport(self) -> WSGITransport:
        if self._transport is None:
            self._transport = WSGITransport(
                app=self.app, raise_app_exceptions=self.raise_server_exceptions
            )

        return self._transport

    @contextlib.contextmanager
    def handle_exceptions(self, handle_exceptions: bool = True) -> Generator[None]:
        raise_app_exceptions = self.transport.raise_app_exceptions
        self.transport.raise_app_exceptions = not handle_exceptions

        yield

        self.transport.raise_app_exceptions = raise_app_exceptions
