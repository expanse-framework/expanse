from expanse.http.request import Request


def test_url() -> None:
    request = Request.create("http://example.com:1234/foo/bar?foo=bar&bar=baz")

    url = request.url

    assert url.scheme == "http"
    assert url.netloc == "example.com:1234"
    assert url.path == "/foo/bar"
    assert url.query == "foo=bar&bar=baz"
    assert url.fragment == ""
    assert url.username is None
    assert url.password is None
    assert url.hostname == "example.com"
    assert url.port == 1234
    assert url.full == "http://example.com:1234/foo/bar?foo=bar&bar=baz"
