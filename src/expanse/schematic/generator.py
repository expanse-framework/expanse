from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.schematic.openapi.info import Info
from expanse.schematic.openapi.openapi import OpenAPI
from expanse.schematic.openapi.operation import Operation


if TYPE_CHECKING:
    from expanse.contracts.routing.router import Router
    from expanse.routing.route import Route
    from expanse.schematic.generator_config import GeneratorConfig


class Generator:
    def __init__(self, router: Router) -> None:
        self._router: Router = router

    def generate(self, config: GeneratorConfig) -> None:
        openapi = self.make_openapi(config)
        routes: list[Route] = []
        for route in self._router.routes:
            if not config.filter_routes(route):
                continue

            operation = self.create_operation(openapi, route, config)
            if not operation:
                continue

        print(routes)

    def make_openapi(self, config: GeneratorConfig) -> OpenAPI:
        openapi = OpenAPI(
            "3.1.0",
            Info(
                config.get("info.title", "API"), config.get("info.version", "1.0.0")
            ).set_description(config.get("info.description", "")),
        )

        return openapi

    def create_operation(
        self, openapi: OpenAPI, route: Route, config: GeneratorConfig
    ) -> Operation | None:
        if not route.name:
            return None

        operation: dict = {
            "operationId": route.name,
            "path": route.path,
            "methods": route.methods,
            "tags": config.get_tags(route),
            "summary": config.get_summary(route),
            "description": config.get_description(route),
            "parameters": config.get_parameters(route),
            "responses": config.get_responses(route),
        }

        return operation
