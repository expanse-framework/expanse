from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.support._utils import module_from_path
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.routing.route import Route


class RouteServiceProvider(ServiceProvider):
    def load_routes_from_file(self, path: Path) -> list[Route]:
        module = module_from_path(path)

        if module is None:
            return []

        routes = module.routes

        assert isinstance(routes, list)

        return routes
