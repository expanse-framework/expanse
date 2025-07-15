import json

import pendulum
import pytest

from expanse.container.container import Container
from expanse.http.cookie import Cookie
from expanse.http.request import Request
from expanse.http.responses.response import Response


async def test_init() -> None:
    response = Response("Hello, World!", status_code=200, content_type="text/plain")
    assert await response.render() == b"Hello, World!"
    assert response.status_code == 200
    assert response.content_type == "text/plain"
    assert len(response.headers) == 0
    assert len(response.cookies) == 0


def test_setting_status_code() -> None:
    response = Response("Hello, World!")
    response.with_status(404)
    assert response.status_code == 404


def test_setting_header() -> None:
    response = Response("Hello, World!")
    response.with_header("X-Test-Header", "TestValue")
    assert response.headers["X-Test-Header"] == "TestValue"


def test_setting_headers() -> None:
    response = Response("Hello, World!")
    response.with_headers(
        {"X-Test-Header": "TestValue", "X-Another-Header": "AnotherValue"}
    )
    assert response.headers["X-Test-Header"] == "TestValue"
    assert response.headers["X-Another-Header"] == "AnotherValue"


def test_setting_cookie() -> None:
    response = Response("Hello, World!")
    cookie = Cookie(name="foo", value="abc123", expires=pendulum.tomorrow())
    response.with_cookie(cookie)
    response.with_cookie("bar", "xyz789", expires=pendulum.tomorrow())
    assert "foo" in response.cookies
    assert response.cookies["foo"].value == "abc123"
    assert "bar" in response.cookies
    assert response.cookies["bar"].value == "xyz789"


async def test_preparing_complete_response() -> None:
    response = Response(
        json.dumps({"foo": "bar"}), content_type="application/json", encoding="utf-8"
    )

    assert not response.headers.has("Content-Type")
    assert not response.headers.has("Content-Length")

    request = Request.create("http://example.com")

    await response.prepare(request, Container())

    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["Content-Length"] == "14"


@pytest.mark.parametrize(
    "status_code",
    [100, 101, 102, 103, 204, 205, 304],
)
async def test_preparing_informational_or_empty_response_drops_content(
    status_code: int,
) -> None:
    response = Response(
        "This is an informational response",
        status_code=status_code,
        content_type="text/plain",
    )

    assert not response.headers.has("Content-Type")
    assert not response.headers.has("Content-Length")

    request = Request.create("http://example.com")

    await response.prepare(request, Container())

    assert not response.headers.has("Content-Type")
    assert not response.headers.has("Content-Length")
    assert await response.render() is None


async def test_preparing_head_request_drops_content() -> None:
    response = Response("This is a response body", content_type="text/plain")

    assert not response.headers.has("Content-Type")
    assert not response.headers.has("Content-Length")

    request = Request.create("http://example.com", method="HEAD")

    await response.prepare(request, Container())

    assert await response.render() is None
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.headers["Content-Length"] == "23"


@pytest.mark.parametrize(
    "secure",
    [False, True],
)
async def test_cookies_are_prepared_with_secure_flag(secure: bool) -> None:
    response = Response("This is a response body")
    response.with_cookie(Cookie(name="session", value="abc123")).with_cookie(
        Cookie(name="another", value="xyz789").with_secure(True)
    )

    scheme = "https" if secure else "http"

    request = Request.create(f"{scheme}://example.com")

    await response.prepare(request, Container())

    assert "session" in response.cookies
    assert response.cookies["session"].is_secure() is secure
    assert response.cookies["another"].is_secure() is True


def test_encode_headers() -> None:
    response = Response("This is a response body")
    response.with_header("X-Test-Header", "TestValue")
    response.with_cookie(Cookie(name="session", value="abc123"))

    encoded_headers = response.encode_headers()

    assert encoded_headers == [
        (b"X-Test-Header", b"TestValue"),
        (b"set-cookie", b"session=abc123; path=/; samesite=lax"),
    ]


async def test_render() -> None:
    response = Response("This is a response body", content_type="text/plain")
    assert response.content_type == "text/plain"

    rendered_body = await response.render()
    assert rendered_body == b"This is a response body"

    assert response.is_rendered()

    response = Response(b"This is another response body", content_type="text/plain")

    rendered_body = await response.render()
    assert rendered_body == b"This is another response body"


def test_is_informational() -> None:
    response = Response("This is an informational response", status_code=100)
    assert response.is_informational()

    response = Response("This is not an informational response", status_code=200)
    assert not response.is_informational()


def test_is_empty() -> None:
    response = Response("", status_code=204)
    assert response.is_empty()

    response = Response("This is not an empty response", status_code=200)
    assert not response.is_empty()

    response = Response(None, status_code=200)
    assert not response.is_empty()  # Empty body but not an empty response


def test_is_client_error() -> None:
    response = Response("Client error", status_code=400)
    assert response.is_client_error()

    response = Response("Not a client error", status_code=500)
    assert not response.is_client_error()


def test_is_successful() -> None:
    response = Response("Success", status_code=200)
    assert response.is_successful()

    response = Response("Not successful", status_code=404)
    assert not response.is_successful()


def test_is_server_error() -> None:
    response = Response("Server error", status_code=500)
    assert response.is_server_error()

    response = Response("Not a server error", status_code=200)
    assert not response.is_server_error()


def test_is_redirection() -> None:
    response = Response("Redirect", status_code=301)
    assert response.is_redirection()

    response = Response("Not a redirect", status_code=200)
    assert not response.is_redirection()


def test_is_ok() -> None:
    response = Response("OK", status_code=200)
    assert response.is_ok()

    response = Response("Not OK", status_code=404)
    assert not response.is_ok()
