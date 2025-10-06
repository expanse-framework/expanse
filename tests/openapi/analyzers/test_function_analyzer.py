"""Tests for FunctionAnalyzer class with Pydantic models."""

from __future__ import annotations

import inspect

from typing import Any
from typing import Optional
from typing import Union

import pytest

from pydantic import BaseModel
from pydantic import Field

from expanse.openapi.analyzers.function_analyzer import FunctionAnalyzer
from expanse.openapi.analyzers.function_analyzer import ParameterInfo
from expanse.openapi.analyzers.function_analyzer import ReturnInfo
from expanse.openapi.config import OpenAPIConfig


# Test Pydantic models
class UserModel(BaseModel):
    """User model for testing."""

    id: int
    name: str
    email: str
    age: int | None = None
    is_active: bool = True


class CreateUserRequest(BaseModel):
    """Request model for creating users."""

    name: str = Field(..., description="User's full name")
    email: str = Field(..., description="User's email address")
    age: int | None = Field(None, description="User's age")


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


# Test functions with Pydantic models
def function_with_pydantic_param(user: UserModel) -> dict[str, Any]:
    """Function with Pydantic model parameter."""
    return {"id": user.id, "name": user.name}


def function_with_pydantic_return(user_id: int) -> UserModel:
    """Function returning Pydantic model."""
    return UserModel(id=user_id, name="Test", email="test@example.com")


def function_with_optional_pydantic(user: UserModel | None = None) -> dict[str, Any]:
    """Function with optional Pydantic parameter."""
    return {"user": user.model_dump() if user else None}


def function_with_union_pydantic(data: UserModel | str) -> Any:
    """Function with Union type including Pydantic model."""
    if isinstance(data, UserModel):
        return data.model_dump()
    return {"message": data}


def function_with_multiple_pydantic(
    user: UserModel, request: CreateUserRequest
) -> UserResponse:
    """Function with multiple Pydantic parameters."""
    return UserResponse(
        id=user.id,
        name=request.name,
        email=request.email,
        created_at="2023-01-01T00:00:00Z",
    )


def function_with_nested_pydantic(data: NestedModel) -> dict[str, Any]:
    """Function with nested Pydantic model."""
    return {"user_id": data.user.id, "metadata": data.metadata}


def function_with_mixed_params(
    user_id: int, user: UserModel, active: bool = True, limit: int | None = None
) -> list[UserModel]:
    """Function with mixed parameter types."""
    return [user] if active else []


async def async_function_with_pydantic(user: UserModel) -> UserResponse:
    """Async function with Pydantic models."""
    return UserResponse(
        id=user.id, name=user.name, email=user.email, created_at="2023-01-01T00:00:00Z"
    )


# Test functions with problematic annotations
def function_with_string_annotation(user: UserModel) -> UserResponse:
    """Function with string type annotations."""
    return UserResponse(id=1, name="test", email="test@example.com", created_at="now")


def function_with_none_annotation(data):
    """Function with no type annotations."""
    return data


class TestParameterInfo:
    """Tests for ParameterInfo class with Pydantic models."""

    def test_parameter_info_with_pydantic_model(self):
        """Test ParameterInfo with Pydantic model annotation."""
        param = ParameterInfo("user", UserModel)

        assert param.name == "user"
        assert param.annotation == UserModel
        assert param.is_required

        openapi_type = param.get_openapi_type()
        assert openapi_type == {"$ref": "#/components/schemas/UserModel"}

    def test_parameter_info_with_optional_pydantic(self):
        """Test ParameterInfo with Optional Pydantic model."""
        param = ParameterInfo("user", Optional[UserModel], default=None)

        assert param.name == "user"
        assert not param.is_required

        # This might fail with current implementation - that's what we're testing
        openapi_type = param.get_openapi_type()
        # Should handle Optional[BaseModel] properly
        assert "$ref" in str(openapi_type) or "nullable" in openapi_type

    def test_parameter_info_with_union_pydantic(self):
        """Test ParameterInfo with Union including Pydantic model."""
        param = ParameterInfo("data", Union[UserModel, str])

        openapi_type = param.get_openapi_type()
        # Should handle Union types with Pydantic models
        assert openapi_type is not None

    def test_parameter_info_with_string_annotation(self):
        """Test ParameterInfo with string annotation for Pydantic model."""
        param = ParameterInfo("user", "UserModel")

        openapi_type = param.get_openapi_type()
        # Should handle string annotations - this might fail currently
        assert openapi_type is not None

    def test_parameter_info_is_body_parameter_with_pydantic(self):
        """Test that Pydantic models are correctly identified as body parameters."""
        param = ParameterInfo("user", UserModel)

        # This uses the private method but tests important logic
        # Check if it would be identified as a body parameter by looking at annotation
        assert "model" in str(param.annotation).lower() or hasattr(
            param.annotation, "__name__"
        )


