import re

from typing import Any
from urllib.parse import urlencode

from expanse.common.http.url import URL
from expanse.http.request import Request
from expanse.routing.router import Router


class URLGenerator:
    def __init__(self, router: Router, request: Request) -> None:
        self._router: Router = router
        self._request: Request = request

    def to(
        self,
        path: str,
        secure: bool | None = None,
    ) -> str:
        # If the URL is already valid, there is nothing to do, and we return it directly.
        if self._is_valid_url(path):
            return path

        url = self._request.url

        if secure is not None:
            url = url.replace(scheme="https" if secure else "http")

        return str(url.replace(path=path))

    def to_route(
        self,
        name: str,
        parameters: dict[str, Any] | None = None,
        absolute: bool = False,
    ) -> str:
        # If the URL is already valid, there is nothing to do, and we return it directly.
        url = self._router.route(name, parameters)

        if absolute:
            return str(
                URL(url).replace(
                    scheme=self._request.url.scheme, netloc=self._request.url.netloc
                )
            )

        return str(url)

    def _format_parameters(self, parameters: dict[str, Any] | None) -> str:
        if parameters is None:
            return ""

        return urlencode(parameters)

    def _is_valid_url(self, path: str) -> bool:
        return re.match(r"^(#|//|https?://|(mailto|tel|sms):)", path) is not None
