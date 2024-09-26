from typing import TYPE_CHECKING

from expanse.http.redirect import Redirect
from expanse.routing.router import Router
from expanse.routing.url_generator import URLGenerator
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.view.view_factory import AsyncViewFactory
    from expanse.view.view_factory import ViewFactory


class RoutingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(Router)
        self._container.alias(Router, "router")
        self._container.scoped(Redirect)

    async def boot(self) -> None:
        await self._container.on_resolved("view", self._register_view_locals)
        await self._container.on_resolved(
            "view:async", self._register_async_view_locals
        )

    async def _register_view_locals(
        self, view: "ViewFactory", generator: URLGenerator
    ) -> None:
        view.register_local(url=generator.to, route=generator.to_route)

    async def _register_async_view_locals(
        self, view: "AsyncViewFactory", generator: URLGenerator
    ) -> None:
        view.register_local(url=generator.to, route=generator.to_route)
