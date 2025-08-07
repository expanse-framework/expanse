from __future__ import annotations

import asyncio
import json

from datetime import timezone
from email.utils import formatdate
from typing import TYPE_CHECKING
from urllib.parse import quote

import pytest

from expanse.http.exceptions import ClientDisconnectedError
from expanse.http.exceptions import ConflictingForwardedHeadersError
from expanse.http.exceptions import MalformedJSONError
from expanse.http.exceptions import SuspiciousOperationError
from expanse.http.exceptions import UnsupportedContentTypeError
from expanse.http.request import Request
from expanse.http.trusted_header import TrustedHeader
from expanse.routing.route import Route
from expanse.session.session import HTTPSession
from expanse.session.synchronous.stores.dict import DictStore


if TYPE_CHECKING:
    from expanse.types import PartialScope


class TestRequestBasicProperties:
    def test_url(self) -> None:
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

    def test_method_get(self) -> None:
        request = Request.create("http://example.com", method="GET")
        assert request.method == "GET"

    def test_method_post(self) -> None:
        request = Request.create("http://example.com", method="POST")
        assert request.method == "POST"

    def test_method_lowercase_normalized(self) -> None:
        request = Request.create("http://example.com", method="post")
        assert request.method == "POST"

    def test_path(self) -> None:
        request = Request.create("http://example.com/foo/bar")
        assert request.path == "/foo/bar"

    def test_path_root(self) -> None:
        request = Request.create("http://example.com")
        assert request.path == "/"

    def test_scheme_http(self) -> None:
        request = Request.create("http://example.com")
        assert request.scheme == "http"

    def test_scheme_https(self) -> None:
        request = Request.create("https://example.com")
        assert request.scheme == "https"

    def test_is_secure_http(self) -> None:
        request = Request.create("http://example.com")
        assert not request.is_secure()

    def test_is_secure_https(self) -> None:
        request = Request.create("https://example.com")
        assert request.is_secure()


