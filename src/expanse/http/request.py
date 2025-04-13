from __future__ import annotations

import ipaddress
import re

from functools import cached_property
from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from baize.asgi import empty_receive
from baize.asgi import empty_send
from baize.asgi.requests import Request as BaseRequest

from expanse.http.accept_header import AcceptHeader
from expanse.http.exceptions import ConflictingForwardedHeadersError
from expanse.http.exceptions import SuspiciousOperationError
from expanse.http.trusted_header import TrustedHeader
from expanse.http.url import URL


if TYPE_CHECKING:
    from collections.abc import Mapping

    from expanse.routing.route import Route
    from expanse.session.session import HTTPSession
    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


FORWARDED_PARAMS = {
    TrustedHeader.X_FORWARDED_FOR: "for",
    TrustedHeader.X_FORWARDED_HOST: "host",
    TrustedHeader.X_FORWARDED_PROTO: "proto",
    TrustedHeader.X_FORWARDED_PORT: "host",
}


class Request(BaseRequest):
    def __init__(
        self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send
    ):
        super().__init__(scope=scope, receive=receive, send=send)

        self._route: Route | None = None
        self._session: HTTPSession | None = None
        self._trusted_proxies: list[str] = []
        self._trusted_headers: list[TrustedHeader] = []
        self._trusted_hosts: list[str] = []
        self._url = URL(scope=scope)

    @cached_property
    def url(self) -> URL:  # type: ignore[override]
        return self._url.replace(scheme=self.scheme, hostname=self.http_host, port=None)

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

        host = re.sub(":\d+$", "", host).lower()

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

    @classmethod
    def create(
        cls, raw_url: str, method: str = "GET", scope: dict[str, Any] | None = None
    ) -> Request:
        default_headers = {
            b"User-Agent": b"Expanse",
            b"Accept": b"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            b"Accept-Language": b"en-us,en;q=0.5",
        }
        base_scope = {
            "type": "http",
            "scheme": "http",
            "server": ["localhost", 80],
            "headers": [],
            "REMOTE_ADDR": "127.0.0.1",
            "root_path": "",
            "http_version": "1.1",
            "path": "",
            "raw_path": "",
            "method": method.upper(),
            **(scope or {}),
        }

        headers = base_scope["headers"]
        header_names = {header[0] for header in headers}

        for default_header in default_headers:
            if default_header not in header_names:
                headers.append([default_header, default_headers[default_header]])

        url = URL(raw_url)

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
        base_scope["raw_path"] = path

        query_string = ""
        if url.query:
            query_string = url.query

        base_scope["query_string"] = query_string

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
            f"and a {header} header, which are conflicting. "
            f"You should configure your proxy to remove one of them."
        )


__all__ = ["Request"]
