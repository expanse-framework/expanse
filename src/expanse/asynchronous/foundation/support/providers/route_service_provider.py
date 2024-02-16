from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.common.support._utils import module_from_path


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.asynchronous.routing.route import Route


class RouteServiceProvider(ServiceProvider):
    async def load_routes_from_file(self, path: Path) -> list[Route]:
        module = module_from_path(path)

        if module is None:
            return []

        routes = module.routes

        assert isinstance(routes, list)

        return routes
