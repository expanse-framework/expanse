from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from baize.asgi import empty_receive
from baize.asgi import empty_send
from baize.asgi.requests import Request as BaseRequest

from expanse.http.accept_header import AcceptHeader
from expanse.http.url import URL


if TYPE_CHECKING:
    from collections.abc import Mapping

    from expanse.routing.route import Route
    from expanse.session.session import HTTPSession
    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


class Request(BaseRequest):
    def __init__(
        self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send
    ):
        super().__init__(scope=scope, receive=receive, send=send)

        self._route: Route | None = None
        self._session: HTTPSession | None = None

    @cached_property
    def url(self) -> URL:  # type: ignore[override]
        return URL(scope=self._scope)

    @cached_property
    def host(self) -> str:
        client = self.client

        if not client:
            return ""

        return client.host or ""

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
        ips = [self.client.host]

        if not self.is_from_trusted_proxy():
            return [ip for ip in ips if ip is not None]

        if forwarded_ip := self.headers.get("X-Forwarded-For"):
            ips.insert(0, forwarded_ip)

        return [ip for ip in ips if ip is not None]

    @property
    def route(self) -> Route | None:
        return self._route

    @property
    def session(self) -> HTTPSession | None:
        return self._session

    def is_secure(self) -> bool:
        return self.url.scheme == "https"

    def is_from_trusted_proxy(self) -> bool:
        return False

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
            base_scope["server"][0] = url.hostname

        if url.scheme:
            base_scope["scheme"] = url.scheme

            if url.scheme == "https":
                base_scope["server"][1] = 443
            else:
                base_scope["server"][1] = 80

        if url.port is not None:
            base_scope["server"][1] = url.port

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


__all__ = ["Request"]
