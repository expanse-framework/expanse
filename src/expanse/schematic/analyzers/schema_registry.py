from __future__ import annotations

import inspect
import typing

from collections.abc import Sequence
from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Any
from typing import Union
from typing import get_args
from typing import get_origin
from uuid import UUID

from pydantic import BaseModel

from expanse.schematic.openapi.reference import Reference
from expanse.schematic.openapi.schema import Schema
from expanse.schematic.openapi.types import ArrayType
from expanse.schematic.openapi.types import BooleanType
from expanse.schematic.openapi.types import IntegerType
from expanse.schematic.openapi.types import NumberType
from expanse.schematic.openapi.types import ObjectType
from expanse.schematic.openapi.types import StringType


if typing.TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from expanse.schematic.openapi.components import Components


class SchemaRegistry:
    """
    Generates OpenAPI Schema objects from Python type hints and Pydantic models.
    """

    def __init__(self, components: Components) -> None:
        self._components: Components = components

    def generate_from_type(self, type_hint: Any) -> Schema | Reference:
        # None/NoneType
        if type_hint is None or type_hint is type(None):
            return Schema().set_nullable(True)

        # Pydantic models
        if self._is_pydantic_model(type_hint):
            return self.generate_from_pydantic(type_hint)

        # Simple types
        if type_hint in (str, bytes):
            return Schema(StringType())
        elif type_hint is int:
            return Schema(IntegerType())
        elif type_hint is float:
            return Schema(NumberType())
        elif type_hint is bool:
            return Schema(BooleanType())
        elif type_hint is Decimal:
            return Schema(NumberType())
        elif type_hint is UUID:
            return Schema(StringType().set_format("uuid"))
        elif type_hint is datetime:
            return Schema(StringType().set_format("date-time"))
        elif type_hint is date:
            return Schema(StringType().set_format("date"))
        elif type_hint is time:
            return Schema(StringType().set_format("time"))

        # Enums
        if inspect.isclass(type_hint) and issubclass(type_hint, Enum):
            return self._generate_enum_schema(type_hint)

        # Generic types
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        # Handle Optional[T], Union[T, None]
        if origin is Union or origin is UnionType:
            # Check if it's Optional (has None in union)
            non_none_types = [arg for arg in args if arg is not type(None)]
            if len(args) == 2 and len(non_none_types) == 1:
                # It's Optional[T]
                schema = self.generate_from_type(non_none_types[0])
                if isinstance(schema, Schema):
                    schema.set_nullable(True)
                else:
                    # It's a Reference - wrap in Schema to set nullable
                    schema = Schema().add_any_of(schema).add_any_of(Schema(None))

                return schema
            else:
                # It's a union of multiple types - use oneOf
                schema = Schema()
                for arg in non_none_types:
                    schema.add_one_of(self.generate_from_type(arg))
                if len(non_none_types) < len(args):
                    # Has None in union
                    schema.set_nullable(True)
                return schema

        # Handle List[T], list[T]
        if origin in (list, list, Sequence):
            items_type = args[0] if args else Any
            return Schema(ArrayType()).set_items(self.generate_from_type(items_type))

        # Handle Dict[K, V], dict[K, V]
        if origin in (dict, dict):
            value_type = args[1] if len(args) >= 2 else Any
            schema = Schema(ObjectType())
            schema.set_additional_properties(self.generate_from_type(value_type))
            return schema

        # Handle Set[T], set[T]
        if origin in (set, set):
            items_type = args[0] if args else Any
            return (
                Schema(ArrayType())
                .set_items(self.generate_from_type(items_type))
                .set_nullable(False)
            )

        # Tuple - we can treat them as arrays
        if origin in (tuple, tuple):
            # For fixed-length tuples, we could use prefixItems in JSON Schema
            # For now, treat as array
            return Schema(ArrayType())

        if origin is typing.Annotated and len(args) >= 1:
            items_type = args[0]
            if (
                hasattr(items_type, "__tablename__")
                and len(args) >= 2
                and issubclass(args[1], BaseModel)
            ):
                # Annotated SQLAlchemy model
                return self.get_or_create_component_schema(args[1])[0]

        # If we could not determine a more specialized type, return a generic object schema
        return Schema(ObjectType())

    def generate_from_pydantic(self, model: type[BaseModel]) -> Schema:
        raw_schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )

        schema = Schema.from_dict(raw_schema, ObjectType())

        assert isinstance(schema, Schema)

        if "$defs" in raw_schema:
            for def_name, raw_def_schema in raw_schema.get("$defs", {}).items():
                def_schema = Schema.from_dict(raw_def_schema, ObjectType())

                assert isinstance(def_schema, Schema)

                self._components.schemas[def_name] = def_schema

        return schema

    def _generate_field_schema(self, field_info: FieldInfo) -> Schema | Reference:
        return self.generate_from_type(field_info.annotation)

    def _generate_enum_schema(self, enum_class: type[Enum]) -> Schema:
        # Determine the base type of enum values
        enum_values = [e.value for e in enum_class]

        if all(isinstance(v, str) for v in enum_values):
            schema = Schema(StringType())
        elif all(isinstance(v, int) for v in enum_values):
            schema = Schema(IntegerType())
        else:
            schema = Schema(StringType())

        schema.set_enum(enum_values)

        # Add description
        if enum_class.__doc__:
            schema.set_description(enum_class.__doc__.strip())

        return schema

    def _is_pydantic_model(self, type_hint: Any) -> bool:
        try:
            return isinstance(type_hint, type) and issubclass(type_hint, BaseModel)
        except TypeError:
            return False

    def get_or_create_component_schema(
        self, model: type[BaseModel]
    ) -> tuple[Reference, Schema]:
        component_name = model.__name__

        if component_name not in self._components.schemas:
            schema = self.generate_from_pydantic(model)
            self._components.schemas[component_name] = schema
        else:
            schema = self._components.schemas[component_name]

        return Reference(f"#/components/schemas/{component_name}"), schema
