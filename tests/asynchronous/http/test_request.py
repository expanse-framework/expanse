from typing import Any

import pytest

from expanse.asynchronous.http.request import Request


@pytest.mark.parametrize(
    "content_type,expected",
    [("application/json", True), ("application/foo+json", True), ("text/html", False)],
)
def test_is_json(scope: dict[str, Any], content_type: str, expected: bool) -> None:
    scope["headers"].append((b"content-type", content_type.encode()))

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
    del scope["headers"][2]
    scope["headers"].append((b"accept", header.encode()))

    request = Request(scope)

    assert request.wants_json() is expected
