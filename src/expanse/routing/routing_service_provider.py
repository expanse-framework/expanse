from __future__ import annotations

from expanse.routing.router import Router
from expanse.support.service_provider import ServiceProvider


class RoutingServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._app.singleton(Router, lambda app: Router(app))
        self._app.alias(Router, "router")
