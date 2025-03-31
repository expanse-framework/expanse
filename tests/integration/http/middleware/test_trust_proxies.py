from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

import pytest

from expanse.contracts.routing.router import Router
from expanse.http.exceptions import ConflictingForwardedHeadersError
from expanse.http.middleware.trust_proxies import TrustProxies
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.testing.client import TestClient


@pytest.fixture()
def request_() -> Request:
    return Request.create(
        "http://example.com:8080",
        scope={
            "headers": [
                (b"X-Forwarded-For", b"81.82.83.84"),
                (b"X-Forwarded-Host", b"some-other-host.com"),
                (b"X-Forwarded-Port", b"443"),
                (b"X-Forwarded-Prefix", b"/prefix"),
                (b"X-Forwarded-Proto", b"https"),
            ],
            "client": ("192.168.1.1", 12345),
        },
    )


def get_handler(
    ip: str | None = None,
    scheme: str | None = None,
    host: str | None = None,
    port: int | None = None,
    prefix: str | None = None,
    ips: list[str] | None = None,
) -> Callable[[Request], Awaitable[Response]]:
    async def handler(request: Request) -> Response:
        if ip:
            assert request.ip == ip
        if ips is not None:
            assert request.ips == ips
        if scheme:
            assert request.is_secure() == (scheme == "https")
        if host:
            assert request.host == host
        if port:
            assert request.port == port
        if prefix:
            assert request.url.path == prefix + request.url.path

        return Response("Hello")

    return handler


async def test_proxies_are_not_trusted_by_default(
    router: Router, client: TestClient, request_: Request
) -> None:
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(
        request_,
        get_handler(ip="192.168.1.1", scheme="http", host="example.com", port=8080),
    )

    assert response.status_code == 200


async def test_proxies_with_any_proxy_trusted(
    router: Router, client: TestClient, request_: Request
) -> None:
    trust_proxies = TrustProxies(client.app)
    client.app.config["http.trusted_proxies"] = ["*"]

    response = await trust_proxies.handle(
        request_,
        get_handler(
            ip="81.82.83.84", scheme="https", host="some-other-host.com", port=443
        ),
    )

    assert response.status_code == 200


async def test_proxies_with_specific_headers(
    router: Router, client: TestClient, request_: Request
) -> None:
    trust_proxies = TrustProxies(client.app)
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    client.app.config["http.trusted_headers"] = ["x-forwarded-for"]

    response = await trust_proxies.handle(
        request_,
        get_handler(ip="81.82.83.84", scheme="http", host="example.com", port=8080),
    )

    assert response.status_code == 200


