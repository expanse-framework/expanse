import sys

from pathlib import Path
from typing import TYPE_CHECKING

from expanse.common.support._utils import module_from_path
from expanse.routing.router import Router
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.core.application import Application


class RouteServiceProvider(ServiceProvider):
    def load_routes_from_file(self, router: Router, path: Path) -> Router:
        app: Application = self._container.make("app")
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
