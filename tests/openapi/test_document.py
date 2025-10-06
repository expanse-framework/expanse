"""Tests for OpenAPI document classes."""

from __future__ import annotations

import json

import pytest

from expanse.openapi.config import OpenAPIConfig
from expanse.openapi.document import OpenAPIDocument
from expanse.openapi.document import Operation
from expanse.openapi.document import PathItem


def test_openapi_document_basic_initialization(openapi_config):
    """Test basic OpenAPIDocument initialization."""
    doc = OpenAPIDocument(openapi_config)

    assert doc.config == openapi_config
    assert doc.paths == {}
    assert doc.components["schemas"] == {}
    assert doc.components["securitySchemes"] == {}
    assert doc.tags == []
    assert doc.external_docs is None


def test_openapi_document_initialization_with_config_data():
    """Test initialization with configuration containing data."""
    config = OpenAPIConfig(
        title="Advanced API",
        version="2.0.0",
        security_schemes={"bearerAuth": {"type": "http", "scheme": "bearer"}},
        tags=[{"name": "users", "description": "User operations"}],
    )
    doc = OpenAPIDocument(config)

    assert doc.components["securitySchemes"] == {
        "bearerAuth": {"type": "http", "scheme": "bearer"}
    }
    assert doc.tags == [{"name": "users", "description": "User operations"}]


def test_add_path(openapi_config):
    """Test adding paths to the document."""
    doc = OpenAPIDocument(openapi_config)

    operation = {
        "operationId": "getUser",
        "responses": {"200": {"description": "Success"}},
    }

    doc.add_path("/users/{id}", "get", operation)

    assert "/users/{id}" in doc.paths
    assert doc.paths["/users/{id}"]["get"] == operation


def test_add_multiple_methods_to_same_path(openapi_config):
    """Test adding multiple HTTP methods to the same path."""
    doc = OpenAPIDocument(openapi_config)

    get_operation = {
        "operationId": "getUser",
        "responses": {"200": {"description": "Get user"}},
    }
    post_operation = {
        "operationId": "updateUser",
        "responses": {"200": {"description": "Update user"}},
    }

    doc.add_path("/users/{id}", "get", get_operation)
    doc.add_path("/users/{id}", "post", post_operation)

    assert doc.paths["/users/{id}"]["get"] == get_operation
    assert doc.paths["/users/{id}"]["post"] == post_operation


def test_add_schema(openapi_config):
    """Test adding schemas to components."""
    doc = OpenAPIDocument(openapi_config)

    user_schema = {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
    }

    doc.add_schema("User", user_schema)

    assert doc.components["schemas"]["User"] == user_schema


def test_add_response(openapi_config):
    """Test adding responses to components."""
    doc = OpenAPIDocument(openapi_config)

    error_response = {
        "description": "Error response",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                }
            }
        },
    }

    doc.add_response("ErrorResponse", error_response)

    assert doc.components["responses"]["ErrorResponse"] == error_response


def test_add_parameter(openapi_config):
    """Test adding parameters to components."""
    doc = OpenAPIDocument(openapi_config)

    limit_param = {
        "name": "limit",
        "in": "query",
        "schema": {"type": "integer", "minimum": 1, "maximum": 100},
    }

    doc.add_parameter("LimitParam", limit_param)

    assert doc.components["parameters"]["LimitParam"] == limit_param


def test_add_request_body(openapi_config):
    """Test adding request bodies to components."""
    doc = OpenAPIDocument(openapi_config)

    user_request_body = {
        "description": "User data",
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/User"}}
        },
    }

    doc.add_request_body("UserRequestBody", user_request_body)

    assert doc.components["requestBodies"]["UserRequestBody"] == user_request_body


def test_add_tag_new(openapi_config):
    """Test adding a new tag."""
    doc = OpenAPIDocument(openapi_config)

    doc.add_tag("users", "User management operations")

    assert {
        "name": "users",
        "description": "User management operations",
    } in doc.tags


