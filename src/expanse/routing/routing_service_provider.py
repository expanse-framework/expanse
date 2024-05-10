from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.routing.redirect import Redirect
from expanse.routing.router import Router
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.common.http.url_path import URLPath
    from expanse.view.view_factory import ViewFactory


class RoutingServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._app.singleton(Router, lambda app: Router(app))
        self._app.alias(Router, "router")
        self._app.scoped(Redirect)

    def boot(self) -> None:
        self._app.on_resolved("view", self._register_view_globals)

    def _register_view_globals(self, view: ViewFactory) -> None:
        router = self._app.make(Router)

        def route(name: str, **parameters) -> URLPath:
            return router.route(name, parameters)

        def url(name: str, **parameters) -> URLPath:
            return router.url(name, parameters)

        view.register_global(url=url)
        view.register_global(route=route)
