import pytest

from expanse.contracts.routing.router import Router
from expanse.http.exceptions import SuspiciousOperationError
from expanse.http.middleware.trust_hosts import TrustHosts
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.testing.client import TestClient


@pytest.fixture()
def request_() -> Request:
    return Request.create(
        "http://foo.example.com",
        scope={
            "headers": [
                (b"Host", b"foo.example.com"),
            ],
            "client": ("192.168.1.1", 12345),
            "server": ("foo.example.com", 80),
        },
    )


async def handler(request: Request) -> Response:
    return Response("Hello")


async def test_hosts_are_not_trusted_by_default(
    router: Router, client: TestClient, request_: Request
) -> None:
    trust_hosts = TrustHosts(client.app)

    await trust_hosts.handle(request_, handler)

    with pytest.raises(SuspiciousOperationError):
        request_.host  # noqa: B018


async def test_hosts_are_not_trusted_if_not_configured(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_hosts"] = ["foo.bar"]

    trust_hosts = TrustHosts(client.app)

    await trust_hosts.handle(request_, handler)

    with pytest.raises(SuspiciousOperationError):
        request_.host  # noqa: B018


async def test_hosts_are_trusted_if_configured(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_hosts"] = ["foo.example.com"]

    trust_hosts = TrustHosts(client.app)

    await trust_hosts.handle(request_, handler)

    assert request_.host == "foo.example.com"


async def test_hosts_are_trusted_if_subdomain(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_hosts"] = [".example.com"]

    trust_hosts = TrustHosts(client.app)

    await trust_hosts.handle(request_, handler)

    assert request_.host == "foo.example.com"


async def test_hosts_are_trusted_if_any_hosts(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_hosts"] = ["*"]

    trust_hosts = TrustHosts(client.app)

    await trust_hosts.handle(request_, handler)

    assert request_.host == "foo.example.com"


async def test_hosts_are_not_trusted_if_subdomain_but_only_parent_domain_configured(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["http.trusted_hosts"] = ["example.com"]

    trust_hosts = TrustHosts(client.app)

    await trust_hosts.handle(request_, handler)

    with pytest.raises(SuspiciousOperationError):
        request_.host  # noqa: B018


async def test_hosts_trusted_in_debug_mode_by_default_are_local(
    router: Router, client: TestClient, request_: Request
) -> None:
    client.app.config["app.debug"] = True

    trust_hosts = TrustHosts(client.app)

    await trust_hosts.handle(request_, handler)

    with pytest.raises(SuspiciousOperationError):
        request_.host  # noqa: B018

    request_ = Request.create(
        "http://localhost:8000",
        scope={
            "headers": [
                (b"Host", b"localhost:8000"),
            ],
            "client": ("192.168.1.1", 12345),
            "server": ("localhost", 8000),
        },
    )

    await trust_hosts.handle(request_, handler)

    assert request_.host == "localhost"