def test_add_tag_without_description(openapi_config):
    """Test adding a tag without description."""
    doc = OpenAPIDocument(openapi_config)

    doc.add_tag("users")

    assert {"name": "users"} in doc.tags


def test_add_tag_duplicate(openapi_config):
    """Test that duplicate tags are not added."""
    doc = OpenAPIDocument(openapi_config)

    doc.add_tag("users", "User operations")
    doc.add_tag("users", "Different description")

    # Should only have one tag
    user_tags = [tag for tag in doc.tags if tag["name"] == "users"]
    assert len(user_tags) == 1
    assert user_tags[0]["description"] == "User operations"


def test_to_dict_minimal(openapi_config):
    """Test converting minimal document to dictionary."""
    doc = OpenAPIDocument(openapi_config)

    result = doc.to_dict()

    expected = {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }

    assert result == expected


def test_to_dict_full():
    """Test converting full document to dictionary."""
    config = OpenAPIConfig(
        title="Full API",
        version="2.1.0",
        openapi_version="3.0.3",
        description="A comprehensive API",
        contact={"name": "Support", "email": "support@example.com"},
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        terms_of_service="https://example.com/terms",
        servers=[{"url": "https://api.example.com", "description": "Production"}],
    )
    doc = OpenAPIDocument(config)

    # Add some content
    doc.add_path(
        "/users",
        "get",
        {
            "operationId": "listUsers",
            "responses": {"200": {"description": "Success"}},
        },
    )
    doc.add_schema(
        "User", {"type": "object", "properties": {"id": {"type": "integer"}}}
    )
    doc.add_tag("users", "User operations")

    result = doc.to_dict()

    assert result["openapi"] == "3.0.3"
    assert result["info"]["title"] == "Full API"
    assert result["info"]["version"] == "2.1.0"
    assert result["info"]["description"] == "A comprehensive API"
    assert result["info"]["contact"] == {
        "name": "Support",
        "email": "support@example.com",
    }
    assert result["info"]["license"] == {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
    assert result["info"]["termsOfService"] == "https://example.com/terms"
    assert result["servers"] == [
        {"url": "https://api.example.com", "description": "Production"}
    ]
    assert result["tags"] == [{"name": "users", "description": "User operations"}]
    assert result["paths"] == {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "responses": {"200": {"description": "Success"}},
            }
        }
    }
    assert result["components"]["schemas"]["User"] == {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
    }


def test_to_dict_empty_components_excluded(openapi_config):
    """Test that empty component sections are excluded from output."""
    doc = OpenAPIDocument(openapi_config)

    # Add only a schema
    doc.add_schema("User", {"type": "object"})

    result = doc.to_dict()

    # Should only have schemas in components
    assert "components" in result
    assert "schemas" in result["components"]
    assert "responses" not in result["components"]
    assert "parameters" not in result["components"]


def test_to_json(openapi_config):
    """Test converting document to JSON string."""
    doc = OpenAPIDocument(openapi_config)

    json_str = doc.to_json()
    parsed = json.loads(json_str)

    assert parsed["info"]["title"] == "Test API"
    assert parsed["info"]["version"] == "1.0.0"


def test_to_json_with_custom_indent(openapi_config):
    """Test JSON conversion with custom indentation."""
    doc = OpenAPIDocument(openapi_config)

    json_str = doc.to_json(indent=4)

    # Check that it's properly indented
    assert "    " in json_str  # 4-space indent
    assert json.loads(json_str)["info"]["title"] == "Test API"


def test_to_json_compact(openapi_config):
    """Test compact JSON conversion."""
    doc = OpenAPIDocument(openapi_config)

    json_str = doc.to_json(indent=None)

    # Should be compact (no extra whitespace)
    assert "\n" not in json_str
    assert json.loads(json_str)["info"]["title"] == "Test API"


