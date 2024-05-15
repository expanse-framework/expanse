from __future__ import annotations

import sys

from typing import TYPE_CHECKING

from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.common.support._utils import module_from_path


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class RouteServiceProvider(ServiceProvider):
    async def load_routes_from_file(self, path: Path) -> Router:
        module_name = (
            path.resolve()
            .relative_to(self._app.base_path)
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )

        module = module_from_path(path, name=module_name)

        if module is None:
            return

        # Register route file to sys.modules
        if module_name not in sys.modules:
            sys.modules[module_name] = module

        routes: Callable[[Router], None] = module.routes

        router: Router = Router(self._app)

        routes(router)

        return router