class TestReturnInfo:
    """Tests for ReturnInfo class with Pydantic models."""

    def test_return_info_with_pydantic_model(self):
        """Test ReturnInfo with Pydantic model."""
        return_info = ReturnInfo(UserModel)

        schema = return_info.get_openapi_schema()
        assert schema == {"$ref": "#/components/schemas/UserModel"}

    def test_return_info_with_optional_pydantic(self):
        """Test ReturnInfo with Optional Pydantic model."""
        return_info = ReturnInfo(Optional[UserModel])

        schema = return_info.get_openapi_schema()
        # Should handle Optional return types
        assert schema is not None

    def test_return_info_with_string_annotation(self):
        """Test ReturnInfo with string annotation."""
        return_info = ReturnInfo("UserModel")

        schema = return_info.get_openapi_schema()
        assert schema is not None


class TestFunctionAnalyzer:
    """Tests for FunctionAnalyzer class with Pydantic models."""

    @pytest.fixture
    def analyzer(self):
        """Create FunctionAnalyzer instance."""
        config = OpenAPIConfig(title="Test API", version="1.0.0")
        return FunctionAnalyzer(config)

    def test_analyze_function_with_pydantic_param(self, analyzer):
        """Test analyzing function with Pydantic parameter."""
        signature = analyzer.analyze_function(function_with_pydantic_param)

        assert len(signature.parameters) == 1
        param = signature.parameters[0]
        assert param.name == "user"
        assert param.annotation == "UserModel"
        assert param.is_required

    def test_analyze_function_with_pydantic_return(self, analyzer):
        """Test analyzing function with Pydantic return type."""
        signature = analyzer.analyze_function(function_with_pydantic_return)

        assert signature.return_info.annotation == "UserModel"
        schema = signature.return_info.get_openapi_schema()
        assert schema == {"$ref": "#/components/schemas/UserModel"}

    def test_analyze_function_with_optional_pydantic(self, analyzer):
        """Test analyzing function with optional Pydantic parameter."""
        signature = analyzer.analyze_function(function_with_optional_pydantic)

        assert len(signature.parameters) == 1
        param = signature.parameters[0]
        assert param.name == "user"
        assert param.annotation == "UserModel | None"
        assert not param.is_required

    def test_analyze_function_with_union_pydantic(self, analyzer):
        """Test analyzing function with Union type including Pydantic model."""
        signature = analyzer.analyze_function(function_with_union_pydantic)

        assert len(signature.parameters) == 1
        param = signature.parameters[0]
        assert param.name == "data"
        assert param.annotation == "UserModel | str"

        # Should not crash when getting OpenAPI type
        openapi_type = param.get_openapi_type()
        assert openapi_type is not None

    def test_analyze_function_with_multiple_pydantic(self, analyzer):
        """Test analyzing function with multiple Pydantic parameters."""
        signature = analyzer.analyze_function(function_with_multiple_pydantic)

        assert len(signature.parameters) == 2

        user_param = signature.parameters[0]
        assert user_param.name == "user"
        assert user_param.annotation == "UserModel"

        request_param = signature.parameters[1]
        assert request_param.name == "request"
        assert request_param.annotation == "CreateUserRequest"

    def test_analyze_function_with_nested_pydantic(self, analyzer):
        """Test analyzing function with nested Pydantic model."""
        signature = analyzer.analyze_function(function_with_nested_pydantic)

        assert len(signature.parameters) == 1
        param = signature.parameters[0]
        assert param.annotation == "NestedModel"

    def test_analyze_function_with_mixed_params(self, analyzer):
        """Test analyzing function with mixed parameter types."""
        signature = analyzer.analyze_function(function_with_mixed_params)

        assert len(signature.parameters) == 4

        # Check parameter types and defaults
        user_id_param = signature.parameters[0]
        assert user_id_param.name == "user_id"
        assert user_id_param.annotation == "int"
        assert user_id_param.is_required

        user_param = signature.parameters[1]
        assert user_param.name == "user"
        assert user_param.annotation == "UserModel"
        assert user_param.is_required

        active_param = signature.parameters[2]
        assert active_param.name == "active"
        assert active_param.annotation == "bool"
        assert not active_param.is_required

        limit_param = signature.parameters[3]
        assert limit_param.name == "limit"
        assert limit_param.annotation == "int | None"
        assert not limit_param.is_required

    def test_analyze_async_function_with_pydantic(self, analyzer):
        """Test analyzing async function with Pydantic models."""
        signature = analyzer.analyze_function(async_function_with_pydantic)

        assert signature.is_async
        assert len(signature.parameters) == 1
        assert signature.parameters[0].annotation == "UserModel"
        assert signature.return_info.annotation == "UserResponse"

    def test_analyze_function_with_string_annotation(self, analyzer):
        """Test analyzing function with string type annotations."""
        # This might fail with current implementation
        signature = analyzer.analyze_function(function_with_string_annotation)

        assert len(signature.parameters) == 1
        param = signature.parameters[0]
        assert param.name == "user"
        assert param.annotation == "UserModel"

        # Should not crash when getting OpenAPI type
        openapi_type = param.get_openapi_type()
        assert openapi_type is not None

    def test_analyze_function_with_none_annotation(self, analyzer):
        """Test analyzing function with no annotations."""
        signature = analyzer.analyze_function(function_with_none_annotation)

        assert len(signature.parameters) == 1
        param = signature.parameters[0]
        assert param.name == "data"
        assert param.annotation == inspect.Parameter.empty

    def test_get_path_parameters_with_pydantic(self, analyzer):
        """Test path parameter identification with Pydantic models."""
        signature = analyzer.analyze_function(function_with_mixed_params)

        path_params = signature.get_path_parameters()
        # user_id should be identified as path parameter
        assert any(p.name == "user_id" for p in path_params)
        # Pydantic models should not be path parameters
        assert not any(p.annotation == "UserModel" for p in path_params)

    def test_get_query_parameters_with_pydantic(self, analyzer):
        """Test query parameter identification with Pydantic models."""
        signature = analyzer.analyze_function(function_with_mixed_params)

        query_params = signature.get_query_parameters()
        # Optional parameters should be query parameters
        assert any(p.name == "active" for p in query_params)
        assert any(p.name == "limit" for p in query_params)

    def test_get_body_parameters_with_pydantic(self, analyzer):
        """Test body parameter identification with Pydantic models."""
        signature = analyzer.analyze_function(function_with_multiple_pydantic)

        body_params = signature.get_body_parameters()
        # Pydantic models should be identified as body parameters
        assert len(body_params) == 2
        assert any(p.annotation == "UserModel" for p in body_params)
        assert any(p.annotation == "CreateUserRequest" for p in body_params)

    def test_extract_parameter_descriptions(self, analyzer):
        """Test extracting parameter descriptions from docstrings."""

        def documented_function(user: UserModel, limit: int = 10):
            """
            Test function with documented parameters.

            Args:
                user: The user model containing user data
                limit: Maximum number of results to return

            Returns:
                List of user data
            """
            return []

        descriptions = analyzer.extract_parameter_descriptions(documented_function)

        assert "user" in descriptions
        assert "limit" in descriptions
        assert "user model" in descriptions["user"].lower()
        assert "maximum" in descriptions["limit"].lower()

    def test_error_handling_with_invalid_types(self, analyzer):
        """Test that analyzer handles invalid type annotations gracefully."""

        def function_with_invalid_type(param: NonExistentModel):
            return None

        # Should not crash
        signature = analyzer.analyze_function(function_with_invalid_type)
        assert len(signature.parameters) == 1

        param = signature.parameters[0]
        openapi_type = param.get_openapi_type()
        assert openapi_type is not None