class TestRequestHeaders:
    def test_headers_basic(self) -> None:
        scope: PartialScope = {
            "headers": [
                (b"content-type", b"application/json"),
                (b"authorization", b"Bearer token"),
            ]
        }
        request = Request.create("http://example.com", scope=scope)

        assert request.headers["content-type"] == "application/json"
        assert request.headers["authorization"] == "Bearer token"

    def test_headers_case_insensitive(self) -> None:
        scope: PartialScope = {
            "headers": [
                (b"Content-Type", b"application/json"),
                (b"AUTHORIZATION", b"Bearer token"),
            ]
        }
        request = Request.create("http://example.com", scope=scope)

        assert request.headers["content-type"] == "application/json"
        assert request.headers["Content-Type"] == "application/json"
        assert request.headers["CONTENT-TYPE"] == "application/json"

    def test_host_from_header(self) -> None:
        scope: PartialScope = {"headers": [(b"host", b"example.com:8080")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.host == "example.com"

    def test_host_trusted_default(self) -> None:
        request = Request.create("http://example.com")
        # Default trusted hosts is ["*"] so any host should be trusted
        assert request.host == "example.com"

    def test_host_untrusted_raises_error(self) -> None:
        scope: PartialScope = {"headers": [(b"host", b"malicious.com")]}
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_hosts(["example.com"])

        with pytest.raises(SuspiciousOperationError):
            _ = request.host

    def test_host_wildcard_subdomain(self) -> None:
        scope: PartialScope = {"headers": [(b"host", b"api.example.com")]}
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_hosts([".example.com"])

        assert request.host == "api.example.com"

    def test_http_host_default_port_http(self) -> None:
        request = Request.create("http://example.com")
        assert request.http_host == "example.com"

    def test_http_host_default_port_https(self) -> None:
        request = Request.create("https://example.com")
        assert request.http_host == "example.com"

    def test_http_host_custom_port(self) -> None:
        request = Request.create("http://example.com:8080")
        assert request.http_host == "example.com:8080"

    def test_port_from_url(self) -> None:
        request = Request.create("http://example.com:8080")
        assert request.port == 8080

    def test_port_default_http(self) -> None:
        request = Request.create("http://example.com")
        assert request.port == 80

    def test_port_default_https(self) -> None:
        request = Request.create("https://example.com")
        assert request.port == 443


class TestRequestContentType:
    def test_content_type_json(self) -> None:
        scope: PartialScope = {"headers": [(b"content-type", b"application/json")]}
        request = Request.create("http://example.com", scope=scope)

        content_type = request.content_type
        assert content_type.type == "application/json"
        assert content_type.options.get("charset", "utf-8") == "utf-8"

    def test_content_type_with_charset(self) -> None:
        scope: PartialScope = {
            "headers": [(b"content-type", b"application/json; charset=utf-16")]
        }
        request = Request.create("http://example.com", scope=scope)

        content_type = request.content_type
        assert content_type.type == "application/json"
        assert content_type.options.get("charset") == "utf-16"

    def test_content_type_empty(self) -> None:
        request = Request.create("http://example.com")
        content_type = request.content_type
        assert content_type.type == ""

    def test_content_length_valid(self) -> None:
        scope: PartialScope = {"headers": [(b"content-length", b"123")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.content_length == 123

    def test_content_length_zero(self) -> None:
        scope: PartialScope = {"headers": [(b"content-length", b"0")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.content_length == 0

    def test_content_length_negative_becomes_zero(self) -> None:
        scope: PartialScope = {"headers": [(b"content-length", b"-5")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.content_length == 0

    def test_content_length_invalid(self) -> None:
        scope: PartialScope = {"headers": [(b"content-length", b"invalid")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.content_length is None

    def test_content_length_chunked(self) -> None:
        scope: PartialScope = {
            "headers": [(b"content-length", b"123"), (b"transfer-encoding", b"chunked")]
        }
        request = Request.create("http://example.com", scope=scope)
        assert request.content_length is None

    def test_content_length_missing(self) -> None:
        request = Request.create("http://example.com")
        assert request.content_length is None


class TestRequestContentTypeDetection:
    def test_is_json_application_json(self) -> None:
        scope: PartialScope = {"headers": [(b"content-type", b"application/json")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.is_json()

    def test_is_json_with_json_suffix(self) -> None:
        scope: PartialScope = {
            "headers": [(b"content-type", b"application/vnd.api+json")]
        }
        request = Request.create("http://example.com", scope=scope)
        assert request.is_json()

    def test_is_json_false(self) -> None:
        scope: PartialScope = {"headers": [(b"content-type", b"text/html")]}
        request = Request.create("http://example.com", scope=scope)
        assert not request.is_json()

    def test_wants_json_true(self) -> None:
        # Override default headers that include */* by using empty headers first
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [(b"accept", b"application/json")]
        # Clear cached property to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        assert request.wants_json()

    def test_wants_json_with_json_suffix(self) -> None:
        # Override default headers that include */* by using empty headers first
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [(b"accept", b"application/vnd.api+json")]
        # Clear cached property to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        assert request.wants_json()

    def test_wants_json_false(self) -> None:
        scope: PartialScope = {"headers": [(b"accept", b"text/html")]}
        request = Request.create("http://example.com", scope=scope)
        assert not request.wants_json()

    def test_accepts_any_content_type_true_wildcard(self) -> None:
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [(b"accept", b"*/*")]
        # Clear cached property to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        assert request.accepts_any_content_type()

    def test_accepts_any_content_type_true_star(self) -> None:
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [(b"accept", b"*")]
        # Clear cached property to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        assert request.accepts_any_content_type()

    def test_accepts_any_content_type_true_empty(self) -> None:
        # When Accept header is empty, it creates an empty string item which doesn't match "*/*" or "*"
        # So this should actually be False
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": [(b"Accept", b"")]}
        )
        assert not request.accepts_any_content_type()

    def test_accepts_any_content_type_false(self) -> None:
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [(b"accept", b"application/json")]
        # Clear cached property to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        assert not request.accepts_any_content_type()

    def test_expects_json_ajax_any_content(self) -> None:
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [
            (b"x-requested-with", b"XMLHttpRequest"),
            (b"accept", b"*/*"),
        ]
        # Clear cached properties to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        assert request.expects_json()

    def test_expects_json_wants_json(self) -> None:
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [(b"accept", b"application/json")]
        # Clear cached properties to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        assert request.expects_json()


class TestRequestAjaxDetection:
    def test_is_xml_http_request_true(self) -> None:
        scope: PartialScope = {"headers": [(b"x-requested-with", b"XMLHttpRequest")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.is_xml_http_request()

    def test_is_xml_http_request_false(self) -> None:
        request = Request.create("http://example.com")
        assert not request.is_xml_http_request()

    def test_is_ajax_alias(self) -> None:
        scope: PartialScope = {"headers": [(b"x-requested-with", b"XMLHttpRequest")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.is_ajax()

    def test_is_pjax_true(self) -> None:
        scope: PartialScope = {"headers": [(b"x-pjax", b"true")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.is_pjax()

    def test_is_pjax_false(self) -> None:
        request = Request.create("http://example.com")
        assert not request.is_pjax()


class TestRequestCookies:
    def test_cookies_simple(self) -> None:
        scope: PartialScope = {"headers": [(b"cookie", b"session=abc123; theme=dark")]}
        request = Request.create("http://example.com", scope=scope)

        cookies = request.cookies
        assert cookies["session"] == "abc123"
        assert cookies["theme"] == "dark"

    def test_cookies_quoted(self) -> None:
        scope: PartialScope = {
            "headers": [(b"cookie", b'session="abc123"; theme="dark"')]
        }
        request = Request.create("http://example.com", scope=scope)

        cookies = request.cookies
        assert cookies["session"] == "abc123"
        assert cookies["theme"] == "dark"

    def test_cookies_empty_value(self) -> None:
        scope: PartialScope = {"headers": [(b"cookie", b"empty=; valid=value")]}
        request = Request.create("http://example.com", scope=scope)

        cookies = request.cookies
        assert cookies["empty"] == ""
        assert cookies["valid"] == "value"

    def test_cookies_no_equals(self) -> None:
        scope: PartialScope = {"headers": [(b"cookie", b"standalone")]}
        request = Request.create("http://example.com", scope=scope)

        cookies = request.cookies
        assert cookies[""] == "standalone"

    def test_cookies_empty(self) -> None:
        request = Request.create("http://example.com")
        assert request.cookies == {}


class TestRequestDate:
    def test_date_valid(self) -> None:
        date_str = formatdate(timeval=None, localtime=False, usegmt=True)
        scope: PartialScope = {"headers": [(b"date", date_str.encode())]}
        request = Request.create("http://example.com", scope=scope)

        date = request.date
        assert date is not None
        assert date.tzinfo == timezone.utc

    def test_date_invalid(self) -> None:
        scope: PartialScope = {"headers": [(b"date", b"invalid-date")]}
        request = Request.create("http://example.com", scope=scope)
        assert request.date is None

    def test_date_missing(self) -> None:
        request = Request.create("http://example.com")
        assert request.date is None

    def test_date_timezone_aware(self) -> None:
        # Test date without timezone gets UTC assigned
        scope: PartialScope = {"headers": [(b"date", b"Wed, 21 Oct 2015 07:28:00")]}
        request = Request.create("http://example.com", scope=scope)

        date = request.date
        assert date is not None
        assert date.tzinfo == timezone.utc


class TestRequestReferrer:
    def test_referrer_valid(self) -> None:
        scope: PartialScope = {"headers": [(b"referer", b"https://google.com/search")]}
        request = Request.create("http://example.com", scope=scope)

        referrer = request.referrer
        assert referrer is not None
        assert referrer.full == "https://google.com/search"

    def test_referrer_missing(self) -> None:
        request = Request.create("http://example.com")
        assert request.referrer is None


class TestRequestClient:
    def test_client_default(self) -> None:
        request = Request.create("http://example.com")
        client = request.client
        assert client.host == "127.0.0.1"
        assert client.port == 80

    def test_client_custom(self) -> None:
        scope: PartialScope = {"client": ("192.168.1.1", 12345)}
        request = Request.create("http://example.com", scope=scope)

        client = request.client
        assert client.host == "192.168.1.1"
        assert client.port == 12345

    def test_client_none(self) -> None:
        scope: PartialScope = {"client": None}
        request = Request.create("http://example.com", scope=scope)

        client = request.client
        assert client.host is None
        assert client.port is None


class TestRequestIPs:
    def test_ip_single(self) -> None:
        scope: PartialScope = {"client": ("192.168.1.1", 80)}
        request = Request.create("http://example.com", scope=scope)
        assert request.ip == "192.168.1.1"

    def test_ip_none_when_no_client(self) -> None:
        scope: PartialScope = {"client": None}
        request = Request.create("http://example.com", scope=scope)
        assert request.ip is None

    def test_ips_single(self) -> None:
        scope: PartialScope = {"client": ("192.168.1.1", 80)}
        request = Request.create("http://example.com", scope=scope)
        assert request.ips == ["192.168.1.1"]

    def test_ips_with_forwarded_for(self) -> None:
        scope: PartialScope = {
            "client": ("192.168.1.1", 80),
            "headers": [(b"x-forwarded-for", b"10.0.0.1, 10.0.0.2")],
        }
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_proxies(["192.168.1.0/24"])
        request.set_trusted_headers([TrustedHeader.X_FORWARDED_FOR])

        assert request.ips == ["10.0.0.1", "10.0.0.2", "192.168.1.1"]


class TestRequestQueryParams:
    def test_query_params_simple(self) -> None:
        request = Request.create("http://example.com?foo=bar&baz=qux")
        params = request.query_params
        assert params["foo"] == "bar"
        assert params["baz"] == "qux"

    def test_query_params_multiple_values(self) -> None:
        request = Request.create("http://example.com?tag=python&tag=web")
        params = request.query_params
        assert params.getlist("tag") == ["python", "web"]

    def test_query_params_empty(self) -> None:
        request = Request.create("http://example.com")
        params = request.query_params
        assert len(params) == 0

    def test_query_params_encoded(self) -> None:
        encoded_value = quote("hello world")
        request = Request.create(f"http://example.com?msg={encoded_value}")
        params = request.query_params
        assert params["msg"] == "hello world"


class TestRequestTrustedProxies:
    def test_is_from_trusted_proxy_false_no_proxies(self) -> None:
        request = Request.create("http://example.com")
        assert not request.is_from_trusted_proxy()

    def test_is_from_trusted_proxy_false_no_client(self) -> None:
        scope: PartialScope = {"client": None}
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_proxies(["192.168.1.0/24"])
        assert not request.is_from_trusted_proxy()

    def test_is_from_trusted_proxy_true(self) -> None:
        scope: PartialScope = {"client": ("192.168.1.100", 80)}
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_proxies(["192.168.1.0/24"])
        assert request.is_from_trusted_proxy()

    def test_is_from_trusted_proxy_false_different_network(self) -> None:
        scope: PartialScope = {"client": ("10.0.0.1", 80)}
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_proxies(["192.168.1.0/24"])
        assert not request.is_from_trusted_proxy()

    def test_is_header_trusted_true(self) -> None:
        request = Request.create("http://example.com")
        request.set_trusted_headers([TrustedHeader.X_FORWARDED_FOR])
        assert request.is_header_trusted(TrustedHeader.X_FORWARDED_FOR)

    def test_is_header_trusted_false(self) -> None:
        request = Request.create("http://example.com")
        assert not request.is_header_trusted(TrustedHeader.X_FORWARDED_FOR)

    def test_trusted_host_configuration(self) -> None:
        request = Request.create("http://example.com")
        request.set_trusted_hosts(["example.com", "api.example.com"])
        # Should not raise an exception
        assert request.host == "example.com"

    def test_port_from_forwarded_port(self) -> None:
        scope: PartialScope = {
            "client": ("192.168.1.1", 80),
            "headers": [(b"x-forwarded-port", b"8080")],
        }
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_proxies(["192.168.1.0/24"])
        request.set_trusted_headers([TrustedHeader.X_FORWARDED_PORT])

        assert request.port == 8080

    def test_scheme_from_forwarded_proto(self) -> None:
        scope: PartialScope = {
            "client": ("192.168.1.1", 80),
            "headers": [(b"x-forwarded-proto", b"https")],
        }
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_proxies(["192.168.1.0/24"])
        request.set_trusted_headers([TrustedHeader.X_FORWARDED_PROTO])

        assert request.scheme == "https"
        assert request.is_secure()


class TestRequestAcceptableContentTypes:
    def test_acceptable_content_types_single(self) -> None:
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [(b"accept", b"application/json")]
        # Clear cached properties to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        assert "application/json" in request.acceptable_content_types

    def test_acceptable_content_types_multiple(self) -> None:
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": []}
        )
        request._scope["headers"] = [
            (b"accept", b"text/html,application/json;q=0.9,*/*;q=0.8")
        ]
        # Clear cached properties to force recalculation
        if "headers" in request.__dict__:
            del request.__dict__["headers"]
        if "acceptable_content_types" in request.__dict__:
            del request.__dict__["acceptable_content_types"]
        types = request.acceptable_content_types
        assert "text/html" in types
        assert "application/json" in types
        assert "*/*" in types

    def test_acceptable_content_types_empty(self) -> None:
        request = Request.create(
            "http://example.com", method="GET", scope={"headers": [(b"Accept", b"")]}
        )
        # Empty Accept header still creates one empty string item
        assert request.acceptable_content_types == [""]


class TestRequestRouteAndSession:
    def test_route_initially_none(self) -> None:
        request = Request.create("http://example.com")
        assert request.route is None

    def test_session_initially_none(self) -> None:
        request = Request.create("http://example.com")
        assert request.session is None

    def test_set_route(self) -> None:
        request = Request.create("http://example.com")
        route = Route("GET", "/foo", lambda: 42, name="test_route")
        result = request.set_route(route)
        assert result is request
        assert request.route is route

    def test_set_session(self) -> None:
        request = Request.create("http://example.com")
        session = HTTPSession("foo", DictStore(lifetime=60))
        result = request.set_session(session)
        assert result is request
        assert request.session is session


class TestRequestAsyncMethods:
    async def test_body_empty(self) -> None:
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = Request.create("http://example.com")
        request._receive = receive

        body = await request.body
        assert body == b""

    async def test_body_with_content(self) -> None:
        content = b"Hello, World!"

        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}

        request = Request.create("http://example.com")
        request._receive = receive

        body = await request.body
        assert body == content

    async def test_body_chunked(self) -> None:
        chunks = [b"Hello, ", b"World!"]
        chunk_index = 0

        async def receive():
            nonlocal chunk_index
            if chunk_index < len(chunks):
                body = chunks[chunk_index]
                more_body = chunk_index < len(chunks) - 1
                chunk_index += 1
                return {"type": "http.request", "body": body, "more_body": more_body}
            return {"type": "http.request", "body": b"", "more_body": False}

        request = Request.create("http://example.com")
        request._receive = receive

        body = await request.body
        assert body == b"Hello, World!"

    async def test_json_valid(self) -> None:
        data = {"message": "hello", "count": 42}
        content = json.dumps(data).encode()

        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}

        scope: PartialScope = {"headers": [(b"content-type", b"application/json")]}
        request = Request.create("http://example.com", scope=scope)
        request._receive = receive

        result = await request.json
        assert result == data

    async def test_json_invalid_content_type(self) -> None:
        scope: PartialScope = {"headers": [(b"content-type", b"text/plain")]}
        request = Request.create("http://example.com", scope=scope)

        with pytest.raises(UnsupportedContentTypeError):
            await request.json

    async def test_json_malformed(self) -> None:
        content = b"invalid json"

        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}

        request = Request.create(
            "http://example.com",
            method="GET",
            scope={"headers": [(b"content-type", b"application/json")]},
        )
        request._receive = receive
        with pytest.raises(MalformedJSONError):
            await request.json

    async def test_form_urlencoded(self) -> None:
        content = b"name=John&age=30&city=New+York"

        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}

        scope: PartialScope = {
            "headers": [(b"content-type", b"application/x-www-form-urlencoded")]
        }
        request = Request.create("http://example.com", scope=scope)
        request._receive = receive

        form = await request.form
        assert form["name"] == "John"
        assert form["age"] == "30"
        assert form["city"] == "New York"

    async def test_form_invalid_content_type(self) -> None:
        scope: PartialScope = {"headers": [(b"content-type", b"text/plain")]}
        request = Request.create("http://example.com", scope=scope)

        with pytest.raises(UnsupportedContentTypeError):
            await request.form

    async def test_input_from_json(self) -> None:
        data = {"name": "John", "age": 30}
        content = json.dumps(data).encode()

        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}

        scope: PartialScope = {"headers": [(b"content-type", b"application/json")]}
        request = Request.create("http://example.com", method="POST", scope=scope)
        request._receive = receive

        assert await request.input("name") == "John"
        assert await request.input("age") == 30
        assert await request.input("missing", "default") == "default"

    async def test_input_from_form(self) -> None:
        content = b"name=John&age=30"

        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}

        scope: PartialScope = {
            "headers": [(b"content-type", b"application/x-www-form-urlencoded")]
        }
        request = Request.create("http://example.com", method="POST", scope=scope)
        request._receive = receive

        assert await request.input("name") == "John"
        assert await request.input("age") == "30"

    async def test_input_from_query_params_get(self) -> None:
        request = Request.create("http://example.com?name=John&age=30", method="GET")

        assert await request.input("name") == "John"
        assert await request.input("age") == "30"

    async def test_input_query_params_override(self) -> None:
        content = b"name=FormJohn"

        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}

        scope: PartialScope = {
            "headers": [(b"content-type", b"application/x-www-form-urlencoded")]
        }
        request = Request.create(
            "http://example.com?name=QueryJohn", method="POST", scope=scope
        )
        request._receive = receive

        # Query params should override form data
        assert await request.input("name") == "QueryJohn"

    async def test_stream_simple(self) -> None:
        content = b"Hello, World!"

        async def receive():
            return {"type": "http.request", "body": content, "more_body": False}

        request = Request.create("http://example.com")
        request._receive = receive

        chunks = []
        async for chunk in request.stream():
            if chunk:  # Skip empty final chunk
                chunks.append(chunk)

        assert b"".join(chunks) == content

    async def test_stream_consumed_error(self) -> None:
        async def receive():
            return {"type": "http.request", "body": b"test", "more_body": False}

        request = Request.create("http://example.com")
        request._receive = receive

        # Consume the stream once
        async for _ in request.stream():
            pass

        # Second attempt should raise error
        with pytest.raises(
            RuntimeError, match="Request stream has already been consumed"
        ):
            async for _ in request.stream():
                pass

    async def test_stream_disconnect(self) -> None:
        async def receive():
            return {"type": "http.disconnect"}

        request = Request.create("http://example.com")
        request._receive = receive

        with pytest.raises(ClientDisconnectedError):
            async for _ in request.stream():
                pass

    async def test_is_disconnected_false(self) -> None:
        async def receive():
            # Simulate timeout
            await asyncio.sleep(1)
            return {"type": "http.request", "body": b"", "more_body": False}

        request = Request.create("http://example.com")
        request._receive = receive

        # Should return False due to timeout
        assert not await request.is_disconnected()

    async def test_is_disconnected_true(self) -> None:
        async def receive():
            return {"type": "http.disconnect"}

        request = Request.create("http://example.com")
        request._receive = receive

        assert await request.is_disconnected()

    async def test_close_no_form(self) -> None:
        request = Request.create("http://example.com")
        # Should not raise an error even without form data
        await request.close()


class TestRequestErrorCases:
    def test_conflicting_forwarded_headers(self) -> None:
        scope: PartialScope = {
            "client": ("192.168.1.1", 80),
            "headers": [
                (b"forwarded", b"for=10.0.0.1;host=example.com"),
                (b"x-forwarded-for", b"10.0.0.2"),
            ],
        }
        request = Request.create("http://example.com", scope=scope)
        request.set_trusted_proxies(["192.168.1.0/24"])
        request.set_trusted_headers([TrustedHeader.X_FORWARDED_FOR])

        with pytest.raises(ConflictingForwardedHeadersError):
            _ = request._get_trusted_values(TrustedHeader.X_FORWARDED_FOR)

    def test_host_port_removal(self) -> None:
        scope: PartialScope = {"headers": [(b"host", b"example.com:8080")]}
        request = Request.create("http://example.com", scope=scope)
        # Host should have port removed
        assert request.host == "example.com"

    def test_empty_cookie_chunks(self) -> None:
        scope: PartialScope = {"headers": [(b"cookie", b"valid=value;;;empty=")]}
        request = Request.create("http://example.com", scope=scope)

        cookies = request.cookies
        assert cookies["valid"] == "value"
        assert cookies["empty"] == ""


class TestRequestEdgeCases:
    def test_url_without_path(self) -> None:
        request = Request.create("http://example.com")
        assert request.path == "/"

    def test_url_with_fragment(self) -> None:
        request = Request.create("http://example.com/path#fragment")
        # Fragment should be preserved in original URL but not affect path
        assert request.path == "/path"

    def test_query_params_with_empty_values(self) -> None:
        request = Request.create("http://example.com?empty=&valid=value&also_empty")
        params = request.query_params
        assert params["empty"] == ""
        assert params["valid"] == "value"
        assert params["also_empty"] == ""

    def test_headers_latin1_encoding(self) -> None:
        # Test headers with non-ASCII characters
        scope: PartialScope = {
            "headers": [(b"custom-header", "café".encode("latin-1"))]
        }
        request = Request.create("http://example.com", scope=scope)
        assert request.headers["custom-header"] == "café"

    def test_multiple_set_methods_chaining(self) -> None:
        request = Request.create("http://example.com")

        result = (
            request.set_trusted_proxies(["192.168.1.0/24"])
            .set_trusted_headers([TrustedHeader.X_FORWARDED_FOR])
            .set_trusted_hosts(["example.com"])
        )

        assert result is request
        assert request._trusted_proxies == ["192.168.1.0/24"]
        assert request._trusted_headers == [TrustedHeader.X_FORWARDED_FOR]
        assert request._trusted_hosts == ["example.com"]
