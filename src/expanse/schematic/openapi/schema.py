from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from expanse.schematic.openapi.types import NullType


if TYPE_CHECKING:
    from expanse.schematic.openapi.discriminator import Discriminator
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.tag import ExternalDocumentation
    from expanse.schematic.openapi.types import Type


class Schema:
    def __init__(self, type: Type | None = None) -> None:
        # Core JSON Schema properties
        self.type: Type | None = type
        self.title: str | None = None
        self.description: str | None = None
        self.default: Any = None
        self.examples: list[Any] = []
        self.enum: list[Any] = []

        # Object properties
        self.properties: dict[str, Schema | Reference] = {}
        self.required: list[str] = []
        self.additional_properties: bool | Schema | Reference | None = None
        self.min_properties: int | None = None
        self.max_properties: int | None = None

        # Array properties
        self.items: Schema | Reference | None = None
        self.min_items: int | None = None
        self.max_items: int | None = None
        self.unique_items: bool | None = None

        # String properties
        self.min_length: int | None = None
        self.max_length: int | None = None
        self.pattern: str | None = None

        # Number properties
        self.minimum: float | None = None
        self.maximum: float | None = None
        self.exclusive_minimum: bool | None = None
        self.exclusive_maximum: bool | None = None
        self.multiple_of: float | None = None

        # Composition keywords
        self.all_of: list[Schema | Reference] = []
        self.one_of: list[Schema | Reference] = []
        self.any_of: list[Schema | Reference] = []
        self.not_: Schema | Reference | None = None

        # OpenAPI specific extensions
        self.discriminator: Discriminator | None = None
        self.external_docs: ExternalDocumentation | None = None
        self.example: Any = None  # Deprecated in favor of examples
        self.deprecated: bool = False

        # JSON Schema meta properties
        self.schema: str | None = None
        self.read_only: bool = False
        self.write_only: bool = False
        self.nullable: bool = False

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], type: Type | None = None
    ) -> Schema | Reference:
        from expanse.schematic.openapi.types import ArrayType
        from expanse.schematic.openapi.types import BooleanType
        from expanse.schematic.openapi.types import IntegerType
        from expanse.schematic.openapi.types import NumberType
        from expanse.schematic.openapi.types import ObjectType
        from expanse.schematic.openapi.types import StringType

        # Handle type if not provided
        if type is None and "type" in data:
            type_value = data["type"]
            # Handle nullable types (can be a list like ["string", "null"])
            if isinstance(type_value, list):
                # Take the first non-null type
                type_value = next((t for t in type_value if t != "null"), type_value[0])

            # Create Type object based on type string
            type_map = {
                "string": StringType,
                "integer": IntegerType,
                "number": NumberType,
                "boolean": BooleanType,
                "array": ArrayType,
                "object": ObjectType,
                "null": NullType,
            }
            if type_value in type_map:
                type_obj = type_map[type_value]()

                # Set format if present
                if "format" in data:
                    type_obj.set_format(data["format"])

                type = type_obj

        schema = cls(type)

        # JSON Schema meta properties
        if "$schema" in data:
            schema.schema = data["$schema"]

        if "$ref" in data:
            from expanse.schematic.openapi.reference import Reference

            return Reference(ref=data["$ref"])

        # Core properties
        if "title" in data:
            schema.title = data["title"]

        if "description" in data:
            schema.description = data["description"]

        if "default" in data:
            schema.default = data["default"]

        if "examples" in data:
            schema.examples = data["examples"]

        if "enum" in data:
            schema.enum = data["enum"]

        # Object properties
        if "properties" in data:
            for name, prop_data in data["properties"].items():
                prop_schema = cls.from_dict(prop_data)
                schema.properties[name] = prop_schema

        if "required" in data:
            schema.required = data["required"]

        if "additionalProperties" in data:
            add_props = data["additionalProperties"]
            if isinstance(add_props, bool):
                schema.additional_properties = add_props
            else:
                schema.additional_properties = cls.from_dict(add_props)

        if "minProperties" in data:
            schema.min_properties = data["minProperties"]

        if "maxProperties" in data:
            schema.max_properties = data["maxProperties"]

        # Array properties
        if "items" in data:
            schema.items = cls.from_dict(data["items"])

        if "minItems" in data:
            schema.min_items = data["minItems"]

        if "maxItems" in data:
            schema.max_items = data["maxItems"]

        if "uniqueItems" in data:
            schema.unique_items = data["uniqueItems"]

        # String properties
        if "minLength" in data:
            schema.min_length = data["minLength"]

        if "maxLength" in data:
            schema.max_length = data["maxLength"]

        if "pattern" in data:
            schema.pattern = data["pattern"]

        # Number properties
        if "minimum" in data:
            schema.minimum = data["minimum"]

        if "maximum" in data:
            schema.maximum = data["maximum"]

        if "exclusiveMinimum" in data:
            schema.exclusive_minimum = data["exclusiveMinimum"]

        if "exclusiveMaximum" in data:
            schema.exclusive_maximum = data["exclusiveMaximum"]

        if "multipleOf" in data:
            schema.multiple_of = data["multipleOf"]

        # Composition keywords
        if "allOf" in data:
            schema.all_of = [cls.from_dict(item) for item in data["allOf"]]

        if "oneOf" in data:
            schema.one_of = [cls.from_dict(item) for item in data["oneOf"]]

        if "anyOf" in data:
            any_of = [cls.from_dict(item) for item in data["anyOf"]]
            null = next(
                (
                    item
                    for item in any_of
                    if isinstance(item, Schema) and isinstance(item.type, NullType)
                ),
                None,
            )
            if null is not None:
                any_of.remove(null)
                if len(any_of) == 1:
                    single_schema = any_of[0]
                    if isinstance(single_schema, Schema):
                        schema = single_schema
                    else:
                        schema.any_of = any_of
                else:
                    schema.any_of = any_of

                assert isinstance(schema, Schema)
                schema.set_nullable(True)
            else:
                schema.any_of = any_of

        if "not" in data:
            schema.not_ = cls.from_dict(data["not"])

        # OpenAPI specific extensions
        if "discriminator" in data:
            from expanse.schematic.openapi.discriminator import Discriminator

            schema.discriminator = Discriminator.from_dict(data["discriminator"])

        if "externalDocs" in data:
            from expanse.schematic.openapi.tag import ExternalDocumentation

            schema.external_docs = ExternalDocumentation.from_dict(data["externalDocs"])

        if "example" in data:
            schema.example = data["example"]

        if "deprecated" in data:
            schema.deprecated = data["deprecated"]

        # JSON Schema meta properties
        if "readOnly" in data:
            schema.read_only = data["readOnly"]

        if "writeOnly" in data:
            schema.write_only = data["writeOnly"]

        if "nullable" in data:
            schema.nullable = data["nullable"]

        return schema

    def set_title(self, title: str) -> Schema:
        self.title = title
        return self

    def set_description(self, description: str) -> Schema:
        self.description = description
        return self

    def set_default(self, default: Any) -> Schema:
        self.default = default
        return self

    def add_example(self, example: Any) -> Schema:
        self.examples.append(example)
        return self

    def set_enum(self, values: list[Any]) -> Schema:
        self.enum = values
        return self

    def add_property(self, name: str, schema: Schema, required: bool = False) -> Schema:
        self.properties[name] = schema
        if required:
            self.required.append(name)
        return self

    def set_required(self, required: list[str]) -> Schema:
        self.required = required
        return self

    def set_additional_properties(
        self, additional_properties: bool | Schema | Reference
    ) -> Schema:
        self.additional_properties = additional_properties
        return self

    def set_items(self, items: Schema | Reference) -> Schema:
        self.items = items
        return self

    def set_min_length(self, min_length: int) -> Schema:
        self.min_length = min_length
        return self

    def set_max_length(self, max_length: int) -> Schema:
        self.max_length = max_length
        return self

    def set_pattern(self, pattern: str) -> Schema:
        self.pattern = pattern
        return self

    def set_minimum(self, minimum: float, exclusive: bool = False) -> Schema:
        self.minimum = minimum
        if exclusive:
            self.exclusive_minimum = True
        return self

    def set_maximum(self, maximum: float, exclusive: bool = False) -> Schema:
        self.maximum = maximum
        if exclusive:
            self.exclusive_maximum = True
        return self

    def add_all_of(self, schema: Schema | Reference) -> Schema:
        self.all_of.append(schema)
        return self

    def add_one_of(self, schema: Schema | Reference) -> Schema:
        self.one_of.append(schema)
        return self

    def add_any_of(self, schema: Schema | Reference) -> Schema:
        self.any_of.append(schema)
        return self

    def set_not(self, schema: Schema | Reference) -> Schema:
        self.not_ = schema
        return self

    def set_discriminator(self, discriminator: Discriminator) -> Schema:
        self.discriminator = discriminator
        return self

    def set_external_docs(self, external_docs: ExternalDocumentation) -> Schema:
        self.external_docs = external_docs
        return self

    def set_deprecated(self, deprecated: bool) -> Schema:
        self.deprecated = deprecated
        return self

    def set_read_only(self, read_only: bool) -> Schema:
        self.read_only = read_only
        return self

    def set_write_only(self, write_only: bool) -> Schema:
        self.write_only = write_only
        return self

    def set_nullable(self, nullable: bool) -> Schema:
        self.nullable = nullable
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        # Add JSON Schema meta properties
        if self.schema is not None:
            result["$schema"] = self.schema

        # Add core properties
        if self.type is not None:
            result.update(self.type.to_dict())

        if self.title is not None:
            result["title"] = self.title

        if self.description is not None:
            result["description"] = self.description

        if self.default is not None:
            result["default"] = self.default

        if self.examples:
            result["examples"] = self.examples

        if self.enum:
            result["enum"] = self.enum

        # Object properties
        if self.properties:
            result["properties"] = {
                name: schema.to_dict() for name, schema in self.properties.items()
            }

        if self.required:
            result["required"] = self.required

        if self.additional_properties is not None:
            if isinstance(self.additional_properties, bool):
                result["additionalProperties"] = self.additional_properties
            else:
                result["additionalProperties"] = self.additional_properties.to_dict()

        if self.min_properties is not None:
            result["minProperties"] = self.min_properties

        if self.max_properties is not None:
            result["maxProperties"] = self.max_properties

        # Array properties
        if self.items is not None:
            result["items"] = self.items.to_dict()

        if self.min_items is not None:
            result["minItems"] = self.min_items

        if self.max_items is not None:
            result["maxItems"] = self.max_items

        if self.unique_items is not None:
            result["uniqueItems"] = self.unique_items

        # String properties
        if self.min_length is not None:
            result["minLength"] = self.min_length

        if self.max_length is not None:
            result["maxLength"] = self.max_length

        if self.pattern is not None:
            result["pattern"] = self.pattern

        # Number properties
        if self.minimum is not None:
            result["minimum"] = self.minimum

        if self.maximum is not None:
            result["maximum"] = self.maximum

        if self.exclusive_minimum is not None:
            result["exclusiveMinimum"] = self.exclusive_minimum

        if self.exclusive_maximum is not None:
            result["exclusiveMaximum"] = self.exclusive_maximum

        if self.multiple_of is not None:
            result["multipleOf"] = self.multiple_of

        # Composition keywords
        if self.all_of:
            result["allOf"] = [schema.to_dict() for schema in self.all_of]

        if self.one_of:
            result["oneOf"] = [schema.to_dict() for schema in self.one_of]

        if self.any_of:
            result["anyOf"] = [schema.to_dict() for schema in self.any_of]

        if self.not_ is not None:
            result["not"] = self.not_.to_dict()

        # OpenAPI specific extensions
        if self.discriminator is not None:
            result["discriminator"] = self.discriminator.to_dict()

        if self.external_docs is not None:
            result["externalDocs"] = self.external_docs.to_dict()

        if self.example is not None:
            result["example"] = self.example

        if self.deprecated:
            result["deprecated"] = self.deprecated

        # JSON Schema meta properties
        if self.read_only:
            result["readOnly"] = self.read_only

        if self.write_only:
            result["writeOnly"] = self.write_only

        if self.nullable:
            result["nullable"] = self.nullable

        return result
