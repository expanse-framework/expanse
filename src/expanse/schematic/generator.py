from collections.abc import Callable

from expanse.contracts.routing.router import Router
from expanse.routing.route import Route
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

    Uses an extensible architecture with:
    - Signature analyzer for extracting parameter information
    - Docstring parser for extracting documentation
    - Schema generator for converting Python types to OpenAPI schemas
    - Code inference for detecting HTTP errors and responses
    - Operation builders for constructing OpenAPI operations
    """

    def __init__(
        self, operation_builder: OperationBuilder, inference: Inference
    ) -> None:
        self._operation_builder = operation_builder
        self._inference = inference

    def generate(self, config: GeneratorConfig, router: Router) -> OpenAPI:
        """
        Generate an OpenAPI specification.

        Args:
            config: Configuration for the generator

        Returns:
            OpenAPI specification object
        """
        openapi = self.make_openapi(config)
        paths = Paths()
        components = Components()

        # Group routes by path
        routes_by_path: dict[str, list[Route]] = {}
        for route in router.routes:
            if not config.filter_routes(route):
                continue

            if route.path not in routes_by_path:
                routes_by_path[route.path] = []
            routes_by_path[route.path].append(route)

        # Process each path
        for path, routes in routes_by_path.items():
            path_item = PathItem()

            for route in routes:
                operation = self.create_operation(openapi, route, config)
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
        """
        Create the base OpenAPI object with metadata.

        Args:
            config: Configuration for the generator

        Returns:
            OpenAPI object with basic information
        """
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
        route_info = RouteInfo(route, self._inference)
        operation = self._operation_builder.build(
            openapi, route_info, config, self._inference
        )

        return operation
        # Get the actual function to analyze
        func = self._get_route_function(route)

        # Analyze the route
        signature_info = self._signature_analyzer.analyze(route)
        docstring_info = self._docstring_parser.parse(func)
        code_analysis = self._code_analyzer.analyze(func)
        inference_result = self._inference.infer(route, func, code_analysis)

        # Create the operation
        operation = Operation(route.methods[0].lower())
        operation.set_operation_id(route.name)

        # Set summary and description
        if docstring_info.summary:
            operation.set_summary(docstring_info.summary)
        if docstring_info.description:
            operation.set_description(docstring_info.description)

        # Add tags from config
        tags = self._get_tags(route, config)
        for tag in tags:
            operation.add_tag(tag)

        # Build operation using extensions
        self._operation_builder.build(
            operation,
            route,
            func,
            signature_info,
            docstring_info,
            inference_result,
            self._schema_generator,
            components,
        )

        return operation

    def _get_route_function(self, route: Route) -> Callable:
        """
        Get the actual function from a route.

        Args:
            route: The route

        Returns:
            The callable function
        """
        if isinstance(route.endpoint, tuple):
            # It's a class method
            class_type = route.endpoint[0]
            method_name = route.endpoint[1]
            return getattr(class_type, method_name)
        else:
            return route.endpoint

    def _get_tags(self, route: Route, config: GeneratorConfig) -> list[str]:
        """
        Get tags for a route.

        Args:
            route: The route
            config: Configuration for the generator

        Returns:
            List of tags
        """
        # For now, extract from path
        # e.g., /api/users/... -> ["users"]
        path_parts = route.path.strip("/").split("/")
        if len(path_parts) >= 2:
            # Skip the first part (e.g., "api") and use the second
            return [path_parts[1]]
        return []

    def add_inference_extension(self, extension) -> None:
        """
        Add a custom inference extension.

        Args:
            extension: The inference extension to add
        """
        self._inference.add_extension(extension)

    def add_operation_builder_extension(self, extension) -> None:
        """
        Add a custom operation builder extension.

        Args:
            extension: The operation builder extension to add
        """
        self._operation_builder.add_extension(extension)
