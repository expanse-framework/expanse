from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.asynchronous.routing.redirect import Redirect
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.asynchronous.view.view_factory import ViewFactory
    from expanse.common.http.url_path import URLPath


class RoutingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(Router)
        self._container.alias(Router, "router")
        self._container.scoped(Redirect)

    async def boot(self) -> None:
        await self._container.on_resolved("view", self._register_view_globals)

    async def _register_view_globals(self, view: ViewFactory) -> None:
        router = await self._container.make(Router)

        async def route(name: str, **parameters) -> URLPath:
            return await router.route(name, parameters)

        async def url(name: str, **parameters) -> URLPath:
            return await router.url(name, parameters)

        view.register_global(url=url)
        view.register_global(route=route)
