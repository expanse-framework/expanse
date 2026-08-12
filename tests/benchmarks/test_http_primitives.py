"""Micro-benchmarks for the Rust-backed HTTP primitives.

These are the specific call sites the Rust port was meant to make cheap:
URL parsing, header bag mutation, cookie serialization, JSON body decode.
Run alongside the existing routing benchmarks so a regression on either
end shows up on Codspeed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.http.cookie import Cookie
from expanse.http.cookie import SameSite
from expanse.http.header_bag import HeaderBag
from expanse.http.response_header_bag import ResponseHeaderBag
from expanse.http.url import URL


if TYPE_CHECKING:
    from pytest_codspeed.plugin import BenchmarkFixture


_SAMPLE_URL = (
    "https://user:pass@api.example.com:8443"
    "/v1/users/12345/orders?status=open&limit=50&sort=-created_at#top"
)

_SAMPLE_HEADERS = {
    "Host": "api.example.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cookie": "session_id=abc123def456; theme=dark; consent=yes",
    "X-Forwarded-For": "10.0.0.1, 10.0.0.2",
    "X-Request-Id": "req_01HZY1234567890ABCDEFG",
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": "1234",
}


def test_bench_url_parse(benchmark: BenchmarkFixture) -> None:
    @benchmark
    def _() -> None:
        for _ in range(1000):
            URL(_SAMPLE_URL)


def test_bench_url_properties(benchmark: BenchmarkFixture) -> None:
    url = URL(_SAMPLE_URL)

    @benchmark
    def _() -> None:
        for _ in range(1000):
            _ = url.scheme
            _ = url.hostname
            _ = url.port
            _ = url.path
            _ = url.query


def test_bench_header_bag_construct(benchmark: BenchmarkFixture) -> None:
    @benchmark
    def _() -> None:
        for _ in range(1000):
            HeaderBag(_SAMPLE_HEADERS)


def test_bench_header_bag_encode(benchmark: BenchmarkFixture) -> None:
    bag = ResponseHeaderBag(_SAMPLE_HEADERS)

    @benchmark
    def _() -> None:
        for _ in range(1000):
            bag.encode()


def test_bench_cookie_serialize(benchmark: BenchmarkFixture) -> None:
    cookie = Cookie(
        name="session_id",
        value="abcdef1234567890abcdef1234567890",
        expires=2_000_000_000,
        domain="api.example.com",
        path="/",
        secure=True,
        http_only=True,
        same_site=SameSite.LAX,
    )

    @benchmark
    def _() -> None:
        for _ in range(1000):
            str(cookie)
