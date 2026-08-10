from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.http.middleware.prefer_json_response import PreferJsonResponse
from expanse.http.request import Request
from expanse.http.response import Response


if TYPE_CHECKING:
    from expanse.types import Scope


def make_request(accept: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if accept is not None:
        headers.append((b"accept", accept.encode()))

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "client": ("127.0.0.1", 80),
        "scheme": "http",
        "server": ("localhost", 80),
        "headers": headers,
        "root_path": "",
        "http_version": "1.1",
        "path": "/",
        "query_string": b"",
        "raw_path": b"/",
        "method": "GET",
    }

    return Request(scope)


async def handler(request: Request) -> Response:
    return Response("Hello, World!")


async def test_prefers_json_when_there_is_no_accept_header() -> None:
    middleware = PreferJsonResponse()
    request = make_request(accept=None)

    await middleware.handle(request, handler)

    assert request.wants_json()


@pytest.mark.parametrize("accept", ["*", "*/*", "application/*"])
async def test_prefers_json_when_accept_header_is_a_wildcard(accept: str) -> None:
    middleware = PreferJsonResponse()
    request = make_request(accept=accept)

    await middleware.handle(request, handler)

    assert request.wants_json()


async def test_does_not_prefer_json_when_accept_header_is_specific() -> None:
    middleware = PreferJsonResponse()
    request = make_request(accept="text/html")

    await middleware.handle(request, handler)

    assert not request.wants_json()


async def test_does_not_prefer_json_when_accept_header_already_wants_json() -> None:
    middleware = PreferJsonResponse()
    request = make_request(accept="application/json")

    await middleware.handle(request, handler)

    assert request.wants_json()


async def test_calls_next_handler_and_returns_its_response() -> None:
    middleware = PreferJsonResponse()
    request = make_request(accept=None)

    response = await middleware.handle(request, handler)

    assert response.status_code == 200
