from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.contracts.routing.router import Router
    from expanse.routing.route import Route
    from expanse.schematic.generator_config import GeneratorConfig


class Generator:
    def __init__(self, router: Router) -> None:
        self._router: Router = router

    def generate(self, config: GeneratorConfig) -> None:
        routes: list[Route] = []
        for route in self._router.routes:
            if not config.filter_routes(route):
                continue

            routes.append(route)

        print(routes)
