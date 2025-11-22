from expanse.schematic.openapi.schema import Schema
from expanse.schematic.openapi.types import StringType


def test_schema_from_dict_with_basic_type():
    """Test creating a schema from dict with basic type."""
    data = {"type": "string", "description": "A string field"}

    schema = Schema.from_dict(data)

    assert schema.type is not None
    assert schema.type.name == "string"
    assert schema.description == "A string field"


def test_schema_from_dict_with_format():
    """Test creating a schema from dict with format."""
    data = {"type": "string", "format": "uuid", "description": "A UUID field"}

    schema = Schema.from_dict(data)

    assert schema.type is not None
    assert schema.type.name == "string"
    assert schema.type.format == "uuid"
    assert schema.description == "A UUID field"


def test_schema_from_dict_with_nullable_type():
    """Test creating a schema from dict with nullable type."""
    data = {"type": ["string", "null"], "description": "A nullable string"}

    schema = Schema.from_dict(data)

    assert schema.type is not None
    assert schema.type.name == "string"
    assert schema.description == "A nullable string"


def test_schema_from_dict_with_object_properties():
    """Test creating a schema from dict with object properties."""
    data = {
        "type": "object",
        "title": "User",
        "description": "A user object",
        "properties": {
            "name": {"type": "string", "description": "User's name"},
            "age": {"type": "integer", "description": "User's age"},
        },
        "required": ["name"],
    }

    schema = Schema.from_dict(data)

    assert schema.type.name == "object"
    assert schema.title == "User"
    assert schema.description == "A user object"
    assert "name" in schema.properties
    assert "age" in schema.properties
    assert schema.properties["name"].type.name == "string"
    assert schema.properties["age"].type.name == "integer"
    assert schema.required == ["name"]


def test_schema_from_dict_with_array():
    """Test creating a schema from dict with array type."""
    data = {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "maxItems": 10,
    }

    schema = Schema.from_dict(data)

    assert schema.type.name == "array"
    assert schema.items is not None
    assert schema.items.type.name == "string"
    assert schema.min_items == 1
    assert schema.max_items == 10


def test_schema_from_dict_with_string_constraints():
    """Test creating a schema from dict with string constraints."""
    data = {
        "type": "string",
        "minLength": 5,
        "maxLength": 50,
        "pattern": "^[a-z]+$",
    }

    schema = Schema.from_dict(data)

    assert schema.type.name == "string"
    assert schema.min_length == 5
    assert schema.max_length == 50
    assert schema.pattern == "^[a-z]+$"


def test_schema_from_dict_with_number_constraints():
    """Test creating a schema from dict with number constraints."""
    data = {
        "type": "number",
        "minimum": 0,
        "maximum": 100,
        "exclusiveMinimum": True,
        "multipleOf": 5,
    }

    schema = Schema.from_dict(data)

    assert schema.type.name == "number"
    assert schema.minimum == 0
    assert schema.maximum == 100
    assert schema.exclusive_minimum is True
    assert schema.multiple_of == 5


def test_schema_from_dict_with_enum():
    """Test creating a schema from dict with enum values."""
    data = {"type": "string", "enum": ["red", "green", "blue"]}

    schema = Schema.from_dict(data)

    assert schema.type.name == "string"
    assert schema.enum == ["red", "green", "blue"]


def test_schema_from_dict_with_default_and_examples():
    """Test creating a schema from dict with default and examples."""
    data = {
        "type": "string",
        "default": "example",
        "examples": ["example1", "example2"],
    }

    schema = Schema.from_dict(data)

    assert schema.type.name == "string"
    assert schema.default == "example"
    assert schema.examples == ["example1", "example2"]


def test_schema_from_dict_with_all_of():
    """Test creating a schema from dict with allOf composition."""
    data = {
        "allOf": [
            {"type": "object", "properties": {"name": {"type": "string"}}},
            {"type": "object", "properties": {"age": {"type": "integer"}}},
        ]
    }

    schema = Schema.from_dict(data)

    assert len(schema.all_of) == 2
    assert "name" in schema.all_of[0].properties
    assert "age" in schema.all_of[1].properties


