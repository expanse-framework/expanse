from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

import pytest

from expanse.contracts.routing.router import Router
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
            assert request.url.scheme == scheme
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
            {"ip": "192.1.2.3", "ips": ["192.1.2.3", "192.168.1.1"], "port": 443},
        ),
        (
            b'for="2001:db8:cafe::17", for=192.1.2.3',
            {
                "ip": "2001:db8:cafe::17",
                "ips": ["2001:db8:cafe::17", "192.1.2.3", "192.168.1.1"],
                "port": 8080,
            },
        ),
        (
            b'for="[2001:db8:cafe::17]:4711", for=192.1.2.3',
            {
                "ip": "2001:db8:cafe::17",
                "ips": ["2001:db8:cafe::17", "192.1.2.3", "192.168.1.1"],
                "port": 4711,
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
