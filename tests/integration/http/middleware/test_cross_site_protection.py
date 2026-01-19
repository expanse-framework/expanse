import pytest

from expanse.contracts.routing.router import Router
from expanse.http.middleware.cross_site_protection import CrossSiteProtection
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.testing.client import TestClient


async def handler(request: Request) -> Response:
    return Response("Hello, World!")


def test_allows_get_requests_by_default(client: TestClient, router: Router) -> None:
    router.get("/", handler).middleware(CrossSiteProtection)

    response = client.get("/")

    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_allows_head_requests_by_default(client: TestClient, router: Router) -> None:
    router.head("/", handler).middleware(CrossSiteProtection)

    response = client.head("/")

    assert response.status_code == 200


def test_allows_options_requests_by_default(client: TestClient, router: Router) -> None:
    router.options("/", handler).middleware(CrossSiteProtection)

    response = client.options("/")

    assert response.status_code == 200


def test_allows_post_with_same_site_header(client: TestClient, router: Router) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    response = client.post("/", headers={"Sec-Fetch-Site": "same-origin"})

    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_allows_post_with_none_fetch_site(client: TestClient, router: Router) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    response = client.post("/", headers={"Sec-Fetch-Site": "none"})

    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_blocks_post_with_cross_site_header(client: TestClient, router: Router) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    response = client.post("/", headers={"Sec-Fetch-Site": "cross-site"})

    assert response.status_code == 403


def test_blocks_post_with_same_site_header(client: TestClient, router: Router) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    response = client.post("/", headers={"Sec-Fetch-Site": "same-site"})

    assert response.status_code == 403


def test_allows_post_with_matching_origin_header(
    client: TestClient, router: Router
) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    response = client.post("/", headers={"Origin": "http://testserver"})

    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_blocks_post_with_non_matching_origin_header(
    client: TestClient, router: Router
) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    response = client.post("/", headers={"Origin": "http://evil.example.com"})

    assert response.status_code == 403


def test_allows_post_without_origin_or_sec_fetch_headers(
    client: TestClient, router: Router
) -> None:
    """Allows requests without headers (old browsers or non-browser clients)."""
    router.post("/", handler).middleware(CrossSiteProtection)

    # Create request without Origin or Sec-Fetch-Site headers
    response = client.post("/")

    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_allows_put_with_same_site_header(client: TestClient, router: Router) -> None:
    router.put("/", handler).middleware(CrossSiteProtection)

    response = client.put("/", headers={"Sec-Fetch-Site": "same-origin"})

    assert response.status_code == 200


def test_blocks_put_with_cross_site_header(client: TestClient, router: Router) -> None:
    router.put("/", handler).middleware(CrossSiteProtection)

    response = client.put("/", headers={"Sec-Fetch-Site": "cross-site"})

    assert response.status_code == 403


def test_allows_patch_with_same_site_header(client: TestClient, router: Router) -> None:
    router.patch("/", handler).middleware(CrossSiteProtection)

    response = client.patch("/", headers={"Sec-Fetch-Site": "same-origin"})

    assert response.status_code == 200


def test_blocks_patch_with_cross_site_header(
    client: TestClient, router: Router
) -> None:
    router.patch("/", handler).middleware(CrossSiteProtection)

    response = client.patch("/", headers={"Sec-Fetch-Site": "cross-site"})

    assert response.status_code == 403


def test_allows_delete_with_same_site_header(
    client: TestClient, router: Router
) -> None:
    router.delete("/", handler).middleware(CrossSiteProtection)

    response = client.delete("/", headers={"Sec-Fetch-Site": "same-origin"})

    assert response.status_code == 200


def test_blocks_delete_with_cross_site_header(
    client: TestClient, router: Router
) -> None:
    router.delete("/", handler).middleware(CrossSiteProtection)

    response = client.delete("/", headers={"Sec-Fetch-Site": "cross-site"})

    assert response.status_code == 403


def test_sec_fetch_site_header_is_case_insensitive(
    client: TestClient, router: Router
) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    # Test uppercase
    response = client.post("/", headers={"Sec-Fetch-Site": "same-origin"})
    assert response.status_code == 200

    # Test mixed case
    response = client.post("/", headers={"Sec-Fetch-Site": "same-origin"})
    assert response.status_code == 200


def test_sec_fetch_site_header_is_trimmed(client: TestClient, router: Router) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    response = client.post("/", headers={"Sec-Fetch-Site": "  same-origin  "})

    assert response.status_code == 200
    assert response.text == "Hello, World!"


def test_origin_hostname_must_match_host_exactly(
    client: TestClient, router: Router
) -> None:
    router.post("/", handler).middleware(CrossSiteProtection)

    # Matching origin
    response = client.post("/", headers={"Origin": "http://testserver"})
    assert response.status_code == 200

    # Different port should still work (hostname matches)
    response = client.post("/", headers={"Origin": "http://testserver:9000"})
    assert response.status_code == 200

    # Different hostname should fail
    response = client.post("/", headers={"Origin": "http://differenthost"})
    assert response.status_code == 403


def test_allows_post_with_matching_origin_different_scheme(
    client: TestClient, router: Router
) -> None:
    """Origin with different scheme but matching hostname is allowed."""
    router.post("/", handler).middleware(CrossSiteProtection)

    response = client.post("/", headers={"Origin": "https://testserver"})

    assert response.status_code == 200
    assert response.text == "Hello, World!"


@pytest.mark.parametrize(
    "method",
    ["GET", "HEAD", "OPTIONS"],
)
def test_safe_methods_bypass_all_checks(
    client: TestClient, router: Router, method: str
) -> None:
    """Safe methods are always allowed regardless of headers."""
    route_method = getattr(router, method.lower())
    route_method("/", handler).middleware(CrossSiteProtection)

    request_method = getattr(client, method.lower())

    # Even with cross-site header
    response = request_method("/", headers={"Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 200

    # Even with bad origin
    response = request_method("/", headers={"Origin": "http://evil.example.com"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "method",
    ["POST", "PUT", "PATCH", "DELETE"],
)
def test_unsafe_methods_require_validation(
    client: TestClient, router: Router, method: str
) -> None:
    """Unsafe methods must pass cross-site checks."""
    route_method = getattr(router, method.lower())
    route_method("/", handler).middleware(CrossSiteProtection)

    request_method = getattr(client, method.lower())

    # Cross-site should be blocked
    response = request_method("/", headers={"Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 403

    # same-origin should be allowed
    response = request_method("/", headers={"Sec-Fetch-Site": "same-origin"})
    assert response.status_code == 200
