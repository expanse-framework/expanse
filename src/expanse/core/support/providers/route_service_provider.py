from __future__ import annotations

import sys

from typing import TYPE_CHECKING

from expanse.support._utils import module_from_path
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from expanse.core.application import Application
    from expanse.routing.router import Router


class RouteServiceProvider(ServiceProvider):
    async def load_routes_from_file(self, router: Router, path: Path) -> Router:
        app: Application = await self._container.get("app")
        module_name = (
            path.resolve()
            .relative_to(app.base_path)
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )

        module = module_from_path(path, name=module_name)

        if module is None:
            return router

        # Register route file to sys.modules
        if module_name not in sys.modules:
            sys.modules[module_name] = module

        routes: Callable[[Router], None] = module.routes

        routes(router)

        return router
