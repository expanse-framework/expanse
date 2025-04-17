import pytest

from expanse.contracts.routing.router import Router
from expanse.http.request import Request
from expanse.routing.url_generator import URLGenerator


@pytest.fixture
def url(router: Router) -> URLGenerator:
    return URLGenerator(router, Request.create("http://example.com"))


def test_generator_can_generate_simple_urls(router: Router, url: URLGenerator) -> None:
    assert url.to("foo/bar") == "http://example.com/foo/bar"
    assert url.to("foo/bar", secure=True) == "https://example.com/foo/bar"
    assert (
        url.to("foo/bar?foo=bar", secure=True) == "https://example.com/foo/bar?foo=bar"
    )

    url = URLGenerator(router, Request.create("https://example.com"))
    assert url.to("foo/bar") == "https://example.com/foo/bar"


def test_generator_can_generate_route_urls(router: Router, url: URLGenerator) -> None:
    router.get("/", lambda: "", name="index")
    router.get("/foo/bar", lambda: "", name="foo")
    router.get("/foo/bar/{baz}/boom/{boom}", lambda: "", name="bar")
    router.get("/catch-all/{path:.*}", lambda: "", name="catch_all")

    assert url.to("foo/bar") == "http://example.com/foo/bar"
    assert url.to("foo/bar", secure=True) == "https://example.com/foo/bar"
    assert (
        url.to("foo/bar?foo=bar", secure=True) == "https://example.com/foo/bar?foo=bar"
    )

    assert url.to_route("index") == "/"
    assert url.to_route("index", {"foo": "bar"}) == "/?foo=bar"
    assert url.to_route("index", absolute=True) == "http://example.com/"

    assert url.to_route("foo") == "/foo/bar"
    assert url.to_route("foo", {"baz": "boom"}) == "/foo/bar?baz=boom"
    assert url.to_route("foo", absolute=True) == "http://example.com/foo/bar"

    assert (
        url.to_route("bar", {"baz": "john", "boom": "doe"}) == "/foo/bar/john/boom/doe"
    )
    assert (
        url.to_route("bar", {"baz": "john", "boom": "doe", "another": "param"})
        == "/foo/bar/john/boom/doe?another=param"
    )
    assert (
        url.to_route("bar", {"baz": "john", "boom": "doe"}, absolute=True)
        == "http://example.com/foo/bar/john/boom/doe"
    )

    assert (
        url.to_route("catch_all", {"path": "foo/bar/baz"}) == "/catch-all/foo/bar/baz"
    )
