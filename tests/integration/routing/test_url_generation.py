from typing import Any

import pytest

from expanse.http.request import Request
from expanse.routing.exceptions import NotEnoughURLParameters
from expanse.routing.router import Router
from expanse.routing.url_generator import URLGenerator


@pytest.mark.parametrize(
    "path, parameters, expected",
    [
        ("/foo", {}, "https://example.com/foo"),
        ("/foo/{bar}", {"bar": 42}, "https://example.com/foo/42"),
        (
            "/foo/{bar}/{baz}",
            {"bar": "bim", "baz": 43},
            "https://example.com/foo/bim/43",
        ),
    ],
)
async def test_url_generation(
    router: Router, path: str, parameters: dict[str, Any], expected: str
) -> None:
    assert (
        URLGenerator(router, Request.create("https://example.com")).to(path, parameters)
        == expected
    )


@pytest.mark.parametrize(
    "path, parameters, expected",
    [
        (
            "/foo/{bar}",
            {},
            "Not enough parameters for URL /foo/{bar}: missing bar",
        ),
        (
            "/foo/{bar}/{baz}",
            {"baz": 43},
            "Not enough parameters for URL /foo/{bar}/{baz}: missing bar",
        ),
        (
            "/foo/{bar}/{baz}",
            {},
            "Not enough parameters for URL /foo/{bar}/{baz}: missing bar, baz",
        ),
    ],
)
async def test_url_generation_with_missing_parameters(
    router: Router, path: str, parameters: dict[str, Any], expected: str
) -> None:
    with pytest.raises(NotEnoughURLParameters) as e:
        URLGenerator(router, Request.create("https://example.com")).to(path, parameters)

    assert str(e.value) == expected


@pytest.mark.parametrize(
    "path, parameters, expected",
    [
        ("foo", {}, "/foo"),
        ("foo.bar", {"bar": 42}, "/foo/42"),
        ("foo.bar.baz", {"bar": "bim", "baz": "43"}, "/foo/bim/43"),
    ],
)
async def test_route_url_generation(
    router: Router, path: str, parameters: dict[str, Any], expected: str
) -> None:
    router.get("/foo", lambda: "foo", name="foo")
    router.get("/foo/{bar}", lambda: "foo", name="foo.bar")
    router.get("/foo/{bar}/{baz:int}", lambda: "foo", name="foo.bar.baz")

    assert (
        URLGenerator(router, Request.create("https://example.com")).to_route(
            path, parameters
        )
        == expected
    )
