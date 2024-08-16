from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.common.http.url import URL


class URLPath(str):
    def __new__(cls, path: str, protocol: str = "", host: str = "") -> URLPath:
        assert protocol in ("http", "websocket", "")
        return str.__new__(cls, path)

    def __init__(self, path: str, protocol: str = "", host: str = "") -> None:
        self.protocol = protocol
        self.host = host

    def make_absolute_url(self, base_url: str | URL) -> URL:
        from expanse.common.http.url import URL

        if isinstance(base_url, str):
            base_url = URL(base_url)

        if self.protocol:
            scheme = {
                "http": {True: "https", False: "http"},
                "websocket": {True: "wss", False: "ws"},
            }[self.protocol][base_url.is_secure()]

        else:
            scheme = base_url.scheme

        netloc = self.host or base_url.netloc
        path = base_url.path.rstrip("/") + str(self)
        return URL(scheme=scheme, netloc=netloc, path=path)
