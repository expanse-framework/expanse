from expanse.http.request import Request
from expanse.routing.router import Router
from expanse.routing.url_generator import URLGenerator


def test_generator_can_generate_simple_urls(router: Router) -> None:
    url = URLGenerator(router, Request.create("http://example.com"))

    assert url.to("foo/bar") == "http://example.com/foo/bar"
    assert url.to("foo/bar", secure=True) == "https://example.com/foo/bar"
    assert (
        url.to("foo/bar?foo=bar", secure=True) == "https://example.com/foo/bar?foo=bar"
    )

    url = URLGenerator(router, Request.create("https://example.com"))
    assert url.to("foo/bar") == "https://example.com/foo/bar"


def test_generator_can_generate_route_urls(router: Router) -> None:
    url = URLGenerator(router, Request.create("http://example.com"))

    router.get("/", lambda: "", name="index")
    router.get("/foo/bar", lambda: "", name="foo")
    router.get("/foo/bar/{baz}/boom/{boom}", lambda: "", name="bar")

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
