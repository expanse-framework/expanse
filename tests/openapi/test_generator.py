"""Tests for OpenAPIGenerator class."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from expanse.openapi.config import OpenAPIConfig
from expanse.openapi.generator import OpenAPIGenerator


# Helper classes for testing


class MockRoute:
    """Mock route for testing."""

    def __init__(
        self,
        path: str,
        methods: list[str],
        endpoint: callable | None = None,
        name: str | None = None,
    ) -> None:
        self.path = path
        self.methods = methods
        self.endpoint = endpoint
        self.name = name or f"{methods[0].lower()}_{path.replace('/', '_')}"


class MockRouter:
    """Mock router for testing."""

    def __init__(self, routes: list[MockRoute] | None = None) -> None:
        self.routes = routes or []


class MockRouteInfo:
    """Mock route info for testing."""

    def __init__(
        self,
        route: MockRoute,
        path: str | None = None,
        methods: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.route = route
        self.path = path or route.path
        self.methods = methods or route.methods
        self.tags = tags or []
        self.path_parameters: list[dict] = []

    def get_openapi_path(self) -> str:
        """Get OpenAPI formatted path."""
        return self.path.replace("<", "{").replace(">", "}")

    def get_operation_id(self, method: str) -> str:
        """Get operation ID for method."""
        return f"{method.lower()}_{self.path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"


class MockSignature:
    """Mock function signature for testing."""

    def __init__(
        self, parameters: list | None = None, return_annotation: type | None = None
    ) -> None:
        self.parameters = parameters or []
        self.return_info = Mock()
        self.return_info.annotation = return_annotation

    def get_query_parameters(self) -> list:
        """Get query parameters."""
        return [p for p in self.parameters if getattr(p, "param_type", None) == "query"]

    def get_body_parameters(self) -> list:
        """Get body parameters."""
        return [p for p in self.parameters if getattr(p, "param_type", None) == "body"]


class MockParameter:
    """Mock function parameter for testing."""

    def __init__(
        self,
        name: str,
        param_type: str = "query",
        is_required: bool = False,
        annotation: type | None = None,
    ) -> None:
        self.name = name
        self.param_type = param_type
        self.is_required = is_required
        self.annotation = annotation

    def get_openapi_type(self) -> dict:
        """Get OpenAPI type definition."""
        if self.annotation == int:
            return {"type": "integer"}
        elif self.annotation == str:
            return {"type": "string"}
        elif self.annotation == bool:
            return {"type": "boolean"}
        else:
            return {"type": "string"}


class MockDocstringInfo:
    """Mock docstring info for testing."""

    def __init__(
        self,
        summary: str | None = None,
        description: str | None = None,
        parameters: dict | None = None,
        returns: str | None = None,
        deprecated: bool = False,
        raises: dict | None = None,
    ) -> None:
        self.summary = summary
        self.description = description
        self.parameters = parameters or {}
        self.returns = returns
        self.deprecated = deprecated
        self.raises = raises or {}


def mock_handler_function() -> dict:
    """Mock handler function for testing."""
    return {"message": "Hello, World!"}


async def mock_async_handler_function() -> dict:
    """Mock async handler function for testing."""
    return {"message": "Hello, Async World!"}


# Test fixtures


@pytest.fixture
def mock_router():
    """Create a mock router for testing."""
    return MockRouter()


@pytest.fixture
def generator(mock_router, openapi_config) -> OpenAPIGenerator:
    """Create an OpenAPI generator for testing."""
    return OpenAPIGenerator(mock_router, openapi_config)


# Tests


def test_initialization(mock_router, openapi_config):
    """Test OpenAPIGenerator initialization."""
    generator = OpenAPIGenerator(mock_router, openapi_config)

    assert generator.router == mock_router
    assert generator.config == openapi_config
    assert generator.route_analyzer is not None
    assert generator.function_analyzer is not None
    assert generator.docstring_parser is not None
    assert generator.code_inference is not None
    assert generator.schema_generator is not None
    assert generator.document is not None


def test_generate_empty_router(generator, mocker):
    """Test generating OpenAPI spec from empty router."""
    mock_analyze = mocker.patch.object(generator.route_analyzer, "analyze_routes")
    mock_analyze.return_value = []

    result = generator.generate()

    assert result["openapi"] == "3.1.0"
    assert result["info"]["title"] == "Test API"
    assert result["info"]["version"] == "1.0.0"
    assert result["paths"] == {}


def test_generate_with_routes(generator, mocker):
    """Test generating OpenAPI spec with routes."""
    # Setup mock route
    route = MockRoute("/users", ["GET"], mock_handler_function)
    route_info = MockRouteInfo(route)

    mock_analyze = mocker.patch.object(generator.route_analyzer, "analyze_routes")
    mock_process = mocker.patch.object(generator, "_process_route")
    mock_analyze.return_value = [route_info]

    generator.generate()

    mock_analyze.assert_called_once()
    mock_process.assert_called_once_with(route_info)


def test_get_route_handler_endpoint(generator):
    """Test extracting handler from route with endpoint attribute."""
    route = Mock()
    route.endpoint = mock_handler_function

    handler = generator._get_route_handler(route)

    assert handler == mock_handler_function


def test_get_route_handler_handler(generator):
    """Test extracting handler from route with handler attribute."""
    route = Mock()
    route.handler = mock_handler_function
    # Remove endpoint attribute
    del route.endpoint

    handler = generator._get_route_handler(route)

    assert handler == mock_handler_function


def test_get_route_handler_callback(generator):
    """Test extracting handler from route with callback attribute."""
    route = Mock()
    route.callback = mock_handler_function
    # Remove endpoint and handler attributes
    del route.endpoint
    del route.handler

    handler = generator._get_route_handler(route)

    assert handler == mock_handler_function


def test_get_route_handler_none(generator):
    """Test extracting handler when no recognized attributes exist."""
    route = Mock()
    # Remove all handler attributes
    del route.endpoint
    del route.handler
    del route.callback

    handler = generator._get_route_handler(route)

    assert handler is None


def test_find_function_parameter_found(generator):
    """Test finding function parameter by name."""
    param = MockParameter("user_id", "path")
    signature = MockSignature([param])

    found = generator._find_function_parameter(signature, "user_id")

    assert found == param


def test_find_function_parameter_not_found(generator):
    """Test finding function parameter when not found."""
    param = MockParameter("user_id", "path")
    signature = MockSignature([param])

    found = generator._find_function_parameter(signature, "post_id")

    assert found is None


def test_get_return_type_schema_with_annotation(generator, mocker):
    """Test getting return type schema with annotation."""
    signature = MockSignature(return_annotation=dict)

    mock_generate = mocker.patch.object(generator.schema_generator, "generate_schema")
    mock_generate.return_value = {"type": "object"}

    schema = generator._get_return_type_schema(signature)

    mock_generate.assert_called_once_with(dict)
    assert schema == {"type": "object"}


def test_get_return_type_schema_no_annotation(generator):
    """Test getting return type schema without annotation."""
    signature = MockSignature(return_annotation=None)

    schema = generator._get_return_type_schema(signature)

    assert schema is None


def test_process_route_no_handler(generator, mocker):
    """Test processing route with no handler function."""
    route = MockRoute("/users", ["GET"])
    route_info = MockRouteInfo(route)

    mock_get_handler = mocker.patch.object(generator, "_get_route_handler")
    mock_get_handler.return_value = None

    # Should not raise an exception
    generator._process_route(route_info)


def test_process_route_with_handler(generator, mocker):
    """Test processing route with handler function."""
    route = MockRoute("/users", ["GET"], mock_handler_function)
    route_info = MockRouteInfo(route, tags=["users"])

    mock_get_handler = mocker.patch.object(generator, "_get_route_handler")
    mock_create_op = mocker.patch.object(generator, "_create_operation")
    mock_add_tag = mocker.patch.object(generator.document, "add_tag")
    mock_add_path = mocker.patch.object(generator.document, "add_path")

    mock_get_handler.return_value = mock_handler_function
    mock_operation = Mock()
    mock_operation.to_dict.return_value = {"operationId": "getUsers"}
    mock_create_op.return_value = mock_operation

    generator._process_route(route_info)

    mock_add_tag.assert_called_once_with("users")
    mock_create_op.assert_called_once_with(route_info, "GET", mock_handler_function)
    mock_add_path.assert_called_once()


def test_create_operation_basic(generator, mocker):
    """Test creating basic operation."""
    route = MockRoute("/users", ["GET"])
    route_info = MockRouteInfo(route)

    mock_analyze = mocker.patch.object(generator.function_analyzer, "analyze_function")
    mock_parse = mocker.patch.object(generator.docstring_parser, "parse_docstring")
    mock_signature = MockSignature()
    mock_docstring = MockDocstringInfo()
    mock_analyze.return_value = mock_signature
    mock_parse.return_value = mock_docstring

    operation = generator._create_operation(route_info, "GET", mock_handler_function)

    assert operation is not None
    assert operation.method == "GET"
    assert operation.path == "/users"


def test_create_operation_with_docstring_info(generator, mocker):
    """Test creating operation with docstring information."""
    route = MockRoute("/users", ["GET"])
    route_info = MockRouteInfo(route)

    mock_analyze = mocker.patch.object(generator.function_analyzer, "analyze_function")
    mock_parse = mocker.patch.object(generator.docstring_parser, "parse_docstring")
    mock_signature = MockSignature()
    mock_docstring = MockDocstringInfo(
        summary="Get users",
        description="Retrieve list of users",
        deprecated=True,
    )
    mock_analyze.return_value = mock_signature
    mock_parse.return_value = mock_docstring

    operation = generator._create_operation(route_info, "GET", mock_handler_function)

    assert operation.summary == "Get users"
    assert operation.description == "Retrieve list of users"
    assert operation.deprecated is True


def test_create_operation_with_tags(generator, mocker):
    """Test creating operation with tags."""
    route = MockRoute("/users", ["GET"])
    route_info = MockRouteInfo(route, tags=["users", "admin"])

    mock_analyze = mocker.patch.object(generator.function_analyzer, "analyze_function")
    mock_parse = mocker.patch.object(generator.docstring_parser, "parse_docstring")
    mock_signature = MockSignature()
    mock_docstring = MockDocstringInfo()
    mock_analyze.return_value = mock_signature
    mock_parse.return_value = mock_docstring

    operation = generator._create_operation(route_info, "GET", mock_handler_function)

    assert operation.tags == ["users", "admin"]


def test_add_parameters_to_operation_path_params(generator):
    """Test adding path parameters to operation."""
    route = MockRoute("/users/{id}", ["GET"])
    route_info = MockRouteInfo(route)
    route_info.path_parameters = [{"name": "id", "schema": {"type": "integer"}}]

    operation = Mock()
    signature = MockSignature([MockParameter("id", "path", True, int)])
    docstring_info = MockDocstringInfo(parameters={"id": "User ID"})

    generator._add_parameters_to_operation(
        operation, route_info, signature, docstring_info
    )

    operation.add_parameter.assert_called_with(
        name="id",
        param_in="path",
        schema={"type": "integer"},
        required=True,
        description="User ID",
    )


def test_add_parameters_to_operation_query_params(generator):
    """Test adding query parameters to operation."""
    route = MockRoute("/users", ["GET"])
    route_info = MockRouteInfo(route)

    operation = Mock()
    query_param = MockParameter("limit", "query", False, int)
    signature = MockSignature([query_param])
    signature.get_query_parameters = Mock(return_value=[query_param])
    docstring_info = MockDocstringInfo(parameters={"limit": "Result limit"})

    generator._add_parameters_to_operation(
        operation, route_info, signature, docstring_info
    )

    operation.add_parameter.assert_called_with(
        name="limit",
        param_in="query",
        schema={"type": "integer"},
        required=False,
        description="Result limit",
    )


def test_add_request_body_to_operation_with_body(generator, mocker):
    """Test adding request body to operation."""
    operation = Mock()
    body_param = MockParameter("user_data", "body", True)
    signature = MockSignature([body_param])
    signature.get_body_parameters = Mock(return_value=[body_param])
    docstring_info = MockDocstringInfo(parameters={"user_data": "User creation data"})

    mock_generate = mocker.patch.object(
        generator.schema_generator, "generate_request_body_schema"
    )
    mock_generate.return_value = {
        "content": {"application/json": {"schema": {"type": "object"}}},
        "required": True,
    }

    generator._add_request_body_to_operation(operation, signature, docstring_info)

    operation.set_request_body.assert_called_with(
        content={"application/json": {"schema": {"type": "object"}}},
        description="User creation data",
        required=True,
    )


def test_add_request_body_to_operation_no_body(generator):
    """Test adding request body when no body parameters exist."""
    operation = Mock()
    signature = MockSignature()
    signature.get_body_parameters = Mock(return_value=[])
    docstring_info = MockDocstringInfo()

    generator._add_request_body_to_operation(operation, signature, docstring_info)

    operation.set_request_body.assert_not_called()


def test_add_responses_to_operation_inferred(generator, mocker):
    """Test adding inferred responses to operation."""
    operation = Mock()
    signature = MockSignature()
    docstring_info = MockDocstringInfo()
    code_patterns = ["return_json"]

    mock_infer = mocker.patch.object(generator.code_inference, "infer_response_schemas")
    mock_extract = mocker.patch.object(
        generator.docstring_parser, "extract_http_status_codes"
    )
    mock_infer.return_value = {"200": {"description": "Success", "content": {}}}
    mock_extract.return_value = {}

    generator._add_responses_to_operation(
        operation, signature, docstring_info, code_patterns
    )

    operation.add_response.assert_called()


def test_add_responses_to_operation_default(generator, mocker):
    """Test adding default response when no responses found."""
    operation = Mock()
    signature = MockSignature()
    docstring_info = MockDocstringInfo()
    code_patterns = []

    mock_infer = mocker.patch.object(generator.code_inference, "infer_response_schemas")
    mock_extract = mocker.patch.object(
        generator.docstring_parser, "extract_http_status_codes"
    )
    mock_get_schema = mocker.patch.object(generator, "_get_return_type_schema")
    mock_infer.return_value = {}
    mock_extract.return_value = {}
    mock_get_schema.return_value = None

    generator._add_responses_to_operation(
        operation, signature, docstring_info, code_patterns
    )

    operation.add_response.assert_called_with("200", "Success")


def test_export_json(generator, mocker, tmp_path):
    """Test exporting OpenAPI spec to JSON file."""
    file_path = tmp_path / "spec.json"

    mock_generate = mocker.patch.object(generator, "generate")
    mock_generate.return_value = {
        "openapi": "3.1.0",
        "info": {"title": "Test", "version": "1.0.0"},
    }

    generator.export_json(str(file_path))

    assert file_path.exists()
    content = file_path.read_text()
    assert "Test" in content


def test_export_json_custom_indent(generator, mocker, tmp_path):
    """Test exporting JSON with custom indentation."""
    file_path = tmp_path / "spec.json"

    mock_generate = mocker.patch.object(generator, "generate")
    mock_generate.return_value = {"openapi": "3.1.0"}

    generator.export_json(str(file_path), indent=4)

    content = file_path.read_text()
    assert "    " in content  # 4-space indent


def test_export_yaml(generator, mocker, tmp_path):
    """Test exporting OpenAPI spec to YAML file."""
    file_path = tmp_path / "spec.yaml"

    mock_yaml_dump = mocker.patch("yaml.dump")
    mock_generate = mocker.patch.object(generator, "generate")
    mock_generate.return_value = {"openapi": "3.1.0"}
    mock_yaml_dump.return_value = "openapi: 3.1.0\n"

    generator.export_yaml(str(file_path))

    assert file_path.exists()
    mock_yaml_dump.assert_called_once()


def test_export_yaml_import_error(generator, mocker):
    """Test YAML export when PyYAML is not available."""
    mocker.patch.dict("sys.modules", {"yaml": None})

    with pytest.raises(ImportError, match="PyYAML is required"):
        generator.export_yaml("spec.yaml")


def test_to_json(generator, mocker):
    """Test converting OpenAPI spec to JSON string."""
    mock_generate = mocker.patch.object(generator, "generate")
    mock_generate.return_value = {"openapi": "3.1.0", "info": {"title": "Test"}}

    result = generator.to_json()

    assert isinstance(result, str)
    assert "Test" in result


def test_to_json_custom_indent(generator, mocker):
    """Test JSON conversion with custom indentation."""
    mock_generate = mocker.patch.object(generator, "generate")
    mock_generate.return_value = {"openapi": "3.1.0"}

    result = generator.to_json(indent=None)

    # Should be compact
    assert "\n" not in result


def test_to_yaml(generator, mocker):
    """Test converting OpenAPI spec to YAML string."""
    mock_to_yaml = mocker.patch.object(generator.document, "to_yaml")
    mock_to_yaml.return_value = "openapi: 3.1.0\n"

    result = generator.to_yaml()

    assert result == "openapi: 3.1.0\n"


def test_generate_caches_schemas(generator, mocker):
    """Test that generated schemas are cached in components."""
    route = MockRoute("/users", ["GET"], mock_handler_function)
    route_info = MockRouteInfo(route)

    mock_analyze = mocker.patch.object(generator.route_analyzer, "analyze_routes")
    mock_cached = mocker.patch.object(generator.schema_generator, "get_cached_schemas")
    mock_add = mocker.patch.object(generator.document, "add_schema")
    mock_analyze.return_value = [route_info]
    mock_cached.return_value = {"User": {"type": "object"}}

    generator.generate()

    mock_add.assert_called_with("User", {"type": "object"})


def test_code_inference_exception_handling(generator, mocker):
    """Test that code inference exceptions are handled gracefully."""
    route = MockRoute("/users", ["GET"], mock_handler_function)
    route_info = MockRouteInfo(route)

    mock_analyze = mocker.patch.object(generator.function_analyzer, "analyze_function")
    mock_parse = mocker.patch.object(generator.docstring_parser, "parse_docstring")
    mock_infer = mocker.patch.object(generator.code_inference, "analyze_function_code")
    mock_signature = MockSignature()
    mock_docstring = MockDocstringInfo()
    mock_analyze.return_value = mock_signature
    mock_parse.return_value = mock_docstring
    mock_infer.side_effect = Exception("Code analysis failed")

    # Should not raise an exception
    operation = generator._create_operation(route_info, "GET", mock_handler_function)

    assert operation is not None


def test_add_custom_analyzer(generator):
    """Test adding custom analyzer (placeholder implementation)."""
    custom_analyzer = Mock()

    # This is a placeholder - the actual implementation would need to be added
    generator.add_custom_analyzer(custom_analyzer)

    # For now, just ensure it doesn't raise an exception
    assert True


def test_add_schema_processor(generator):
    """Test adding schema processor (placeholder implementation)."""
    schema_processor = Mock()

    # This is a placeholder - the actual implementation would need to be added
    generator.add_schema_processor(schema_processor)

    # For now, just ensure it doesn't raise an exception
    assert True


@pytest.mark.parametrize("inference_depth", ["basic", "medium", "deep"])
def test_inference_depth_affects_code_analysis(
    inference_depth: str, mock_router, mocker
):
    """Test that inference depth setting affects code analysis."""
    config = OpenAPIConfig(
        title="Test API", version="1.0.0", inference_depth=inference_depth
    )
    generator = OpenAPIGenerator(mock_router, config)

    route = MockRoute("/users", ["GET"], mock_handler_function)
    route_info = MockRouteInfo(route)

    mock_analyze = mocker.patch.object(generator.function_analyzer, "analyze_function")
    mock_parse = mocker.patch.object(generator.docstring_parser, "parse_docstring")
    mock_infer = mocker.patch.object(generator.code_inference, "analyze_function_code")
    mock_signature = MockSignature()
    mock_docstring = MockDocstringInfo()
    mock_analyze.return_value = mock_signature
    mock_parse.return_value = mock_docstring
    mock_infer.return_value = []

    generator._create_operation(route_info, "GET", mock_handler_function)

    if inference_depth == "basic":
        mock_infer.assert_not_called()
    else:
        mock_infer.assert_called_once()
