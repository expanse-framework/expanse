from datetime import date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from expanse.schematic.analyzers.schema_generator import SchemaGenerator


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class UserModel(BaseModel):
    """A user model."""

    name: str
    email: str
    age: int | None = None


def test_schema_generator_handles_basic_types():
    """Test that basic Python types are converted correctly."""
    generator = SchemaGenerator()

    # String
    schema = generator.generate_from_type(str)
    assert schema.type.type_name == "string"

    # Integer
    schema = generator.generate_from_type(int)
    assert schema.type.type_name == "integer"

    # Float
    schema = generator.generate_from_type(float)
    assert schema.type.type_name == "number"

    # Boolean
    schema = generator.generate_from_type(bool)
    assert schema.type.type_name == "boolean"


def test_schema_generator_handles_special_types():
    """Test that special types have correct formats."""
    generator = SchemaGenerator()

    # UUID
    schema = generator.generate_from_type(UUID)
    assert schema.type.format == "uuid"

    # DateTime
    schema = generator.generate_from_type(datetime)
    assert schema.type.format == "date-time"

    # Date
    schema = generator.generate_from_type(date)
    assert schema.type.format == "date"

    # Decimal
    schema = generator.generate_from_type(Decimal)
    assert schema.type.type_name == "number"


def test_schema_generator_handles_optional_types():
    """Test that Optional types are marked as nullable."""
    generator = SchemaGenerator()

    schema = generator.generate_from_type(Optional[str])
    assert schema.nullable is True


def test_schema_generator_handles_list_types():
    """Test that list types generate array schemas."""
    generator = SchemaGenerator()

    schema = generator.generate_from_type(list[str])
    assert schema.type.type_name == "array"
    assert schema.items is not None
    assert schema.items.type.type_name == "string"


def test_schema_generator_handles_dict_types():
    """Test that dict types generate object schemas."""
    generator = SchemaGenerator()

    schema = generator.generate_from_type(dict[str, int])
    assert schema.type.type_name == "object"
    assert schema.additional_properties is not None


def test_schema_generator_handles_enum_types():
    """Test that Enum types generate schemas with enum values."""
    generator = SchemaGenerator()

    schema = generator.generate_from_type(Color)
    assert schema.enum == ["red", "green", "blue"]


def test_schema_generator_handles_pydantic_models():
    """Test that Pydantic models are converted correctly."""
    generator = SchemaGenerator()

    schema = generator.generate_from_pydantic(UserModel)

    assert schema.type.type_name == "object"
    assert schema.title == "UserModel"
    assert "name" in schema.properties
    assert "email" in schema.properties
    assert "age" in schema.properties

    # Check required fields
    assert "name" in schema.required
    assert "email" in schema.required
    assert "age" not in schema.required  # Optional field


def test_schema_generator_extracts_pydantic_field_descriptions():
    """Test that field descriptions are extracted from Pydantic models."""

    class UserWithDocs(BaseModel):
        """A documented user model."""

        name: str
        """The user's name."""

    generator = SchemaGenerator()
    schema = generator.generate_from_pydantic(UserWithDocs)

    assert schema.description == "A documented user model."


def test_schema_generator_handles_nested_pydantic_models():
    """Test that nested Pydantic models are handled correctly."""

    class Address(BaseModel):
        street: str
        city: str

    class UserWithAddress(BaseModel):
        name: str
        address: Address

    generator = SchemaGenerator()
    schema = generator.generate_from_pydantic(UserWithAddress)

    assert "address" in schema.properties
    assert schema.properties["address"].type.type_name == "object"


def test_schema_generator_creates_component_references():
    """Test that component schema references are created."""
    generator = SchemaGenerator()
    components_schemas = {}

    component_name = generator.get_or_create_component_schema(
        UserModel, components_schemas
    )

    assert component_name == "UserModel"
    assert "UserModel" in components_schemas
    assert components_schemas["UserModel"].title == "UserModel"


def test_schema_generator_reuses_existing_components():
    """Test that existing component schemas are reused."""
    generator = SchemaGenerator()
    components_schemas = {}

    # Create component twice
    name1 = generator.get_or_create_component_schema(UserModel, components_schemas)
    name2 = generator.get_or_create_component_schema(UserModel, components_schemas)

    assert name1 == name2
    assert len(components_schemas) == 1
