from expanse.asynchronous.http.request import Request
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.routing.url_generator import URLGenerator


async def test_generator_can_generate_simple_urls(router: Router) -> None:
    url = URLGenerator(router, Request.create("http://example.com"))

    assert await url.to("foo/bar") == "http://example.com/foo/bar"
    assert await url.to("foo/bar", secure=True) == "https://example.com/foo/bar"
    assert (
        await url.to("foo/bar?foo=bar", secure=True)
        == "https://example.com/foo/bar?foo=bar"
    )

    url = URLGenerator(router, Request.create("https://example.com"))
    assert await url.to("foo/bar") == "https://example.com/foo/bar"


async def test_generator_can_generate_route_urls(router: Router) -> None:
    url = URLGenerator(router, Request.create("http://example.com"))

    router.get("/", lambda: "", name="index")
    router.get("/foo/bar", lambda: "", name="foo")
    router.get("/foo/bar/{baz}/boom/{boom}", lambda: "", name="bar")

    assert await url.to("foo/bar") == "http://example.com/foo/bar"
    assert await url.to("foo/bar", secure=True) == "https://example.com/foo/bar"
    assert (
        await url.to("foo/bar?foo=bar", secure=True)
        == "https://example.com/foo/bar?foo=bar"
    )

    assert await url.to_route("index") == "/"
    assert await url.to_route("index", {"foo": "bar"}) == "/?foo=bar"
    assert await url.to_route("index", absolute=True) == "http://example.com/"

    assert await url.to_route("foo") == "/foo/bar"
    assert await url.to_route("foo", {"baz": "boom"}) == "/foo/bar?baz=boom"
    assert await url.to_route("foo", absolute=True) == "http://example.com/foo/bar"

    assert (
        await url.to_route("bar", {"baz": "john", "boom": "doe"})
        == "/foo/bar/john/boom/doe"
    )
    assert (
        await url.to_route("bar", {"baz": "john", "boom": "doe", "another": "param"})
        == "/foo/bar/john/boom/doe?another=param"
    )
    assert (
        await url.to_route("bar", {"baz": "john", "boom": "doe"}, absolute=True)
        == "http://example.com/foo/bar/john/boom/doe"
    )
