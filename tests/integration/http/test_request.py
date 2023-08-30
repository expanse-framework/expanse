from typing import Any

import pytest

from starlette.datastructures import MutableHeaders

from expanse.http.request import Request


@pytest.mark.parametrize(
    "content_type,expected",
    [("application/json", True), ("application/foo+json", True), ("text/html", False)],
)
def test_is_json(scope: dict[str, Any], content_type: str, expected: bool) -> None:
    headers = MutableHeaders(scope=scope)
    headers["Content-Type"] = content_type
    scope["headers"] = headers.raw

    request = Request(scope)

    assert request.is_json() is expected


@pytest.mark.parametrize(
    "header,expected",
    [
        ("application/json", True),
        ("application/json; charset=utf-8", True),
        ("application/foo+json", True),
        ("application/json, text/html", True),
        ("text/html", False),
        ("application/json;q=0.1, text/html;q=0.8", False),
        ("application/json;q=0.8, text/html;q=0.8", True),
    ],
)
def test_wants_json(scope: dict[str, Any], header: str, expected: bool) -> None:
    headers = MutableHeaders(scope=scope)
    headers["Accept"] = header
    scope["headers"] = headers.raw

    request = Request(scope)

    assert request.wants_json() is expected
