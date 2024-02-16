from typing import Any

import pytest

from expanse.http.request import Request


@pytest.mark.parametrize(
    "content_type,expected",
    [("application/json", True), ("application/foo+json", True), ("text/html", False)],
)
def test_is_json(environ: dict[str, Any], content_type: str, expected: bool) -> None:
    environ["CONTENT_TYPE"] = content_type

    request = Request(environ)

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
def test_wants_json(environ: dict[str, Any], header: str, expected: bool) -> None:
    environ["HTTP_ACCEPT"] = header

    request = Request(environ)

    assert request.wants_json() is expected
