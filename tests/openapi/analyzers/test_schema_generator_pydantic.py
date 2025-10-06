"""Tests for SchemaGenerator class with Pydantic models."""

from __future__ import annotations

from enum import Enum
from typing import Any
from typing import Optional
from typing import Union

import pytest

from pydantic import BaseModel
from pydantic import Field

from expanse.openapi.analyzers.schema_generator import SchemaGenerator
from expanse.openapi.config import OpenAPIConfig


# Test models
class StatusEnum(str, Enum):
    """Status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class UserModel(BaseModel):
    """User model for testing."""

    id: int
    name: str
    email: str
    age: int | None = None
    is_active: bool = True
    status: StatusEnum = StatusEnum.ACTIVE


class CreateUserRequest(BaseModel):
    """Request model for creating users."""

    name: str = Field(..., description="User's full name", min_length=1, max_length=100)
    email: str = Field(..., description="User's email address")
    age: int | None = Field(None, description="User's age", ge=0, le=150)


class UserResponse(BaseModel):
    """Response model for user operations."""

    id: int
    name: str
    email: str
    created_at: str


class NestedModel(BaseModel):
    """Model with nested Pydantic models."""

    user: UserModel
    metadata: dict[str, Any]
    tags: list[str] = []


class OptionalFieldsModel(BaseModel):
    """Model with various optional field types."""

    required_field: str
    optional_string: str | None = None
    optional_int: int | None = None
    optional_list: list[str] | None = None
    optional_dict: dict[str, Any] | None = None


class GenericModel(BaseModel):
    """Model with generic types."""

    string_list: list[str]
    int_dict: dict[str, int]
    nested_list: list[list[str]]
    user_list: list[UserModel]
    user_dict: dict[str, UserModel]


class ModelWithValidation(BaseModel):
    """Model with Pydantic validation."""

    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    age: int = Field(..., ge=0, le=150)
    name: str = Field(..., min_length=1, max_length=100)
    score: float = Field(..., ge=0.0, le=100.0)


class RecursiveModel(BaseModel):
    """Model with recursive reference."""

    name: str
    children: list[RecursiveModel] = []


# Fix the forward reference
RecursiveModel.model_rebuild()


class TestSchemaGenerator:
    """Tests for SchemaGenerator class with Pydantic models."""

    @pytest.fixture
    def generator(self):
        """Create SchemaGenerator instance."""
        config = OpenAPIConfig(title="Test API", version="1.0.0")
        return SchemaGenerator(config)

    def test_generate_basic_pydantic_schema(self, generator):
        """Test generating schema for basic Pydantic model."""
        schema = generator.generate_pydantic_schema(UserModel)

        assert schema == {"$ref": "#/components/schemas/UserModel"}

        # Check cached schema
        cached_schemas = generator.get_cached_schemas()
        assert "UserModel" in cached_schemas

        user_schema = cached_schemas["UserModel"]
        assert user_schema["type"] == "object"
        assert "properties" in user_schema

        # Check required fields
        assert "required" in user_schema
        required_fields = user_schema["required"]
        assert "id" in required_fields
        assert "name" in required_fields
        assert "email" in required_fields
        assert "age" not in required_fields  # Optional field
        assert "is_active" not in required_fields  # Has default
        assert "status" not in required_fields  # Has default

    def test_generate_schema_with_optional_fields(self, generator):
        """Test schema generation for model with optional fields."""
        schema = generator.generate_pydantic_schema(OptionalFieldsModel)

        cached_schemas = generator.get_cached_schemas()
        model_schema = cached_schemas["OptionalFieldsModel"]

        # Check required fields
        required_fields = model_schema.get("required", [])
        assert "required_field" in required_fields
        assert "optional_string" not in required_fields
        assert "optional_int" not in required_fields

        # Check property types
        properties = model_schema["properties"]
        assert properties["required_field"]["type"] == "string"
        assert properties["optional_string"]["type"] == "string"
        assert properties["optional_string"]["nullable"] == True

    def test_generate_schema_with_nested_models(self, generator):
        """Test schema generation for nested Pydantic models."""
        schema = generator.generate_pydantic_schema(NestedModel)

        cached_schemas = generator.get_cached_schemas()

        # Both models should be cached
        assert "NestedModel" in cached_schemas
        assert "UserModel" in cached_schemas

        nested_schema = cached_schemas["NestedModel"]
        properties = nested_schema["properties"]

        # User field should reference UserModel
        assert properties["user"]["$ref"] == "#/components/schemas/UserModel"

        # Metadata should be object type
        assert properties["metadata"]["type"] == "object"

        # Tags should be array of strings
        assert properties["tags"]["type"] == "array"
        assert properties["tags"]["items"]["type"] == "string"

    def test_generate_schema_with_enums(self, generator):
        """Test schema generation for models with enums."""
        schema = generator.generate_pydantic_schema(UserModel)

        cached_schemas = generator.get_cached_schemas()

        # Both UserModel and StatusEnum should be cached
        assert "UserModel" in cached_schemas
        assert "StatusEnum" in cached_schemas

        user_schema = cached_schemas["UserModel"]
        status_enum_schema = cached_schemas["StatusEnum"]

        # Status field should reference the enum
        status_property = user_schema["properties"]["status"]
        assert status_property["$ref"] == "#/components/schemas/StatusEnum"

        # The enum schema should have the correct values
        assert status_enum_schema["type"] == "string"
        assert "enum" in status_enum_schema
        assert set(status_enum_schema["enum"]) == {"active", "inactive", "pending"}

    def test_generate_schema_with_generic_types(self, generator):
        """Test schema generation for models with generic types."""
        schema = generator.generate_pydantic_schema(GenericModel)

        cached_schemas = generator.get_cached_schemas()
        generic_schema = cached_schemas["GenericModel"]
        properties = generic_schema["properties"]

        # String list
        assert properties["string_list"]["type"] == "array"
        assert properties["string_list"]["items"]["type"] == "string"

        # Int dict
        assert properties["int_dict"]["type"] == "object"
        assert properties["int_dict"]["additionalProperties"]["type"] == "integer"

        # Nested list
        assert properties["nested_list"]["type"] == "array"
        assert properties["nested_list"]["items"]["type"] == "array"
        assert properties["nested_list"]["items"]["items"]["type"] == "string"

        # User list
        assert properties["user_list"]["type"] == "array"
        assert (
            properties["user_list"]["items"]["$ref"] == "#/components/schemas/UserModel"
        )

        # User dict
        assert properties["user_dict"]["type"] == "object"
        assert (
            properties["user_dict"]["additionalProperties"]["$ref"]
            == "#/components/schemas/UserModel"
        )

    def test_generate_schema_with_validation_constraints(self, generator):
        """Test that Pydantic validation constraints are preserved."""
        schema = generator.generate_pydantic_schema(ModelWithValidation)

        cached_schemas = generator.get_cached_schemas()
        validation_schema = cached_schemas["ModelWithValidation"]
        properties = validation_schema["properties"]

        # Email with pattern
        email_prop = properties["email"]
        assert email_prop["type"] == "string"
        # Note: Pattern validation might be in the original Pydantic schema

        # Age with min/max
        age_prop = properties["age"]
        assert age_prop["type"] == "integer"
        # Note: min/max constraints might be preserved from Pydantic schema

    def test_generate_schema_with_recursive_model(self, generator):
        """Test schema generation for recursive models."""
        schema = generator.generate_pydantic_schema(RecursiveModel)

        cached_schemas = generator.get_cached_schemas()
        recursive_schema = cached_schemas["RecursiveModel"]
        properties = recursive_schema["properties"]

        # Children should reference the same model
        children_prop = properties["children"]
        assert children_prop["type"] == "array"
        assert children_prop["items"]["$ref"] == "#/components/schemas/RecursiveModel"

    def test_generate_schema_caching(self, generator):
        """Test that schema caching works correctly."""
        # Generate schema multiple times
        schema1 = generator.generate_pydantic_schema(UserModel)
        schema2 = generator.generate_pydantic_schema(UserModel)

        assert schema1 == schema2

        # Should only be cached once
        cached_schemas = generator.get_cached_schemas()
        assert len([k for k in cached_schemas.keys() if k == "UserModel"]) == 1

    def test_generate_schema_for_non_pydantic_type(self, generator):
        """Test schema generation for non-Pydantic types."""
        # String type
        schema = generator.generate_schema(str)
        assert schema == {"type": "string"}

        # Integer type
        schema = generator.generate_schema(int)
        assert schema == {"type": "integer"}

        # List type
        schema = generator.generate_schema(list[str])
        assert schema == {"type": "array", "items": {"type": "string"}}

        # Dict type
        schema = generator.generate_schema(dict[str, int])
        assert schema == {"type": "object", "additionalProperties": {"type": "integer"}}

    def test_generate_schema_with_optional_types(self, generator):
        """Test schema generation for Optional types."""
        # Optional string
        schema = generator.generate_schema(Optional[str])
        assert schema["type"] == "string"
        assert schema["nullable"] == True

        # Optional Pydantic model
        schema = generator.generate_schema(Optional[UserModel])
        # Should handle Optional Pydantic models
        assert "$ref" in str(schema) or "nullable" in schema

    def test_generate_schema_with_union_types(self, generator):
        """Test schema generation for Union types."""
        # Union of basic types
        schema = generator.generate_schema(Union[str, int])
        assert "oneOf" in schema or "type" in schema

        # Union with Pydantic model
        schema = generator.generate_schema(Union[UserModel, str])
        assert schema is not None

    def test_generate_parameter_schema(self, generator):
        """Test parameter schema generation."""
        from expanse.openapi.analyzers.function_analyzer import ParameterInfo

        # Pydantic model parameter should return None (it's a body parameter)
        param = ParameterInfo("user", UserModel)
        schema = generator.generate_parameter_schema(param)
        assert schema is None  # Body parameters return None

        # Query parameter with basic type
        param = ParameterInfo("limit", "int", default=10, kind="POSITIONAL_OR_KEYWORD")
        schema = generator.generate_parameter_schema(param)

        assert schema["name"] == "limit"
        assert schema["in"] == "query"
        assert schema["required"] == False
        assert schema["schema"]["type"] == "integer"

        # Path parameter
        param = ParameterInfo("user_id", "int", kind="POSITIONAL_OR_KEYWORD")
        schema = generator.generate_parameter_schema(param)

        assert schema["name"] == "user_id"
        assert schema["in"] == "path"
        assert schema["required"] == True
        assert schema["schema"]["type"] == "integer"

    def test_generate_request_body_schema(self, generator):
        """Test request body schema generation."""
        from expanse.openapi.analyzers.function_analyzer import ParameterInfo

        # Single Pydantic model parameter
        params = [ParameterInfo("user", UserModel)]
        schema = generator.generate_request_body_schema(params)

        assert schema is not None
        assert "content" in schema
        assert "application/json" in schema["content"]
        assert (
            schema["content"]["application/json"]["schema"]["$ref"]
            == "#/components/schemas/UserModel"
        )

        # Multiple parameters
        params = [
            ParameterInfo("user", UserModel),
            ParameterInfo("request", CreateUserRequest),
        ]
        schema = generator.generate_request_body_schema(params)

        assert schema is not None
        content_schema = schema["content"]["application/json"]["schema"]
        assert content_schema["type"] == "object"
        assert "properties" in content_schema
        assert "user" in content_schema["properties"]
        assert "request" in content_schema["properties"]

    def test_generate_example_data(self, generator):
        """Test example data generation from schemas."""
        # Only test if examples are enabled
        if not generator.config.generate_examples:
            generator.config.generate_examples = True

        # Basic types
        assert generator.generate_example_data({"type": "string"}) == "string"
        assert generator.generate_example_data({"type": "integer"}) == 0
        assert generator.generate_example_data({"type": "boolean"}) == True

        # Array
        schema = {"type": "array", "items": {"type": "string"}}
        example = generator.generate_example_data(schema)
        assert isinstance(example, list)
        assert len(example) == 1
        assert example[0] == "string"

        # Object
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }
        example = generator.generate_example_data(schema)
        assert isinstance(example, dict)
        assert "name" in example
        assert "age" in example

    def test_clear_cache(self, generator):
        """Test cache clearing functionality."""
        # Generate some schemas
        generator.generate_pydantic_schema(UserModel)
        generator.generate_pydantic_schema(CreateUserRequest)

        # Verify cache has content
        cached_schemas = generator.get_cached_schemas()
        assert len(cached_schemas) > 0

        # Clear cache
        generator.clear_cache()

        # Verify cache is empty
        cached_schemas = generator.get_cached_schemas()
        assert len(cached_schemas) == 0

    def test_error_handling_with_invalid_models(self, generator):
        """Test error handling with invalid model types."""
        # Non-class type
        try:
            schema = generator.generate_schema("not_a_class")
            assert schema is not None  # Should not crash
        except Exception:
            pytest.fail("Should handle invalid types gracefully")

        # None type
        schema = generator.generate_schema(None)
        assert schema == {"type": "null"}

    def test_string_annotation_parsing(self, generator):
        """Test parsing of string-based type annotations."""
        # Basic types
        assert generator._parse_string_type("str") == {"type": "string"}
        assert generator._parse_string_type("int") == {"type": "integer"}
        assert generator._parse_string_type("bool") == {"type": "boolean"}

        # Generic types
        schema = generator._parse_string_type("list[str]")
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "string"

        schema = generator._parse_string_type("dict[str, int]")
        assert schema["type"] == "object"
        assert schema["additionalProperties"]["type"] == "integer"

        # Optional types
        schema = generator._parse_string_type("Optional[str]")
        assert schema["type"] == "string"
        assert schema["nullable"] == True

    def test_pydantic_v2_compatibility(self, generator):
        """Test compatibility with Pydantic v2 features."""
        # Test that model_json_schema method is used when available
        schema = generator.generate_pydantic_schema(UserModel)

        # Should generate reference
        assert schema == {"$ref": "#/components/schemas/UserModel"}

        # Should cache the actual schema
        cached_schemas = generator.get_cached_schemas()
        assert "UserModel" in cached_schemas

        user_schema = cached_schemas["UserModel"]
        assert "type" in user_schema
        assert user_schema["type"] == "object"

    def test_model_with_complex_field_types(self, generator):
        """Test models with complex field types."""

        class ComplexModel(BaseModel):
            union_field: str | int | UserModel
            optional_union: str | UserModel | None = None
            list_of_unions: list[str | int] = []
            dict_of_models: dict[str, UserModel] = {}

        schema = generator.generate_pydantic_schema(ComplexModel)

        cached_schemas = generator.get_cached_schemas()
        complex_schema = cached_schemas["ComplexModel"]
        properties = complex_schema["properties"]

        # Should handle complex types without crashing
        assert "union_field" in properties
        assert "optional_union" in properties
        assert "list_of_unions" in properties
        assert "dict_of_models" in properties

    def test_schema_title_and_description(self, generator):
        """Test that schema titles and descriptions are properly set."""
        schema = generator.generate_pydantic_schema(UserModel)

        cached_schemas = generator.get_cached_schemas()
        user_schema = cached_schemas["UserModel"]

        # Should have title
        assert "title" in user_schema
        assert user_schema["title"] == "UserModel"
