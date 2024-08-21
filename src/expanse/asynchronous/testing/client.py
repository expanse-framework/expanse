import contextlib
import io

from collections.abc import Callable
from collections.abc import Generator
from contextlib import AbstractContextManager
from types import GeneratorType
from typing import Any
from typing import Literal
from typing import TypedDict
from urllib.parse import unquote

import anyio
import anyio.abc
import anyio.from_thread
import httpx

from expanse.asynchronous.contracts.debug.exception_handler import ExceptionHandler
from expanse.asynchronous.core.application import Application
from expanse.asynchronous.types import Message
from expanse.common.testing.client import TestClient as BaseTestClient


_PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]


class _AsyncBackend(TypedDict):
    backend: str
    backend_options: dict[str, Any]


class _TestClientTransport(httpx.BaseTransport):
    def __init__(
        self,
        app: Application,
        portal_factory: _PortalFactoryType,
        root_path: str = "",
        raise_server_exceptions: bool = False,
    ) -> None:
        self.app = app
        self.portal_factory = portal_factory
        self.root_path = root_path
        self.raise_server_exceptions = raise_server_exceptions

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        scheme = request.url.scheme
        netloc = request.url.netloc.decode(encoding="ascii")
        path = request.url.path
        raw_path = request.url.raw_path
        query = request.url.query.decode(encoding="ascii")

        default_port = {"http": 80, "ws": 80, "https": 443, "wss": 443}[scheme]

        if ":" in netloc:
            host, port_string = netloc.split(":", 1)
            port = int(port_string)
        else:
            host = netloc
            port = default_port

        # Include the 'host' header.
        if "host" in request.headers:
            headers: list[tuple[bytes, bytes]] = []
        elif port == default_port:  # pragma: no cover
            headers = [(b"host", host.encode())]
        else:  # pragma: no cover
            headers = [(b"host", (f"{host}:{port}").encode())]

        # Include other request headers.
        headers += [
            (key.lower().encode(), value.encode())
            for key, value in request.headers.multi_items()
        ]

        scope: dict[str, Any]

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": request.method,
            "path": unquote(path),
            "raw_path": raw_path,
            "root_path": self.root_path,
            "scheme": scheme,
            "query_string": query.encode(),
            "headers": headers,
            "client": None,
            "server": [host, port],
            "extensions": {"http.response.debug": {}},
        }

        request_complete = False
        response_started = False
        response_complete: anyio.Event
        raw_kwargs: dict[str, Any] = {"stream": io.BytesIO()}
        template = None
        context = None

        async def receive() -> Message:
            nonlocal request_complete

            if request_complete:
                if not response_complete.is_set():
                    await response_complete.wait()
                return {"type": "http.disconnect"}

            body = request.read()
            if isinstance(body, str):
                body_bytes: bytes = body.encode("utf-8")  # pragma: no cover
            elif body is None:
                body_bytes = b""  # pragma: no cover
            elif isinstance(body, GeneratorType):
                try:  # pragma: no cover
                    chunk = body.send(None)
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    return {"type": "http.request", "body": chunk, "more_body": True}
                except StopIteration:  # pragma: no cover
                    request_complete = True
                    return {"type": "http.request", "body": b""}
            else:
                body_bytes = body

            request_complete = True
            return {"type": "http.request", "body": body_bytes}

        async def send(message: Message) -> None:
            nonlocal raw_kwargs, response_started, template, context

            if message["type"] == "http.response.start":
                assert (
                    not response_started
                ), 'Received multiple "http.response.start" messages.'
                raw_kwargs["status_code"] = message["status"]
                raw_kwargs["headers"] = [
                    (key.decode(), value.decode())
                    for key, value in message.get("headers", [])
                ]
                response_started = True
            elif message["type"] == "http.response.body":
                assert (
                    response_started
                ), 'Received "http.response.body" without "http.response.start".'
                assert (
                    not response_complete.is_set()
                ), 'Received "http.response.body" after response completed.'
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if request.method != "HEAD":
                    raw_kwargs["stream"].write(body)
                if not more_body:
                    raw_kwargs["stream"].seek(0)
                    response_complete.set()
            elif message["type"] == "http.response.debug":
                template = message["info"]["template"]
                context = message["info"]["context"]

        with self.portal_factory() as portal:
            response_complete = portal.call(anyio.Event)
            handler: ExceptionHandler = portal.call(
                self.app.container.make, ExceptionHandler
            )
            with handler.raise_unhandled_exceptions(self.raise_server_exceptions):
                portal.call(self.app, scope, receive, send)

        if self.raise_server_exceptions:
            assert response_started, "TestClient did not receive any response."
        elif not response_started:
            raw_kwargs = {
                "status_code": 500,
                "headers": [],
                "stream": io.BytesIO(),
            }

        raw_kwargs["stream"] = httpx.ByteStream(raw_kwargs["stream"].read())

        response = httpx.Response(**raw_kwargs, request=request)
        if template is not None:
            response.template = template  # type: ignore[attr-defined]
            response.context = context  # type: ignore[attr-defined]
        return response


class TestClient(BaseTestClient[Application]):
    def __init__(
        self,
        app: Application,
        base_url: str = "http://testserver",
        backend: Literal["asyncio", "trio"] = "asyncio",
        backend_options: dict[str, Any] | None = None,
        cookies: httpx._client.CookieTypes = None,
        headers: dict[str, str] | None = None,
        raise_server_exceptions: bool = False,
    ) -> None:
        self._transport: _TestClientTransport | None = None
        self.app = app
        self.async_backend = _AsyncBackend(
            backend=backend, backend_options=backend_options or {}
        )
        self.raise_server_exceptions = raise_server_exceptions
        if headers is None:
            headers = {}

        headers.setdefault("user-agent", "testclient")
        super().__init__(
            app=self.app,
            base_url=base_url,
            headers=headers,
            follow_redirects=True,
            cookies=cookies,
        )

    @property
    def transport(self) -> _TestClientTransport:
        if self._transport is None:
            self._transport = _TestClientTransport(
                self.app,
                portal_factory=self._portal_factory,
                raise_server_exceptions=self.raise_server_exceptions,
            )

        return self._transport

    @contextlib.contextmanager
    def _portal_factory(
        self,
    ) -> Generator[anyio.abc.BlockingPortal, None, None]:
        with anyio.from_thread.start_blocking_portal(**self.async_backend) as portal:
            yield portal

    @contextlib.contextmanager
    def handle_exceptions(
        self, handle_exceptions: bool = True
    ) -> Generator[None, None, None]:
        raise_server_exceptions = self.transport.raise_server_exceptions
        self.transport.raise_server_exceptions = not handle_exceptions

        yield

        self.transport.raise_server_exceptions = raise_server_exceptions
