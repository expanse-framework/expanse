from __future__ import annotations

import re

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.openapi.config import OpenAPIConfig
    from expanse.routing.route import Route


class RouteInfo:
    """Information extracted from a route."""

    def __init__(
        self,
        route: Route,
        path: str,
        methods: list[str],
        name: str | None = None,
        tags: list[str] | None = None,
        middleware: list[str] | None = None,
    ) -> None:
        """Initialize route information."""
        self.route = route
        self.path = path
        self.methods = methods
        self.name = name
        self.tags = tags or []
        self.middleware = middleware or []
        self.path_parameters: list[dict[str, Any]] = []
        self.query_parameters: list[dict[str, Any]] = []

        # Extract path parameters
        self._extract_path_parameters()

    def _extract_path_parameters(self) -> None:
        """Extract path parameters from the route path."""
        # Find all path parameters like {id}, {user_id}, etc.
        param_pattern = r"\{([^}]+)\}"
        matches = re.findall(param_pattern, self.path)

        for param_name in matches:
            # Basic parameter info - can be enhanced by function analysis
            param_info = {
                "name": param_name,
                "in": "path",
                "required": True,
                "schema": {
                    "type": "string"
                },  # Default to string, will be refined later
            }
            self.path_parameters.append(param_info)

    def get_openapi_path(self) -> str:
        """Convert route path to OpenAPI format."""
        # Expanse uses {param} format which is already OpenAPI compatible
        return self.path

    def has_path_parameters(self) -> bool:
        """Check if route has path parameters."""
        return len(self.path_parameters) > 0

    def get_operation_id(self, method: str) -> str:
        """Generate operation ID for the route and method."""
        if self.name:
            return f"{method.lower()}_{self.name}"

        # Generate from path
        path_parts = [
            part for part in self.path.split("/") if part and not part.startswith("{")
        ]
        if path_parts:
            operation_name = "_".join(path_parts)
        else:
            operation_name = "root"

        return f"{method.lower()}_{operation_name}"


class RouteAnalyzer:
    """Analyzes routes to extract OpenAPI information."""

    def __init__(self, config: OpenAPIConfig) -> None:
        """Initialize route analyzer with configuration."""
        self.config = config

    def analyze_route(self, route: Route) -> RouteInfo | None:
        """
        Analyze a single route and extract information.

        Args:
            route: The route to analyze

        Returns:
            RouteInfo if route should be included, None otherwise
        """
        # Get basic route information
        path = self._get_route_path(route)
        methods = self._get_route_methods(route)
        name = self._get_route_name(route)

        # Check if route should be included
        if not self.config.should_include_route(path):
            return None

        # Skip internal routes if configured
        if not self.config.include_internal_routes and self._is_internal_route(route):
            return None

        # Extract tags and middleware
        tags = self._extract_tags(route)
        middleware = self._extract_middleware(route)

        return RouteInfo(
            route=route,
            path=path,
            methods=methods,
            name=name,
            tags=tags,
            middleware=middleware,
        )

    def _get_route_path(self, route: Route) -> str:
        """Extract path from route."""
        return getattr(route, "path", "/")

    def _get_route_methods(self, route: Route) -> list[str]:
        """Extract HTTP methods from route."""
        methods = getattr(route, "methods", None)
        if methods:
            if isinstance(methods, str):
                return [methods.upper()]
            elif isinstance(methods, (list, tuple, set)):
                return [method.upper() for method in methods]

        # Try to get from route attributes
        if hasattr(route, "method"):
            return [route.method.upper()]

        # Default fallback - try to infer from route creation method
        route_str = str(route).lower()
        if "get" in route_str:
            return ["GET"]
        elif "post" in route_str:
            return ["POST"]
        elif "put" in route_str:
            return ["PUT"]
        elif "delete" in route_str:
            return ["DELETE"]
        elif "patch" in route_str:
            return ["PATCH"]

        return ["GET"]  # Default fallback

    def _get_route_name(self, route: Route) -> str | None:
        """Extract name from route."""
        return getattr(route, "name", None)

    def _extract_tags(self, route: Route) -> list[str]:
        """Extract tags for the route."""
        tags = []

        # Try to get tags from route metadata
        if hasattr(route, "tags"):
            route_tags = route.tags
            if isinstance(route_tags, str):
                tags.append(route_tags)
            elif isinstance(route_tags, (list, tuple)):
                tags.extend(route_tags)

        # Extract tags from path segments (e.g., /api/users -> 'users')
        path = self._get_route_path(route)
        path_segments = [
            seg for seg in path.split("/") if seg and not seg.startswith("{")
        ]

        if path_segments:
            # Use the first non-parameter segment as a tag
            primary_segment = path_segments[0]
            if primary_segment not in ["api", "v1", "v2", "v3"]:  # Skip common prefixes
                tags.append(primary_segment.title())

        return tags

    def _extract_middleware(self, route: Route) -> list[str]:
        """Extract middleware information from route."""
        middleware = []

        if hasattr(route, "middleware"):
            route_middleware = route.middleware
            if isinstance(route_middleware, (list, tuple)):
                middleware.extend([str(m) for m in route_middleware])
            elif route_middleware:
                middleware.append(str(route_middleware))

        return middleware

    def _is_internal_route(self, route: Route) -> bool:
        """Check if route is internal/system route."""
        path = self._get_route_path(route)

        # Common patterns for internal routes
        internal_patterns = [
            r"^/_",  # Routes starting with underscore
            r"^/internal",
            r"^/system",
            r"^/health",
            r"^/metrics",
            r"^/debug",
        ]

        for pattern in internal_patterns:
            if re.match(pattern, path, re.IGNORECASE):
                return True

        return False

    def analyze_routes(self, routes: list[Route]) -> list[RouteInfo]:
        """
        Analyze multiple routes.

        Args:
            routes: List of routes to analyze

        Returns:
            List of RouteInfo objects for included routes
        """
        route_infos = []

        for route in routes:
            route_info = self.analyze_route(route)
            if route_info:
                route_infos.append(route_info)

        return route_infos