def test_to_yaml_success(openapi_config, mocker):
    """Test successful YAML conversion."""
    mock_yaml_dump = mocker.patch("yaml.dump")
    mock_yaml_dump.return_value = "openapi: 3.1.0\ninfo:\n  title: Test API"

    doc = OpenAPIDocument(openapi_config)

    result = doc.to_yaml()

    assert result == "openapi: 3.1.0\ninfo:\n  title: Test API"
    mock_yaml_dump.assert_called_once()


def test_to_yaml_import_error(openapi_config, mocker):
    """Test YAML conversion when PyYAML is not available."""
    mocker.patch.dict("sys.modules", {"yaml": None})
    doc = OpenAPIDocument(openapi_config)

    with pytest.raises(ImportError, match="PyYAML is required"):
        doc.to_yaml()


# PathItem tests


def test_path_item_initialization():
    """Test PathItem initialization."""
    path_item = PathItem("/users/{id}")

    assert path_item.path == "/users/{id}"
    assert path_item.operations == {}
    assert path_item.parameters == []
    assert path_item.summary is None
    assert path_item.description is None


def test_path_item_add_operation():
    """Test adding operations to path item."""
    path_item = PathItem("/users/{id}")
    operation = Operation("GET", "/users/{id}")

    path_item.add_operation("get", operation)

    assert "get" in path_item.operations
    assert path_item.operations["get"] == operation


def test_path_item_to_dict_minimal():
    """Test converting minimal path item to dictionary."""
    path_item = PathItem("/users")

    result = path_item.to_dict()

    assert result == {}


def test_path_item_to_dict_with_operations():
    """Test converting path item with operations to dictionary."""
    path_item = PathItem("/users")
    operation = Operation("GET", "/users")
    operation.summary = "List users"

    path_item.add_operation("get", operation)

    result = path_item.to_dict()

    assert "get" in result
    assert result["get"]["summary"] == "List users"


def test_path_item_to_dict_with_metadata():
    """Test converting path item with metadata to dictionary."""
    path_item = PathItem("/users")
    path_item.summary = "User operations"
    path_item.description = "Operations for managing users"
    path_item.parameters = [
        {
            "name": "version",
            "in": "header",
            "required": False,
            "schema": {"type": "string"},
        }
    ]

    result = path_item.to_dict()

    assert result["summary"] == "User operations"
    assert result["description"] == "Operations for managing users"
    assert result["parameters"] == [
        {
            "name": "version",
            "in": "header",
            "required": False,
            "schema": {"type": "string"},
        }
    ]


# Operation tests


def test_operation_basic_initialization():
    """Test basic Operation initialization."""
    operation = Operation("GET", "/users/{id}")

    assert operation.method == "GET"
    assert operation.path == "/users/{id}"
    assert operation.operation_id.startswith("get_")
    assert operation.summary is None
    assert operation.description is None
    assert operation.tags == []
    assert operation.parameters == []
    assert operation.request_body is None
    assert operation.responses == {}
    assert operation.security == []
    assert operation.deprecated is False


def test_operation_initialization_with_operation_id():
    """Test Operation initialization with custom operation ID."""
    operation = Operation("POST", "/users", operation_id="createUser")

    assert operation.operation_id == "createUser"


def test_operation_method_case_normalization():
    """Test that HTTP method is normalized to uppercase."""
    operation = Operation("post", "/users")

    assert operation.method == "POST"


def test_operation_add_parameter():
    """Test adding parameters to operation."""
    operation = Operation("GET", "/users/{id}")

    operation.add_parameter(
        name="id",
        param_in="path",
        schema={"type": "integer"},
        required=True,
        description="User ID",
    )

    assert len(operation.parameters) == 1
    param = operation.parameters[0]
    assert param["name"] == "id"
    assert param["in"] == "path"
    assert param["required"] is True
    assert param["schema"] == {"type": "integer"}
    assert param["description"] == "User ID"


def test_operation_add_parameter_without_description():
    """Test adding parameter without description."""
    operation = Operation("GET", "/users")

    operation.add_parameter(
        name="limit",
        param_in="query",
        schema={"type": "integer"},
        required=False,
    )

    param = operation.parameters[0]
    assert "description" not in param