def test_schema_from_dict_with_one_of():
    """Test creating a schema from dict with oneOf composition."""
    data = {"oneOf": [{"type": "string"}, {"type": "integer"}]}

    schema = Schema.from_dict(data)

    assert len(schema.one_of) == 2
    assert schema.one_of[0].type.name == "string"
    assert schema.one_of[1].type.name == "integer"


def test_schema_from_dict_with_any_of():
    """Test creating a schema from dict with anyOf composition."""
    data = {"anyOf": [{"type": "string"}, {"type": "integer"}]}

    schema = Schema.from_dict(data)

    assert len(schema.any_of) == 2
    assert schema.any_of[0].type.name == "string"
    assert schema.any_of[1].type.name == "integer"


def test_schema_from_dict_with_not():
    """Test creating a schema from dict with not composition."""
    data = {"not": {"type": "string"}}

    schema = Schema.from_dict(data)

    assert schema.not_ is not None
    assert schema.not_.type.name == "string"


def test_schema_from_dict_with_additional_properties_bool():
    """Test creating a schema from dict with additionalProperties as boolean."""
    data = {"type": "object", "additionalProperties": False}

    schema = Schema.from_dict(data)

    assert schema.additional_properties is False


def test_schema_from_dict_with_additional_properties_schema():
    """Test creating a schema from dict with additionalProperties as schema."""
    data = {
        "type": "object",
        "additionalProperties": {"type": "string"},
    }

    schema = Schema.from_dict(data)

    assert isinstance(schema.additional_properties, Schema)
    assert schema.additional_properties.type.name == "string"


def test_schema_from_dict_with_meta_properties():
    """Test creating a schema from dict with meta properties."""
    data = {
        "type": "string",
        "readOnly": True,
        "writeOnly": False,
        "deprecated": True,
        "nullable": True,
    }

    schema = Schema.from_dict(data)

    assert schema.read_only is True
    assert schema.write_only is False
    assert schema.deprecated is True
    assert schema.nullable is True


def test_schema_from_dict_round_trip():
    """Test that from_dict and to_dict are inverses."""
    original_data = {
        "type": "object",
        "title": "User",
        "description": "A user object",
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "email": {"type": "string", "format": "email"},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
        },
        "required": ["name", "email"],
        "additionalProperties": False,
    }

    schema = Schema.from_dict(original_data)
    result_data = schema.to_dict()

    # Check key fields match
    assert result_data["type"] == original_data["type"]
    assert result_data["title"] == original_data["title"]
    assert result_data["description"] == original_data["description"]
    assert result_data["required"] == original_data["required"]
    assert result_data["additionalProperties"] == original_data["additionalProperties"]
    assert "name" in result_data["properties"]
    assert "email" in result_data["properties"]
    assert "age" in result_data["properties"]


def test_schema_from_dict_with_nested_objects():
    """Test creating a schema from dict with nested objects."""
    data = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                        },
                    },
                },
            }
        },
    }

    schema = Schema.from_dict(data)

    assert "user" in schema.properties
    assert "name" in schema.properties["user"].properties
    assert "address" in schema.properties["user"].properties
    assert "street" in schema.properties["user"].properties["address"].properties
    assert "city" in schema.properties["user"].properties["address"].properties


def test_schema_from_dict_with_provided_type():
    """Test creating a schema from dict with a provided Type object."""
    custom_type = StringType()
    custom_type.set_format("custom")

    data = {"description": "A custom field"}

    schema = Schema.from_dict(data, type=custom_type)

    assert schema.type is custom_type
    assert schema.type.format == "custom"
    assert schema.description == "A custom field"


def test_schema_from_dict_empty():
    """Test creating a schema from an empty dict."""
    data = {}

    schema = Schema.from_dict(data)

    assert schema.type is None
    assert schema.title is None
    assert schema.description is None
    assert len(schema.properties) == 0
