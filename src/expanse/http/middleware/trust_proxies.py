from expanse.core.application import Application
from expanse.core.http.middleware.middleware import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.http.trusted_header import TrustedHeader
from expanse.types.http.middleware import RequestHandler


_DEFAULT_TRUSTED_HEADERS: list[str] = [
    "x-forwarded-for",
    "x-forwarded-proto",
    "x-forwarded-port",
    "forwarded",
]


class TrustProxies(Middleware):
    def __init__(self, app: Application) -> None:
        self._app = app

    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        await self.set_trusted_proxies(request)

        return await next_call(request)

    async def set_trusted_proxies(self, request: Request) -> None:
        trusted_proxies: list[str] | None = self._app.config.get("http.trusted_proxies")

        if trusted_proxies:
            if "*" in trusted_proxies and request.client.host:
                # Trust the calling ip address
                request.set_trusted_proxies([request.client.host])
            else:
                request.set_trusted_proxies(trusted_proxies)

        trusted_headers: list[str] | None = self._app.config.get("http.trusted_headers")

        if trusted_headers is None:
            trusted_headers = _DEFAULT_TRUSTED_HEADERS.copy()

        if trusted_headers:
            request.set_trusted_headers(
                [TrustedHeader(header.lower()) for header in trusted_headers]
            )