async def test_trusted_proxies_with_port_header(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(request_, get_handler(port=443))

    assert response.status_code == 200


async def test_trusted_proxies_with_ip_header(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(request_, get_handler(ip="81.82.83.84"))

    assert response.status_code == 200


async def test_trusted_proxies_with_host_header(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(
        request_, get_handler(host="some-other-host.com")
    )

    assert response.status_code == 200


async def test_trusted_proxies_with_protocol_header(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(request_, get_handler(scheme="https"))

    assert response.status_code == 200


@pytest.mark.parametrize(
    "forwarded,expected",
    [
        (b'for="192.1.2.3"', {"ip": "192.1.2.3", "ips": ["192.1.2.3", "192.168.1.1"]}),
        (
            b"for=192.1.2.3, for=192.4.5.6",
            {"ip": "192.1.2.3", "ips": ["192.1.2.3", "192.4.5.6", "192.168.1.1"]},
        ),
        (
            b"for=192.1.2.3:443",
            {"ip": "192.1.2.3", "ips": ["192.1.2.3", "192.168.1.1"], "port": 8080},
        ),
        (
            b"for=192.1.2.3:443;host=example.com:443",
            {"ip": "192.1.2.3", "ips": ["192.1.2.3", "192.168.1.1"], "port": 443},
        ),
        (
            b'for="2001:db8:cafe::17", for=192.1.2.3; host=example.com',
            {
                "ip": "2001:db8:cafe::17",
                "ips": ["2001:db8:cafe::17", "192.1.2.3", "192.168.1.1"],
                "port": 80,
            },
        ),
        (
            b'for="[2001:db8:cafe::17]:4711", for=192.1.2.3; host=example.com',
            {
                "ip": "2001:db8:cafe::17",
                "ips": ["2001:db8:cafe::17", "192.1.2.3", "192.168.1.1"],
                "port": 80,
            },
        ),
        (
            b"for=192.1.2.3;proto=https;by=203.0.113.43",
            {
                "ip": "192.1.2.3",
                "ips": ["192.1.2.3", "192.168.1.1"],
                "scheme": "https",
                "port": 8080,
            },
        ),
        (
            b"for=192.1.2.3;proto=https;by=203.0.113.43;host=example.com",
            {
                "ip": "192.1.2.3",
                "ips": ["192.1.2.3", "192.168.1.1"],
                "scheme": "https",
                "port": 443,
            },
        ),
        (
            b"for=192.1.2.3;host=foo.bar",
            {
                "ip": "192.1.2.3",
                "ips": ["192.1.2.3", "192.168.1.1"],
                "host": "foo.bar",
            },
        ),
    ],
)
async def test_trusted_proxies_with_forwarded_header(
    router: Router, client: TestClient, forwarded: bytes, expected: dict[str, Any]
) -> None:
    request = Request.create(
        "http://example.com:8080",
        scope={
            "headers": [(b"Forwarded", forwarded)],
            "client": ("192.168.1.1", 12345),
        },
    )
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(request, get_handler(**expected))

    assert response.status_code == 200


@pytest.mark.parametrize(
    "url,forwarded,expected",
    [
        (
            "https://example.com/foo/bar?bar=baz",
            b"",
            "https://example.com/foo/bar?bar=baz",
        ),
        (
            "http://example.com/foo/bar?bar=baz",
            b"proto=https",
            "https://example.com/foo/bar?bar=baz",
        ),
        (
            "http://192.168.1.1:8080/foo/bar?bar=baz",
            b"for=192.1.2.3;proto=https",
            "https://192.168.1.1:8080/foo/bar?bar=baz",
        ),
        (
            "http://192.168.1.1:8080/foo/bar?bar=baz",
            b"for=192.1.2.3;proto=https;host=example.com",
            "https://example.com/foo/bar?bar=baz",
        ),
    ],
)
async def test_trusted_proxies_with_forwarded_header_to_url(
    router: Router,
    client: TestClient,
    url: str,
    forwarded: bytes,
    expected: dict[str, Any],
) -> None:
    request = Request.create(
        url,
        scope={
            "headers": [(b"Forwarded", forwarded)],
            "client": ("192.168.1.1", 12345),
        },
    )
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(request, get_handler())

    assert response.status_code == 200
    assert request.url == expected


@pytest.mark.parametrize(
    "url,headers,expected",
    [
        (
            "https://example.com/foo/bar?bar=baz",
            [],
            "https://example.com/foo/bar?bar=baz",
        ),
        (
            "http://example.com/foo/bar?bar=baz",
            [(b"X-Forwarded-Proto", b"https")],
            "https://example.com/foo/bar?bar=baz",
        ),
        (
            "http://192.168.1.1:8080/foo/bar?bar=baz",
            [(b"X-Forwarded-Proto", b"https"), (b"X-Forwarded-For", b"192.1.2.3")],
            "https://192.168.1.1:8080/foo/bar?bar=baz",
        ),
        (
            "http://192.168.1.1:8080/foo/bar?bar=baz",
            [
                (b"X-Forwarded-Proto", b"https"),
                (b"X-Forwarded-For", b"192.1.2.3"),
                (b"X-Forwarded-Host", b"example.com"),
            ],
            "https://example.com/foo/bar?bar=baz",
        ),
    ],
)
async def test_trusted_proxies_with_x_forwarded_headers_to_url(
    router: Router,
    client: TestClient,
    url: str,
    headers: list[tuple[bytes, bytes]],
    expected: dict[str, Any],
) -> None:
    request = Request.create(
        url,
        scope={
            "headers": headers,
            "client": ("192.168.1.1", 12345),
        },
    )
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(request, get_handler())

    assert response.status_code == 200
    assert request.url == expected


@pytest.mark.parametrize(
    "forwarded,headers",
    [
        (b"for=83.84.85.86", [(b"X-Forwarded-For", b"192.1.2.3")]),
        (b"for=83.84.85.86, for=192.4.5.6", [(b"X-Forwarded-For", b"192.1.2.3")]),
        (b"for=192.1.2.3, for=192.4.5.6", [(b"X-Forwarded-For", b"192.1.2.3")]),
        (
            b"for=192.1.2.3, for=192.4.5.6",
            [(b"X-Forwarded-For", b"192.4.5.6,192.1.2.3")],
        ),
    ],
)
async def test_trusted_proxies_with_conflicting_headers(
    router: Router,
    client: TestClient,
    forwarded: bytes,
    headers: list[tuple[bytes, bytes]],
) -> None:
    async def handler(request: Request) -> Response:
        return Response(request.ip)

    headers.append((b"Forwarded", forwarded))

    request = Request.create(
        "http://example.com",
        scope={
            "headers": headers,
            "client": ("192.168.1.1", 12345),
        },
    )
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    with pytest.raises(ConflictingForwardedHeadersError):
        await trust_proxies.handle(request, handler)


@pytest.mark.parametrize(
    "forwarded,headers,ips",
    [
        (b"for=192.1.2.3", [(b"X-Forwarded-For", b"192.1.2.3")], ["192.1.2.3"]),
        (
            b"for=83.84.85.86, for=192.1.2.3",
            [(b"X-Forwarded-For", b"83.84.85.86,192.1.2.3")],
            ["83.84.85.86", "192.1.2.3"],
        ),
        (
            b"for=83.84.85.86, for=192.1.2.3;proto=https;host=example.com",
            [(b"X-Forwarded-For", b"83.84.85.86,192.1.2.3")],
            ["83.84.85.86", "192.1.2.3"],
        ),
    ],
)
async def test_trusted_proxies_with_agreeing_headers(
    router: Router,
    client: TestClient,
    forwarded: bytes,
    headers: list[tuple[bytes, bytes]],
    ips: list[str],
) -> None:
    headers.append((b"Forwarded", forwarded))

    request = Request.create(
        "http://example.com",
        scope={
            "headers": headers,
            "client": ("192.168.1.1", 12345),
        },
    )
    client.app.config["http.trusted_proxies"] = ["192.168.1.1"]
    trust_proxies = TrustProxies(client.app)

    response = await trust_proxies.handle(
        request, get_handler(ips=[*ips, "192.168.1.1"])
    )

    assert response.status_code == 200
