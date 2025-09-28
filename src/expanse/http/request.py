from __future__ import annotations

import asyncio
import ipaddress
import re

from datetime import UTC
from datetime import datetime
from email.utils import parsedate_to_datetime
from http import cookies as http_cookies
from typing import TYPE_CHECKING
from typing import Any
from typing import Self
from urllib.parse import parse_qsl

import msgspec

from baize.asgi import empty_receive
from baize.asgi import empty_send
from baize.multipart_helper import parse_async_stream

from expanse.http._datastructures import Address
from expanse.http._datastructures import ContentType
from expanse.http._datastructures import FormData
from expanse.http._datastructures import QueryParams
from expanse.http._datastructures import UploadFile
from expanse.http.accept_header import AcceptHeader
from expanse.http.exceptions import ClientDisconnectedError
from expanse.http.exceptions import ConflictingForwardedHeadersError
from expanse.http.exceptions import MalformedJSONError
from expanse.http.exceptions import MalformedMultipartError
from expanse.http.exceptions import SuspiciousOperationError
from expanse.http.exceptions import UnsupportedContentTypeError
from expanse.http.header_bag import HeaderBag
from expanse.http.trusted_header import TrustedHeader
from expanse.http.url import URL
from expanse.support._utils import cached_property


if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from collections.abc import Mapping

    from expanse.routing.route import Route
    from expanse.session.session import HTTPSession
    from expanse.types import PartialScope
    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


FORWARDED_PARAMS = {
    TrustedHeader.X_FORWARDED_FOR: "for",
    TrustedHeader.X_FORWARDED_HOST: "host",
    TrustedHeader.X_FORWARDED_PROTO: "proto",
    TrustedHeader.X_FORWARDED_PORT: "host",
}


