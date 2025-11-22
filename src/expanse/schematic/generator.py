from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.routing.route import Route
from expanse.schematic.analyzers.schema_registry import SchemaRegistry
from expanse.schematic.generator_config import GeneratorConfig
from expanse.schematic.inference.inference import Inference
from expanse.schematic.openapi.components import Components
from expanse.schematic.openapi.info import Info
from expanse.schematic.openapi.openapi import OpenAPI
from expanse.schematic.openapi.operation import Operation
from expanse.schematic.openapi.path_item import PathItem
from expanse.schematic.openapi.paths import Paths
from expanse.schematic.support.operation_builder import OperationBuilder
from expanse.schematic.support.route_info import RouteInfo


class Generator:
    """
    Generates OpenAPI specifications from route definitions.
    """

    def __init__(
        self,
        app: Application,
        operation_builder: OperationBuilder,
        inference: Inference,
    ) -> None:
        self._app: Application = app
        self._operation_builder: OperationBuilder = operation_builder
        self._inference: Inference = inference

    def generate(self, config: GeneratorConfig, router: Router) -> OpenAPI:
        openapi = self.make_openapi(config)
        paths = Paths()
        components = Components()
        schema_registry = SchemaRegistry(components, base_path=self._app.base_path)

        routes_by_path: dict[str, list[Route]] = {}
        for route in router.routes:
            if not config.filter_routes(route):
                continue

            if route.path not in routes_by_path:
                routes_by_path[route.path] = []
            routes_by_path[route.path].append(route)

        for path, routes in routes_by_path.items():
            path_item = PathItem()

            for route in routes:
                operation = self.create_operation(
                    openapi, route, config, schema_registry
                )
                if operation:
                    # Add operation to path item based on HTTP method
                    for method in route.methods:
                        method_lower = method.lower()
                        if method_lower == "get":
                            path_item.set_get(operation)
                        elif method_lower == "post":
                            path_item.set_post(operation)
                        elif method_lower == "put":
                            path_item.set_put(operation)
                        elif method_lower == "patch":
                            path_item.set_patch(operation)
                        elif method_lower == "delete":
                            path_item.set_delete(operation)
                        elif method_lower == "head":
                            path_item.set_head(operation)
                        elif method_lower == "options":
                            path_item.set_options(operation)

            paths.add_path(path, path_item)

        openapi.set_paths(paths)

        # Add components if any schemas were created
        if components.schemas:
            openapi.set_components(components)

        return openapi

    def make_openapi(self, config: GeneratorConfig) -> OpenAPI:
        openapi = OpenAPI(
            "3.1.0",
            Info(
                config.get("info.title", "API"), config.get("info.version", "1.0.0")
            ).set_description(config.get("info.description", "")),
        )

        return openapi

    def create_operation(
        self,
        openapi: OpenAPI,
        route: Route,
        config: GeneratorConfig,
        schema_registry: SchemaRegistry,
    ) -> Operation | None:
        route_info = RouteInfo(route, self._inference)
        operation = self._operation_builder.build(
            openapi, route_info, config, schema_registry, self._inference
        )

        return operation