def test_operation_add_response():
    """Test adding responses to operation."""
    operation = Operation("GET", "/users/{id}")

    content = {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}
    headers = {
        "X-Rate-Limit": {
            "description": "Rate limit remaining",
            "schema": {"type": "integer"},
        }
    }

    operation.add_response(
        status_code="200",
        description="User found",
        content=content,
        headers=headers,
    )

    assert "200" in operation.responses
    response = operation.responses["200"]
    assert response["description"] == "User found"
    assert response["content"] == content
    assert response["headers"] == headers


def test_operation_add_response_minimal():
    """Test adding minimal response."""
    operation = Operation("GET", "/users/{id}")

    operation.add_response("404", "User not found")

    response = operation.responses["404"]
    assert response["description"] == "User not found"
    assert "content" not in response
    assert "headers" not in response


def test_operation_add_response_integer_status_code():
    """Test adding response with integer status code."""
    operation = Operation("GET", "/users/{id}")

    operation.add_response(200, "Success")

    assert "200" in operation.responses


def test_operation_set_request_body():
    """Test setting request body."""
    operation = Operation("POST", "/users")

    content = {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/CreateUserRequest"}
        }
    }

    operation.set_request_body(
        content=content,
        description="User creation data",
        required=True,
    )

    assert operation.request_body is not None
    assert operation.request_body["content"] == content
    assert operation.request_body["description"] == "User creation data"
    assert operation.request_body["required"] is True


def test_operation_set_request_body_minimal():
    """Test setting minimal request body."""
    operation = Operation("POST", "/users")

    content = {"application/json": {"schema": {"type": "object"}}}

    operation.set_request_body(content=content)

    assert operation.request_body["content"] == content
    assert operation.request_body["required"] is True
    assert "description" not in operation.request_body


def test_operation_to_dict_minimal():
    """Test converting minimal operation to dictionary."""
    operation = Operation("GET", "/users")

    result = operation.to_dict()

    expected = {
        "operationId": operation.operation_id,
        "responses": {"200": {"description": "Success"}},
    }

    assert result == expected


def test_operation_to_dict_full():
    """Test converting full operation to dictionary."""
    operation = Operation("POST", "/users", operation_id="createUser")
    operation.summary = "Create user"
    operation.description = "Create a new user account"
    operation.tags = ["users"]
    operation.deprecated = True

    operation.add_parameter(
        "version", "header", {"type": "string"}, False, "API version"
    )
    operation.set_request_body(
        {"application/json": {"schema": {"type": "object"}}}, "User data", True
    )
    operation.add_response(
        "201",
        "User created",
        {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}},
    )
    operation.security = [{"bearerAuth": []}]

    result = operation.to_dict()

    assert result["operationId"] == "createUser"
    assert result["summary"] == "Create user"
    assert result["description"] == "Create a new user account"
    assert result["tags"] == ["users"]
    assert result["deprecated"] is True
    assert len(result["parameters"]) == 1
    assert result["requestBody"]["description"] == "User data"
    assert "201" in result["responses"]
    assert result["security"] == [{"bearerAuth": []}]


def test_operation_id_generation():
    """Test automatic operation ID generation."""
    test_cases = [
        ("GET", "/users", "get_users"),
        ("POST", "/users/{id}", "post_users_id"),
        (
            "DELETE",
            "/api/v1/posts/{post_id}/comments/{comment_id}",
            "delete_api_v1_posts_post_id_comments_comment_id",
        ),
        ("PUT", "/", "put_"),
    ]

    for method, path, expected_prefix in test_cases:
        operation = Operation(method, path)
        assert operation.operation_id.startswith(expected_prefix.rstrip("_"))


def test_operation_empty_responses_get_default():
    """Test that operations with no responses get a default 200 response."""
    operation = Operation("GET", "/users")
    # Don't add any responses

    result = operation.to_dict()

    assert result["responses"] == {"200": {"description": "Success"}}
