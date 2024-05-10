from __future__ import annotations

from typing import TYPE_CHECKING

from baize.asgi import empty_receive
from baize.asgi import empty_send
from baize.asgi.requests import Request as BaseRequest

from expanse.common.http.accept_header import AcceptHeader
from expanse.common.http.url import URL


if TYPE_CHECKING:
    from expanse.asynchronous.types import Receive
    from expanse.asynchronous.types import Scope
    from expanse.asynchronous.types import Send


class Request(BaseRequest):
    def __init__(
        self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send
    ):
        super().__init__(scope=scope, receive=receive, send=send)

        self._acceptable_content_types: list[str] | None = None
        self._url: URL | None = None

    @property
    def url(self) -> URL:
        if self._url is None:
            self._url = URL(scope=self._scope)

        return self._url

    @property
    def host(self) -> str:
        client = self.client

        if not client:
            return ""

        return client.host

    @property
    def acceptable_content_types(self) -> list[str]:
        if self._acceptable_content_types is None:
            self._acceptable_content_types = [
                item.value
                for item in AcceptHeader.from_string(
                    self.headers.get("Accept", "")
                ).all()
            ]

        return self._acceptable_content_types

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


__all__ = ["Request"]
