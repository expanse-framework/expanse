from typing import TYPE_CHECKING

from expanse.contracts.routing.router import Router as RouterContract
from expanse.routing.router import Router
from expanse.routing.url_generator import URLGenerator
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.view.view_factory import ViewFactory


class RoutingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(RouterContract, Router)
        self._container.alias(RouterContract, "router")

    async def boot(self) -> None:
        await self._container.on_resolved("view", self._register_view_locals)

    async def _register_view_locals(
        self, view: "ViewFactory", generator: URLGenerator
    ) -> None:
        view.register_local(url=generator.to, route=generator.to_route)
