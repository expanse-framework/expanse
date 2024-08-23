from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from baize.wsgi.requests import Request as BaseRequest

from expanse.common.http.accept_header import AcceptHeader
from expanse.common.http.url import URL


if TYPE_CHECKING:
    from expanse.routing.route import Route
    from expanse.types import Environ
    from expanse.types import StartResponse


class Request(BaseRequest):
    def __init__(self, environ: Environ, start_response: StartResponse | None = None):
        super().__init__(environ, start_response)  # type: ignore[arg-type]

        self._route: Route | None = None

        self._acceptable_content_types: list[str] | None = None

    @cached_property
    def url(self) -> URL:  # type: ignore[override]
        return URL(environ=self._environ)

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
            self.is_ajax()
            and not self.is_pjax()
            and self.accepts_any_content_type()
            or self.wants_json()
        )

    def is_xml_http_request(self) -> bool:
        return self.headers.get("X-Requested-With") == "XMLHttpRequest"

    def is_ajax(self) -> bool:
        return self.is_xml_http_request()

    def is_pjax(self) -> bool:
        return self.headers.get("X-PJAX") == "true"

    @property
    def route(self) -> Route | None:
        return self._route

    def set_route(self, route: Route) -> Self:
        self._route = route

        return self

    @classmethod
    def create(
        cls, raw_url: str, method: str = "GET", environ: dict[str, Any] | None = None
    ) -> Request:
        base_environ = {
            "wsgi.url_scheme": "http",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": 80,
            "HTTP_HOST": "localhost",
            "HTTP_USER_AGENT": "Expanse",
            "HTTP_ACCEPT": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "HTTP_ACCEPT_LANGUAGE": "en-us,en;q=0.5",
            "REMOTE_ADDR": "127.0.0.1",
            "SCRIPT_NAME": "",
            "SCRIPT_FILENAME": "",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "PATH_INFO": "",
            "REQUEST_METHOD": method.upper(),
            **(environ or {}),
        }

        url = URL(raw_url)

        if url.hostname is not None:
            base_environ["SERVER_NAME"] = url.hostname
            base_environ["HTTP_HOST"] = url.hostname

        if url.scheme:
            base_environ["wsgi.url_scheme"] = url.scheme

            if url.scheme == "https":
                base_environ["HTTPS"] = "on"
                base_environ["SERVER_PORT"] = 443
            else:
                base_environ.pop("HTTPS", None)
                base_environ["SERVER_PORT"] = 80

        if url.port is not None:
            base_environ["SERVER_PORT"] = url.port
            base_environ["HTTP_HOST"] += f":{url.port}"

        path = url.path
        if not path:
            path = "/"

        base_environ["PATH_INFO"] = path

        query_string = ""
        if url.query:
            query_string = url.query

        base_environ["REQUEST_URI"] = path + (
            "?" + query_string if query_string else ""
        )
        base_environ["QUERY_STRING"] = query_string

        return cls(environ=base_environ)


__all__ = ["Request"]
