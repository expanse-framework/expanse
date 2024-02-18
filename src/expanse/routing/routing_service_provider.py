from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.routing.router import Router
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.view.view_factory import ViewFactory


class RoutingServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._app.singleton(Router, lambda app: Router(app))
        self._app.alias(Router, "router")

    def boot(self) -> None:
        self._app.on_resolved("view", self._register_view_globals)

    def _register_view_globals(self, view: ViewFactory) -> None:
        router = self._app.make(Router)
        view.register_global(url=router.url)
        view.register_global(route=router.route)
