from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.requests import Request as BaseRequest
from starlette.requests import empty_receive
from starlette.requests import empty_send

from expanse.http.accept_header import AcceptHeader
from expanse.http.url import URL


if TYPE_CHECKING:
    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


class Request(BaseRequest):
    def __init__(
        self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send
    ):
        super().__init__(scope)

        self._acceptable_content_types: list[str] | None = None
        self._url: URL | None = None

    @property
    def url(self) -> URL:
        if self._url is None:
            self._url = URL(scope=self.scope)

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

    def is_json(self) -> bool:
        """
        Determine whether the request is sending JSON or not.
        """

        content_type = self.headers.get("Content-Type", "")

        return "/json" in content_type or "+json" in content_type

    def wants_json(self) -> bool:
        """
        Determine whether the request is asking for JSON or not.
        """
        acceptable = self.acceptable_content_types

        return len(acceptable) > 0 and (
            "/json" in acceptable[0] or "+json" in acceptable[0]
        )


__all__ = ["Request"]
