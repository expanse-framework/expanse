from __future__ import annotations

from typing import Any


class OpenAPIConfig:
    """Configuration for OpenAPI specification generation."""

    def __init__(
        self,
        title: str,
        version: str,
        openapi_version: str = "3.1.0",
        description: str | None = None,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        docstring_style: str = "auto",
        include_internal_routes: bool = False,
        inference_depth: str = "deep",
        generate_examples: bool = True,
        security_schemes: dict[str, Any] | None = None,
        servers: list[dict[str, Any]] | None = None,
        tags: list[dict[str, Any]] | None = None,
        contact: dict[str, Any] | None = None,
        license_info: dict[str, Any] | None = None,
        terms_of_service: str | None = None,
    ) -> None:
        """
        Initialize OpenAPI configuration.

        Args:
            title: The title of the API
            version: The version of the API
            openapi_version: OpenAPI specification version to use
            description: A description of the API
            include_patterns: Route patterns to include (glob patterns)
            exclude_patterns: Route patterns to exclude (glob patterns)
            docstring_style: Docstring parsing style (auto, google, sphinx, numpy)
            include_internal_routes: Whether to include internal/system routes
            inference_depth: Level of code inference (basic, medium, deep)
            generate_examples: Whether to generate example request/response data
            security_schemes: Security scheme definitions
            servers: Server information
            tags: Tag definitions for grouping operations
            contact: Contact information
            license_info: License information
            terms_of_service: Terms of service URL
        """
        self.title = title
        self.version = version
        self.openapi_version = openapi_version
        self.description = description
        self.include_patterns = include_patterns or ["**"]
        self.exclude_patterns = exclude_patterns or []
        self.docstring_style = docstring_style
        self.include_internal_routes = include_internal_routes
        self.inference_depth = inference_depth
        self.generate_examples = generate_examples
        self.security_schemes = security_schemes or {}
        self.servers = servers or []
        self.tags = tags or []
        self.contact = contact
        self.license_info = license_info
        self.terms_of_service = terms_of_service

    def should_include_route(self, route_path: str) -> bool:
        """
        Check if a route should be included based on patterns.

        Args:
            route_path: The route path to check

        Returns:
            True if the route should be included
        """
        import fnmatch

        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(route_path, pattern):
                return False

        # Check include patterns
        for pattern in self.include_patterns:
            if fnmatch.fnmatch(route_path, pattern):
                return True

        return False
