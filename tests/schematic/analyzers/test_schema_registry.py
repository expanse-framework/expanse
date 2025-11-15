from datetime import date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from typing import Any
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Mapped

from expanse.database.orm import column
from expanse.database.orm.model import Model
from expanse.schematic.analyzers.schema_registry import SchemaRegistry
from expanse.schematic.openapi.components import Components
from expanse.schematic.openapi.reference import Reference
from expanse.schematic.openapi.schema import Schema


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class UserModel(BaseModel):
    """A user model."""

    name: str
    email: str
    age: int | None = None


class User(Model):
    __tablename__ = "users"

    __table_args__: ClassVar[dict[str, Any]] = {"extend_existing": True}

    id: Mapped[int] = column(primary_key=True)
    name: Mapped[str] = column(init=True)
    email: Mapped[str] = column(init=True)


def test_schema_generator_handles_basic_types():
    generator = SchemaRegistry(Components())

    # String
    schema = generator.generate_from_type(str)

    assert isinstance(schema, Schema)
    assert schema.type.name == "string"

    # Integer
    schema = generator.generate_from_type(int)
    assert isinstance(schema, Schema)
    assert schema.type.name == "integer"

    # Float
    schema = generator.generate_from_type(float)
    assert isinstance(schema, Schema)
    assert schema.type.name == "number"

    # Boolean
    schema = generator.generate_from_type(bool)
    assert isinstance(schema, Schema)
    assert schema.type.name == "boolean"


def test_schema_generator_handles_special_types():
    generator = SchemaRegistry(Components())

    # UUID
    schema = generator.generate_from_type(UUID)
    assert isinstance(schema, Schema)
    assert schema.type.format == "uuid"

    # DateTime
    schema = generator.generate_from_type(datetime)
    assert isinstance(schema, Schema)
    assert schema.type.format == "date-time"

    # Date
    schema = generator.generate_from_type(date)
    assert isinstance(schema, Schema)
    assert schema.type.format == "date"

    # Decimal
    schema = generator.generate_from_type(Decimal)
    assert isinstance(schema, Schema)
    assert schema.type.name == "number"


def test_schema_generator_handles_optional_types():
    generator = SchemaRegistry(Components())

    schema = generator.generate_from_type(str | None)
    assert isinstance(schema, Schema)
    assert schema.nullable


def test_schema_generator_handles_list_types():
    generator = SchemaRegistry(Components())

    schema = generator.generate_from_type(list[str])
    assert isinstance(schema, Schema)
    assert schema.type.name == "array"
    assert schema.items is not None
    assert isinstance(schema.items, Schema)
    assert schema.items.type.name == "string"


def test_schema_generator_handles_dict_types():
    generator = SchemaRegistry(Components())

    schema = generator.generate_from_type(dict[str, int])
    assert isinstance(schema, Schema)
    assert schema.type.name == "object"
    assert schema.additional_properties is not None


def test_schema_generator_handles_enum_types():
    generator = SchemaRegistry(Components())

    schema = generator.generate_from_type(Color)
    assert isinstance(schema, Schema)
    assert schema.enum == ["red", "green", "blue"]


def test_schema_generator_handles_pydantic_models():
    generator = SchemaRegistry(Components())

    schema = generator.generate_from_type(UserModel)

    assert isinstance(schema, Schema)
    assert schema.type.name == "object"
    assert schema.title == "UserModel"
    assert "name" in schema.properties
    assert "email" in schema.properties
    assert "age" in schema.properties

    assert "name" in schema.required
    assert "email" in schema.required
    assert "age" not in schema.required


def test_schema_generator_extracts_pydantic_field_descriptions():
    class UserWithDocs(BaseModel):
        """A documented user model."""

        name: str
        """The user's name."""

    generator = SchemaRegistry(Components())
    schema = generator.generate_from_type(UserWithDocs)

    assert schema.description == "A documented user model."


def test_schema_generator_handles_nested_pydantic_models():
    """Test that nested Pydantic models are handled correctly."""

    class Address(BaseModel):
        street: str
        city: str

    class UserWithAddress(BaseModel):
        name: str
        address: Address

    components = Components()
    generator = SchemaRegistry(components)
    schema = generator.generate_from_type(UserWithAddress)

    assert isinstance(schema, Schema)
    assert "address" in schema.properties
    assert isinstance(schema.properties["address"], Reference)
    assert "Address" in components.schemas


def test_schema_generator_creates_component_references_for_annotated_models():
    components = Components()
    generator = SchemaRegistry(components)

    generator.generate_from_type(Annotated[User, UserModel])

    assert "UserModel" in components.schemas
    assert components.schemas["UserModel"].title == "UserModel"