class Request:
    def __init__(
        self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send
    ):
        self._scope: Scope = scope
        self._receive: Receive = receive
        self._send: Send = send
        self._route: Route | None = None
        self._session: HTTPSession | None = None
        self._trusted_proxies: list[str] = []
        self._trusted_headers: list[TrustedHeader] = []
        self._trusted_hosts: list[str] = ["*"]
        self._url: URL = URL.from_scope(scope)
        self._stream_consumed: bool = False
        self._is_disconnected: bool = False
        self.path_params: dict[str, Any] = {}

    @cached_property
    def method(self) -> str:
        """
        HTTP method. Uppercase string.
        """
        return self._scope["method"]

    @cached_property
    def content_type(self) -> ContentType:
        """
        The request's content-type
        """
        return ContentType.from_string(self.headers.get("content-type", ""))

    @cached_property
    def content_length(self) -> int | None:
        """
        The request's content-length
        """
        if self.headers.get("transfer-encoding", "") == "chunked":
            return None

        content_length = self.headers.get("content-length", None)
        if content_length is None:
            return None

        try:
            return max(0, int(content_length))
        except (ValueError, TypeError):
            return None

    @cached_property
    def cookies(self) -> dict[str, str]:
        cookies: dict[str, str] = {}
        cookie_header = self.headers.get("cookie", "")

        # This function has been adapted from Django 3.1.0.
        # Note: we are explicitly _NOT_ using `SimpleCookie.load` because it is based
        # on an outdated spec and will fail on lots of input we want to support
        for chunk in cookie_header.split(";"):
            if not chunk:
                continue
            if "=" in chunk:
                key, val = chunk.split("=", 1)
            else:
                # Assume an empty name per
                # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
                key, val = "", chunk
            key, val = key.strip(), val.strip()
            if key or val:
                # unquote using Python's algorithm.
                cookies[key] = http_cookies._unquote(val)
        return cookies

    @cached_property
    def date(self) -> datetime | None:
        """
        The sending time of the request.

        NOTE: The datetime object is timezone-aware.
        """
        value = self.headers.get("date", None)
        if value is None:
            return None

        try:
            date = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

        if date.tzinfo is None:
            return date.replace(tzinfo=UTC)

        return date

    @cached_property
    def referrer(self) -> URL | None:
        """
        The `Referer` HTTP request header contains an absolute or partial address
        of the page making the request.
        """
        referrer = self.headers.get("referer", None)
        if referrer is None:
            return None

        return URL(url=referrer)

    @cached_property
    def client(self) -> Address:
        """
        Client's IP and Port.

        Note that this depends on the "client" value given by
        the ASGI Server, and is not necessarily accurate.
        """
        host, port = self._scope.get("client") or (None, None)
        return Address(host=host, port=port)

    @cached_property
    def query_params(self) -> QueryParams:
        """
        Query parameter. It is a multi-value mapping.
        """
        return QueryParams(self._scope["query_string"])

    @cached_property
    def url(self) -> URL:
        return self._url.replace(scheme=self.scheme, hostname=self.http_host, port=None)

    @cached_property
    def headers(self) -> HeaderBag:
        """
        Get the request headers as a dictionary.

        The keys are normalized to lowercase.
        """
        return HeaderBag(
            {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in self._scope.get("headers", [])
            }
        )

    @cached_property
    def host(self) -> str:
        host: str
        if (
            self.is_from_trusted_proxy()
            and self.is_header_trusted(TrustedHeader.X_FORWARDED_HOST)
            and (hosts := self._get_trusted_values(TrustedHeader.X_FORWARDED_HOST))
        ):
            host = hosts[0]
        elif "Host" not in self.headers:
            # If there is no Host header, we have to use the server name
            server: tuple[str | None, int | None] | None = self._scope.get("server")
            host = "" if not server or not server[0] else server[0]
        else:
            host = self.headers["Host"]

        host = re.sub(r":\d+$", "", host).lower()

        is_trusted: bool = False
        for trusted_host in self._trusted_hosts:
            if trusted_host.startswith("."):
                # Check if the host ends with the trusted host
                if host.endswith(trusted_host[1:]):
                    is_trusted = True
                    break
            elif host == trusted_host:
                is_trusted = True
                break
            elif trusted_host == "*":
                # If the trusted host is "*", we trust any host
                is_trusted = True
                break

        if not is_trusted:
            # If the host is not trusted, we should not return it
            raise SuspiciousOperationError(f"Host '{host}' is not trusted")

        return host

    @cached_property
    def http_host(self) -> str:
        """
        Get the normalized HTTP host.

        The port will only be appended if it is not the default port for the scheme.

        :return: The HTTP host.
        """
        scheme = self.scheme
        port = self.port

        if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
            return self.host

        return f"{self.host}:{port}"

    @cached_property
    def port(self) -> int:
        """
        Get the port on which the request was made.

        The port can be retrieved from the `X-Forwarded-Port` header when trusted proxies
        were configured via the `set_trusted_proxies()` method.

        :return: The port number.
        """
        if not self.is_from_trusted_proxy():
            return self._url.port or (443 if self.scheme == "https" else 80)

        if self.is_header_trusted(TrustedHeader.X_FORWARDED_PORT) and (
            ports := self._get_trusted_values(TrustedHeader.X_FORWARDED_PORT)
        ):
            return int(ports[0])
        elif self.is_header_trusted(TrustedHeader.X_FORWARDED_HOST) and (
            hosts := self._get_trusted_values(TrustedHeader.X_FORWARDED_HOST)
        ):
            if ":" in hosts[0]:
                return int(hosts[0].split(":")[1])

            return 443 if self.scheme == "https" else 80
        elif host := self.headers.get("Host"):
            if ":" in host:
                return int(host.split(":")[1])

            return 443 if self.scheme == "https" else 80

        return self._url.port or (443 if self.scheme == "https" else 80)

    @cached_property
    def acceptable_content_types(self) -> list[str]:
        return [
            item.value
            for item in AcceptHeader.from_string(self.headers.get("Accept", "")).all()
        ]

    @cached_property
    def ip(self) -> str | None:
        ips = self.ips

        return ips[0] if ips else None

    @cached_property
    def ips(self) -> list[str]:
        ips: list[str] = []

        if self.client.host is not None:
            ips.append(self.client.host)

        if not self.is_from_trusted_proxy():
            return ips

        if self.is_header_trusted(TrustedHeader.X_FORWARDED_FOR) and (
            forwarded_ips := self._get_trusted_values(TrustedHeader.X_FORWARDED_FOR)
        ):
            ips = forwarded_ips + ips

        return ips

    @property
    def route(self) -> Route | None:
        return self._route

    @property
    def session(self) -> HTTPSession | None:
        return self._session

    @property
    def scheme(self) -> str:
        return "https" if self.is_secure() else "http"

    @property
    def path(self) -> str:
        return self._url.path

    def is_secure(self) -> bool:
        if not self.is_from_trusted_proxy() or not self.is_header_trusted(
            TrustedHeader.X_FORWARDED_PROTO
        ):
            return self._url.scheme == "https"

        forwarded_proto = self._get_trusted_values(TrustedHeader.X_FORWARDED_PROTO)
        if forwarded_proto:
            return forwarded_proto[0] == "https"

        return self._url.scheme == "https"

    def set_trusted_proxies(self, trusted_proxies: list[str]) -> Self:
        """
        Set trusted proxies for the request.

        :param trusted_proxies: List of trusted proxies.
        """
        self._trusted_proxies = trusted_proxies

        return self

    def set_trusted_headers(self, trusted_headers: list[TrustedHeader]) -> Self:
        """
        Set trusted headers for the request.

        :param trusted_headers: List of trusted headers.
        """
        self._trusted_headers = trusted_headers

        return self

    def set_trusted_hosts(self, trusted_hosts: list[str]) -> Self:
        """
        Set trusted hosts for the request.

        :param trusted_hosts: List of trusted hosts.
        """
        self._trusted_hosts = trusted_hosts

        return self

    def is_from_trusted_proxy(self) -> bool:
        if not self._trusted_proxies:
            return False

        if not self.client.host:
            return False

        return any(
            ipaddress.ip_address(self.client.host) in ipaddress.ip_network(proxy)
            for proxy in self._trusted_proxies
        )

    def is_header_trusted(self, header: TrustedHeader) -> bool:
        """
        Check if the header is trusted.

        :param header: The header to check.
        """
        return header in self._trusted_headers

    def accepts_any_content_type(self) -> bool:
        """
        Determine if the current request accepts any content type.
        """
        acceptable = self.acceptable_content_types

        return len(acceptable) == 0 or acceptable[0] in ("*/*", "*")

    def is_json(self) -> bool:
        """
        Determine whether the request is sending JSON or not.
        """
        return "/json" in self.content_type.type or "+json" in self.content_type.type

    def wants_json(self) -> bool:
        """
        Determine whether the request is asking for JSON or not.
        """
        acceptable = self.acceptable_content_types

        return len(acceptable) > 0 and (
            "/json" in acceptable[0] or "+json" in acceptable[0]
        )

    def expects_json(self) -> bool:
        """
        Determine if the current request probably expects a JSON response.
        """
        return (
            self.is_ajax() and not self.is_pjax() and self.accepts_any_content_type()
        ) or self.wants_json()

    def is_xml_http_request(self) -> bool:
        return self.headers.get("X-Requested-With") == "XMLHttpRequest"

    def is_ajax(self) -> bool:
        return self.is_xml_http_request()

    def is_pjax(self) -> bool:
        return self.headers.get("X-PJAX") == "true"

    def set_route(self, route: Route) -> Self:
        self._route = route

        return self

    def set_session(self, session: HTTPSession) -> Self:
        self._session = session

        return self

    async def input(self, name: str, default: Any = None) -> Any:
        """
        Retrieve an input item from the request.

        It will search in the request body and query string.

        :param name: The name of the input item.

        :return: The input item.
        """
        source: Mapping[str, Any] = {}
        if self.is_json():
            source = await self.json

            if not isinstance(source, dict):
                source = {}
        elif self.method in ("POST", "PUT", "PATCH"):
            source = await self.form
        else:
            source = self.query_params

        return {**source, **self.query_params}.get(name, default)

    async def stream(self) -> AsyncIterator[bytes]:
        """
        Streaming read request body. e.g. `async for chunk in request.stream(): ...`

        If you access `.stream()` then the byte chunks are provided
        without storing the entire body to memory. Any subsequent
        calls to `.body`, `.form`, or `.json` will raise an error.
        """
        if "body" in self.__dict__ and self.__dict__["body"].done():
            yield await self.body
            yield b""
            return

        if self._stream_consumed:
            raise RuntimeError("Request stream has already been consumed.")

        self._stream_consumed = True
        while True:
            message = await self._receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    yield body
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                self._is_disconnected = True
                raise ClientDisconnectedError()
        yield b""

    @cached_property
    async def body(self) -> bytes:
        """
        Read all the contents of the request body into the memory and return it.
        """
        return b"".join([chunk async for chunk in self.stream()])

    @cached_property
    async def json(self) -> Any:
        """
        Call `await self.body` and use `json.loads` parse it.

        If `content_type` is not equal to `application/json`,
        an HTTPExcption exception will be thrown.
        """
        if self.content_type == "application/json":
            data = await self.body
            try:
                return msgspec.json.decode(
                    data.decode(self.content_type.options.get("charset", "utf8"))
                )
            except msgspec.DecodeError as exc:
                raise MalformedJSONError(str(exc)) from None

        raise UnsupportedContentTypeError("application/json")

    async def _parse_multipart(self, boundary: bytes, charset: str) -> FormData:
        return FormData(
            await parse_async_stream(
                self.stream(), boundary, charset, file_factory=UploadFile
            )
        )

    @cached_property
    async def form(self) -> FormData:
        """
        Parse the data in the form format and return it as a multi-value mapping.

        If `content_type` is equal to `multipart/form-data`, it will directly
        perform streaming analysis, and subsequent calls to `self.body`
        or `self.json` will raise errors.

        If `content_type` is not equal to `multipart/form-data` or
        `application/x-www-form-urlencoded`, an HTTPExcption exception will be thrown.
        """
        if self.content_type == "multipart/form-data":
            charset = self.content_type.options.get("charset", "utf8")
            if "boundary" not in self.content_type.options:
                raise MalformedMultipartError("Missing boundary in header content-type")
            boundary = self.content_type.options["boundary"].encode("latin-1")
            return await self._parse_multipart(boundary, charset)
        if self.content_type == "application/x-www-form-urlencoded":
            body = (await self.body).decode(
                encoding=self.content_type.options.get("charset", "latin-1")
            )
            return FormData(parse_qsl(body, keep_blank_values=True))

        raise UnsupportedContentTypeError(
            "multipart/form-data, application/x-www-form-urlencoded"
        )

    async def close(self) -> None:
        """
        Close all temporary files in the `self.form`.

        This can always be called, regardless of whether you use form or not.
        """
        if "form" in self.__dict__ and self.__dict__["form"].done():
            await (await self.form).aclose()

    async def is_disconnected(self) -> bool:
        """
        The method used to determine whether the connection is interrupted.
        """
        if not self._is_disconnected:
            try:
                message = await asyncio.wait_for(self._receive(), timeout=0.0000001)
                self._is_disconnected = message.get("type") == "http.disconnect"
            except TimeoutError:
                pass
        return self._is_disconnected

    @classmethod
    def create(
        cls, raw_url: str, method: str = "GET", scope: PartialScope | None = None
    ) -> Request:
        default_headers = {
            b"User-Agent": b"Expanse",
            b"Accept": b"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            b"Accept-Language": b"en-us,en;q=0.5",
        }
        base_scope: Scope = {
            "type": "http",
            "asgi": {
                "version": "3.0",
                "spec_version": "2.3",
            },
            "client": ("127.0.0.1", 80),
            "scheme": "http",
            "server": ("localhost", 80),
            "headers": [],
            "root_path": "",
            "http_version": "1.1",
            "path": "",
            "query_string": b"",
            "raw_path": b"",
            "method": method.upper(),
        }

        if scope is not None:
            base_scope.update(scope)

        headers = base_scope["headers"]
        header_names = {header[0] for header in headers}

        for default_header in default_headers:
            if default_header not in header_names:
                headers.append((default_header, default_headers[default_header]))

        url = URL(raw_url)

        assert base_scope["server"] is not None
        if url.hostname is not None:
            base_scope["server"] = (url.hostname, base_scope["server"][1])

        if url.scheme:
            base_scope["scheme"] = url.scheme

            if url.scheme == "https":
                base_scope["server"] = (base_scope["server"][0], 443)
                base_scope["scheme"] = "https"
            else:
                base_scope["server"] = (base_scope["server"][0], 80)

        if url.port is not None:
            base_scope["server"] = (base_scope["server"][0], url.port)

        path = url.path
        if not path:
            path = "/"

        base_scope["path"] = path
        base_scope["raw_path"] = path.encode()

        query_string = ""
        if url.query:
            query_string = url.query

        base_scope["query_string"] = query_string.encode()

        return cls(scope=base_scope)

    def _get_trusted_values(self, header: TrustedHeader) -> list[str]:
        """
        Get the trusted values for the request.

        :return: The trusted values.
        """
        client_values: list[str] = []
        forwarded_values: list[str] = []

        if header in self.headers:
            header_value = self.headers[header]
            for value in header_value.split(","):
                client_values.append(value.strip())

        if TrustedHeader.FORWARDED in self.headers and header in FORWARDED_PARAMS:
            from expanse.http.utils.forwarded_header import ForwardedHeader

            param = FORWARDED_PARAMS[header]

            forwarded_header = ForwardedHeader.parse(
                self.headers[TrustedHeader.FORWARDED]
            )

            match param:
                case "for":
                    if forwarded_header.for_ is not None:
                        forwarded_values = [
                            str(node.ip)
                            for node in forwarded_header.for_
                            if node.ip is not None
                        ]
                case "host":
                    if forwarded_header.host is not None:
                        forwarded_values = [forwarded_header.host]

                        if header is TrustedHeader.X_FORWARDED_PORT:
                            forwarded_values = [
                                value.split(":")[1]
                                if ":" in value
                                else ("443" if self.is_secure() else "80")
                                for value in forwarded_values
                            ]

                case "proto":
                    if forwarded_header.proto is not None:
                        forwarded_values = [forwarded_header.proto]

        if client_values == forwarded_values or not client_values:
            return forwarded_values

        if not forwarded_values:
            return client_values

        raise ConflictingForwardedHeadersError(
            f"The request has both a {TrustedHeader.FORWARDED} header "
            + f"and a {header} header, which are conflicting. "
            + "You should configure your proxy to remove one of them."
        )


__all__ = ["Request"]
