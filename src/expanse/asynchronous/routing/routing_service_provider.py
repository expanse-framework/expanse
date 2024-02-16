from __future__ import annotations

from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.support.service_provider import ServiceProvider


class RoutingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._app.singleton(Router, lambda app: Router(app))
        self._app.alias(Router, "router")
