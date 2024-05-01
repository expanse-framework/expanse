from __future__ import annotations

import sys

from typing import TYPE_CHECKING

from expanse.common.support._utils import module_from_path
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.common.routing.route import Route


class RouteServiceProvider(ServiceProvider):
    def load_routes_from_file(self, path: Path) -> list[Route]:
        module_name = (
            path.resolve()
            .relative_to(self._app.base_path)
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )

        module = module_from_path(path, name=module_name)

        if module is None:
            return []

        # Register route file to sys.modules
        if module_name not in sys.modules:
            sys.modules[module_name] = module

        routes = module.routes

        assert isinstance(routes, list)

        return routes
