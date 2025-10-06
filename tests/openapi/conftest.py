"""Fixtures for OpenAPI tests."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from expanse.openapi.config import OpenAPIConfig
from expanse.openapi.generator import OpenAPIGenerator


@pytest.fixture
def openapi_config() -> OpenAPIConfig:
    """Create a basic OpenAPI configuration for testing."""
    return OpenAPIConfig(title="Test API", version="1.0.0")


@pytest.fixture
def advanced_openapi_config() -> OpenAPIConfig:
    """Create an advanced OpenAPI configuration for testing."""
    return OpenAPIConfig(
        title="Advanced API",
        version="2.1.0",
        openapi_version="3.0.3",
        description="A comprehensive API",
        include_patterns=["/api/**", "/v1/**"],
        exclude_patterns=["/internal/**"],
        docstring_style="google",
        include_internal_routes=True,
        inference_depth="medium",
        generate_examples=False,
        security_schemes={"bearerAuth": {"type": "http", "scheme": "bearer"}},
        servers=[{"url": "https://api.example.com", "description": "Production"}],
        tags=[{"name": "users", "description": "User operations"}],
        contact={"name": "Support", "email": "support@example.com"},
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        terms_of_service="https://example.com/terms",
    )


@pytest.fixture
def mock_router():
    """Create a mock router for testing."""
    router = Mock()
    router.routes = []
    return router


@pytest.fixture
def openapi_generator(mock_router, openapi_config) -> OpenAPIGenerator:
    """Create an OpenAPI generator for testing."""
    return OpenAPIGenerator(mock_router, openapi_config)


@pytest.fixture
def mock_route():
    """Create a mock route for testing."""
    route = Mock()
    route.path = "/users"
    route.methods = ["GET"]
    route.endpoint = Mock()
    route.name = "get_users"
    return route


@pytest.fixture
def mock_route_info(mock_route):
    """Create a mock route info for testing."""
    route_info = Mock()
    route_info.route = mock_route
    route_info.path = mock_route.path
    route_info.methods = mock_route.methods
    route_info.tags = []
    route_info.path_parameters = []
    route_info.get_openapi_path.return_value = mock_route.path
    route_info.get_operation_id.return_value = f"{mock_route.methods[0].lower()}_{mock_route.path.replace('/', '_').strip('_')}"
    return route_info


@pytest.fixture
def mock_signature():
    """Create a mock function signature for testing."""
    signature = Mock()
    signature.parameters = []
    signature.return_info = Mock()
    signature.return_info.annotation = None
    signature.get_query_parameters.return_value = []
    signature.get_body_parameters.return_value = []
    return signature


@pytest.fixture
def mock_parameter():
    """Create a mock function parameter for testing."""
    param = Mock()
    param.name = "test_param"
    param.param_type = "query"
    param.is_required = False
    param.annotation = str
    param.get_openapi_type.return_value = {"type": "string"}
    return param


@pytest.fixture
def mock_docstring_info():
    """Create a mock docstring info for testing."""
    info = Mock()
    info.summary = None
    info.description = None
    info.parameters = {}
    info.returns = None
    info.deprecated = False
    info.raises = {}
    return info


@pytest.fixture
def mock_handler_function():
    """Create a mock handler function for testing."""

    def handler():
        """Mock handler function."""
        return {"message": "Hello, World!"}

    return handler


@pytest.fixture
def mock_async_handler_function():
    """Create a mock async handler function for testing."""

    async def handler():
        """Mock async handler function."""
        return {"message": "Hello, Async World!"}

    return handler
