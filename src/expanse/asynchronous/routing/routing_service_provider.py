from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.asynchronous.view.view_factory import ViewFactory


class RoutingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._app.singleton(Router, lambda app: Router(app))
        self._app.alias(Router, "router")

    async def boot(self) -> None:
        await self._app.on_resolved("view", self._register_view_globals)

    async def _register_view_globals(self, view: ViewFactory) -> None:
        router = await self._app.make(Router)
        view.register_global(url=router.url)
        view.register_global(route=router.route)