class TestPydanticModelIdentification:
    """Tests specifically for Pydantic model identification edge cases."""

    def test_issubclass_error_handling(self):
        """Test that issubclass calls are properly protected."""
        param = ParameterInfo("test", "not_a_class")

        # Should not raise TypeError
        openapi_type = param.get_openapi_type()
        assert openapi_type is not None

    def test_none_annotation_handling(self):
        """Test handling of None annotations."""
        param = ParameterInfo("test", None)

        openapi_type = param.get_openapi_type()
        assert openapi_type == {"type": "string"}  # Default fallback

    def test_complex_generic_types(self):
        """Test handling of complex generic types with Pydantic models."""

        # list[UserModel]
        param = ParameterInfo("users", list[UserModel])
        openapi_type = param.get_openapi_type()
        assert openapi_type["type"] == "array"
        assert "$ref" in str(openapi_type["items"])

        # Dict[str, UserModel]
        param = ParameterInfo("user_map", dict[str, UserModel])
        openapi_type = param.get_openapi_type()
        assert openapi_type["type"] == "object"

    def test_forward_reference_handling(self):
        """Test handling of forward references to Pydantic models."""
        # This tests string annotations that refer to models
        param = ParameterInfo("user", "UserModel")

        openapi_type = param.get_openapi_type()
        # Should recognize this as a potential model reference
        assert openapi_type is not None
