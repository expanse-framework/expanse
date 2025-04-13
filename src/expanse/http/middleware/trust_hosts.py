from expanse.core.application import Application
from expanse.core.http.middleware.middleware import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler


class TrustHosts(Middleware):
    def __init__(self, app: Application) -> None:
        self._app = app

    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        await self.set_trusted_hosts(request)

        return await next_call(request)

    async def set_trusted_hosts(self, request: Request) -> None:
        trusted_hosts: list[str] | None = self._app.config.get("http.trusted_hosts")

        if not trusted_hosts:
            if self._app.config.get("app.debug"):
                # If debug mode is enabled, we only trust local hosts
                trusted_hosts = [".localhost", "127.0.0.1", "::1"]
            else:
                return

        request.set_trusted_hosts(trusted_hosts)
