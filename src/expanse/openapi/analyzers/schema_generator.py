from __future__ import annotations

import inspect
import re
import sys

from typing import TYPE_CHECKING
from typing import Any
from typing import Union
from typing import get_args
from typing import get_origin

from pydantic import BaseModel


# Handle UnionType for Python 3.10+
if sys.version_info >= (3, 10):
    import types

    UnionType = types.UnionType
else:
    UnionType = type(None)  # Fallback that will never match


if TYPE_CHECKING:
    from expanse.openapi.config import OpenAPIConfig


class SchemaGenerator:
    """Generates OpenAPI schemas from Python types and Pydantic models."""

    def __init__(self, config: OpenAPIConfig) -> None:
        """Initialize schema generator with configuration."""
        self.config = config
        self._schema_cache: dict[str, dict[str, Any]] = {}
        self._refs: set[str] = set()

    def generate_schema(
        self, python_type: Any, name: str | None = None
    ) -> dict[str, Any]:
        """
        Generate OpenAPI schema from Python type.

        Args:
            python_type: The Python type to convert
            name: Optional name for the schema (used for refs)

        Returns:
            OpenAPI schema dictionary
        """
        if python_type is None or python_type is type(None):
            return {"type": "null"}

        # Basic types
        if python_type is str:
            return {"type": "string"}
        elif python_type is int:
            return {"type": "integer"}
        elif python_type is float:
            return {"type": "number"}
        elif python_type is bool:
            return {"type": "boolean"}

        # Handle generic types
        origin = get_origin(python_type)
        args = get_args(python_type)

        if origin is list:
            items_type = args[0] if args else str
            return {"type": "array", "items": self.generate_schema(items_type)}

        if origin is dict:
            if len(args) >= 2:
                # dict[str, ValueType]
                value_type = args[1]
                return {
                    "type": "object",
                    "additionalProperties": self.generate_schema(value_type),
                }
            return {"type": "object"}

        if origin is tuple:
            if args:
                # Fixed-length tuple
                items = [self.generate_schema(arg) for arg in args]
                return {
                    "type": "array",
                    "items": items,
                    "minItems": len(items),
                    "maxItems": len(items),
                }
            return {"type": "array"}

        # Handle Union types (including Optional) - both typing.Union and types.UnionType
        if origin is Union or (
            sys.version_info >= (3, 10) and isinstance(python_type, UnionType)
        ):
            if args and len(args) == 2 and type(None) in args:
                # This is Optional[T] which is Union[T, None]
                non_none_type = args[0] if args[1] is type(None) else args[1]
                schema = self.generate_schema(non_none_type)
                schema["nullable"] = True
                return schema
            elif args:
                # Multiple types union - use oneOf
                return {"oneOf": [self.generate_schema(arg) for arg in args]}
            return {"type": "null"}

        # Handle None type
        if origin is type(None) or python_type is type(None):
            return {"type": "null"}

        # Handle string annotations
        if isinstance(python_type, str):
            return self._parse_string_type(python_type)

        # Handle Pydantic models and custom classes
        if hasattr(python_type, "__annotations__"):
            return self._generate_model_schema(python_type, name)

        # Handle Enum types
        if hasattr(python_type, "__members__"):
            return self._generate_enum_schema(python_type)

        # Handle Pydantic models with proper type checking
        try:
            if inspect.isclass(python_type) and issubclass(python_type, BaseModel):
                return self.generate_pydantic_schema(python_type)
        except (TypeError, AttributeError):
            # python_type is not a class or doesn't support issubclass
            pass

        # Default fallback
        return {"type": "object"}

    def generate_pydantic_schema(self, model_class: type) -> dict[str, Any]:
        """
        Generate OpenAPI schema from Pydantic model.

        Args:
            model_class: The Pydantic model class

        Returns:
            OpenAPI schema dictionary
        """
        class_name = model_class.__name__

        # Check cache first
        if class_name in self._schema_cache:
            return {"$ref": f"#/components/schemas/{class_name}"}

        # Try to use Pydantic's schema generation if available
        if hasattr(model_class, "model_json_schema"):
            try:
                pydantic_schema = model_class.model_json_schema()
                openapi_schema = self._convert_pydantic_to_openapi(pydantic_schema)

                # Handle recursive models where the top-level schema is just a $ref
                if (
                    isinstance(openapi_schema, dict)
                    and "$ref" in openapi_schema
                    and len(openapi_schema) == 1
                ):
                    # For recursive models, the actual schema should already be cached
                    # from the $defs processing in _convert_pydantic_to_openapi
                    if class_name not in self._schema_cache:
                        # Fallback: use manual generation if schema wasn't cached
                        raise Exception("Schema not found in cache for recursive model")
                else:
                    # Normal case: cache the converted schema
                    self._schema_cache[class_name] = openapi_schema

                self._refs.add(class_name)
                return {"$ref": f"#/components/schemas/{class_name}"}
            except Exception:
                # Fall back to manual generation
                pass

        # Manual schema generation
        schema = self._generate_model_schema(model_class, class_name)
        self._schema_cache[class_name] = schema
        self._refs.add(class_name)
        return {"$ref": f"#/components/schemas/{class_name}"}

    def _generate_model_schema(
        self, model_class: type, name: str | None = None
    ) -> dict[str, Any]:
        """Generate schema for a model class with annotations."""
        schema = {
            "type": "object",
            "properties": {},
        }

        required_fields = []

        # Get type annotations
        annotations = getattr(model_class, "__annotations__", {})

        for field_name, field_type in annotations.items():
            # Skip private fields
            if field_name.startswith("_"):
                continue

            field_schema = self.generate_schema(field_type)
            schema["properties"][field_name] = field_schema

            # Check if field is required - for Pydantic models, we should use the model's field info
            # For now, check if it's Optional or has a default value
            if not self._is_optional_type(field_type):
                # Check if the field has a default value by looking at class attributes
                if not hasattr(model_class, field_name):
                    required_fields.append(field_name)
                else:
                    # If it exists as a class attribute, it might have a default
                    field_value = getattr(
                        model_class, field_name, inspect.Parameter.empty
                    )
                    if field_value is inspect.Parameter.empty or field_value is None:
                        required_fields.append(field_name)

        if required_fields:
            schema["required"] = required_fields

        # Add title if name provided
        if name:
            schema["title"] = name

        return schema

    def _generate_enum_schema(self, enum_class: type) -> dict[str, Any]:
        """Generate schema for Enum types."""
        members = list(enum_class.__members__.values())

        if not members:
            return {"type": "string"}

        # Determine the type based on first member
        first_value = members[0].value

        if isinstance(first_value, str):
            return {"type": "string", "enum": [member.value for member in members]}
        elif isinstance(first_value, int):
            return {"type": "integer", "enum": [member.value for member in members]}
        else:
            return {"enum": [member.value for member in members]}

    def _convert_pydantic_to_openapi(
        self, pydantic_schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert Pydantic JSON schema to OpenAPI schema."""
        # Pydantic schemas need several conversions for OpenAPI compatibility

        # First, extract and process $defs before recursive conversion
        openapi_schema = pydantic_schema.copy()

        # Process $defs first to cache referenced schemas
        if "$defs" in openapi_schema:
            defs = openapi_schema.pop("$defs")
            for def_name, def_schema in defs.items():
                converted_def = self._convert_schema_recursive(def_schema)
                self._schema_cache[def_name] = converted_def
                self._refs.add(def_name)

        # Now convert the main schema
        openapi_schema = self._convert_schema_recursive(openapi_schema)

        return openapi_schema

    def _convert_schema_recursive(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Recursively convert a schema from Pydantic to OpenAPI format."""
        if not isinstance(schema, dict):
            return schema

        converted = {}

        for key, value in schema.items():
            if key == "$ref":
                # Convert $defs references to components/schemas references
                if isinstance(value, str) and value.startswith("#/$defs/"):
                    converted[key] = value.replace("#/$defs/", "#/components/schemas/")
                else:
                    converted[key] = value
            elif key == "anyOf" and isinstance(value, list):
                # Convert Pydantic's anyOf patterns for optional fields
                if len(value) == 2:
                    types = [
                        item.get("type") for item in value if isinstance(item, dict)
                    ]
                    if "null" in types and len(types) == 2:
                        # This is an optional field - convert to nullable
                        non_null_schema = next(
                            item for item in value if item.get("type") != "null"
                        )
                        converted.update(
                            self._convert_schema_recursive(non_null_schema)
                        )
                        converted["nullable"] = True
                        continue
                # Regular anyOf - convert recursively
                converted[key] = [
                    self._convert_schema_recursive(item) for item in value
                ]
            elif key == "properties" and isinstance(value, dict):
                # Recursively convert properties
                converted[key] = {
                    prop_name: self._convert_schema_recursive(prop_schema)
                    for prop_name, prop_schema in value.items()
                }
            elif key in ["items", "additionalProperties"] and isinstance(value, dict):
                # Recursively convert nested schemas
                converted[key] = self._convert_schema_recursive(value)
            elif key == "default":
                # Keep default values but remove from OpenAPI if None
                if value is not None:
                    converted[key] = value
            elif key in ["title", "description"]:
                # Keep title and description
                converted[key] = value
            elif key in [
                "type",
                "enum",
                "format",
                "pattern",
                "minimum",
                "maximum",
                "minLength",
                "maxLength",
                "minItems",
                "maxItems",
                "required",
            ]:
                # Keep standard OpenAPI fields
                converted[key] = value
            # Skip other Pydantic-specific fields

        return converted

    def _parse_string_type(self, type_string: str) -> dict[str, Any]:
        """Parse string-based type annotations."""
        type_string = type_string.strip()

        # Handle basic types
        basic_types = {
            "str": {"type": "string"},
            "string": {"type": "string"},
            "int": {"type": "integer"},
            "integer": {"type": "integer"},
            "float": {"type": "number"},
            "number": {"type": "number"},
            "bool": {"type": "boolean"},
            "boolean": {"type": "boolean"},
        }

        if type_string in basic_types:
            return basic_types[type_string]

        # Handle generic types
        if type_string.startswith("list[") or type_string.startswith("List["):
            inner_type = self._extract_generic_arg(type_string)
            return {
                "type": "array",
                "items": self._parse_string_type(inner_type)
                if inner_type
                else {"type": "string"},
            }

        if type_string.startswith("dict[") or type_string.startswith("Dict["):
            args = self._extract_generic_args(type_string)
            if len(args) >= 2:
                return {
                    "type": "object",
                    "additionalProperties": self._parse_string_type(args[1]),
                }
            return {"type": "object"}

        # Handle Optional types
        if type_string.startswith("Optional["):
            inner_type = self._extract_generic_arg(type_string)
            if inner_type:
                schema = self._parse_string_type(inner_type)
                schema["nullable"] = True
                return schema

        # Handle Union types
        if type_string.startswith("Union["):
            args = self._extract_generic_args(type_string)
            if len(args) == 2 and "None" in args:
                # Optional type
                non_none_type = args[0] if args[1] == "None" else args[1]
                schema = self._parse_string_type(non_none_type)
                schema["nullable"] = True
                return schema
            else:
                # Multiple types
                return {"oneOf": [self._parse_string_type(arg) for arg in args]}

        # Default to object type for unknown classes
        return {"type": "object"}

    def _extract_generic_arg(self, type_string: str) -> str:
        """Extract the inner type from a generic type string."""
        match = re.search(r"\[([^\[\]]+)\]$", type_string)
        return match.group(1) if match else ""

    def _extract_generic_args(self, type_string: str) -> list[str]:
        """Extract all arguments from a generic type string."""
        match = re.search(r"\[(.+)\]$", type_string)
        if not match:
            return []

        args_string = match.group(1)
        # Simple split by comma (doesn't handle nested generics perfectly)
        args = [arg.strip() for arg in args_string.split(",")]
        return args

    def _is_optional_type(self, python_type: Any) -> bool:
        """Check if a type is Optional (Union[X, None])."""
        origin = get_origin(python_type)
        args = get_args(python_type)

        # Handle Union types - both typing.Union and types.UnionType
        if origin is Union or (
            sys.version_info >= (3, 10) and isinstance(python_type, UnionType)
        ):
            return len(args) == 2 and type(None) in args

        # Handle string annotations
        if isinstance(python_type, str):
            return python_type.startswith("Optional[") or " | None" in python_type

        return False

    def generate_parameter_schema(self, param_info) -> dict[str, Any] | None:
        """
        Generate parameter schema for OpenAPI.

        Args:
            param_info: ParameterInfo object from function analyzer

        Returns:
            OpenAPI parameter schema or None if it's a body parameter
        """
        # Determine parameter location first
        if param_info.is_path_parameter():
            location = "path"
            required = True  # Path parameters are always required
        elif param_info.is_query_parameter():
            location = "query"
            required = param_info.is_required
        else:
            # This is likely a request body parameter
            return None

        schema = {
            "name": param_info.name,
            "in": location,
            "required": required,
            "schema": param_info.get_openapi_type(),
        }

        if param_info.description:
            schema["description"] = param_info.description

        return schema

    def generate_request_body_schema(self, body_params) -> dict[str, Any] | None:
        """
        Generate request body schema from body parameters.

        Args:
            body_params: List of parameters that should be in request body

        Returns:
            OpenAPI request body schema or None
        """
        if not body_params:
            return None

        if len(body_params) == 1:
            # Single parameter - use its type directly
            param = body_params[0]
            schema = self._generate_parameter_schema(param)
        else:
            # Multiple parameters - create object schema
            properties = {}
            required = []

            for param in body_params:
                properties[param.name] = self._generate_parameter_schema(param)
                if param.is_required:
                    required.append(param.name)

            schema = {"type": "object", "properties": properties}

            if required:
                schema["required"] = required

        return {
            "content": {"application/json": {"schema": schema}},
            "required": any(param.is_required for param in body_params),
        }

    def get_cached_schemas(self) -> dict[str, dict[str, Any]]:
        """Get all cached schemas for components section."""
        return self._schema_cache.copy()

    def clear_cache(self) -> None:
        """Clear the schema cache."""
        self._schema_cache.clear()
        self._refs.clear()

    def _generate_parameter_schema(self, param) -> dict[str, Any]:
        """
        Generate schema for a parameter, ensuring Pydantic models are cached.

        Args:
            param: ParameterInfo object

        Returns:
            OpenAPI schema for the parameter
        """
        # For Pydantic models, ensure they're properly generated and cached
        annotation = param.annotation

        # Handle Pydantic models directly
        try:
            if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
                self.generate_pydantic_schema(annotation)
                return param.get_openapi_type()
        except (TypeError, AttributeError):
            pass

        # Handle Union types containing Pydantic models
        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            for arg in args:
                if arg is not type(None):  # Skip None in Optional types
                    try:
                        if inspect.isclass(arg) and issubclass(arg, BaseModel):
                            self.generate_pydantic_schema(arg)
                    except (TypeError, AttributeError):
                        pass

        # Handle string annotations that might reference Pydantic models
        if isinstance(annotation, str):
            # Check if it looks like a Pydantic model
            if (
                annotation.endswith("Model")
                or annotation.endswith("Request")
                or annotation.endswith("Response")
                or annotation.endswith("Schema")
            ):
                # Try to resolve the model from the parameter's context
                # This is a best-effort attempt since we don't have direct access
                # to the module context
                pass

            # Handle Union types in string annotations
            if " | " in annotation or annotation.startswith("Union["):
                # Parse union types in string annotations
                if " | " in annotation:
                    parts = [p.strip() for p in annotation.split(" | ")]
                elif annotation.startswith("Union["):
                    inner_start = annotation.find("[") + 1
                    inner_end = annotation.rfind("]")
                    if inner_end > inner_start:
                        parts = [
                            p.strip()
                            for p in annotation[inner_start:inner_end].split(",")
                        ]
                    else:
                        parts = []
                else:
                    parts = []

                # For each part that looks like a Pydantic model, we can't generate
                # the schema without access to the actual class, but the reference
                # will still be created by get_openapi_type()

        return param.get_openapi_type()

    def generate_example_data(self, schema: dict[str, Any]) -> Any:
        """
        Generate example data from OpenAPI schema.

        Args:
            schema: OpenAPI schema dictionary

        Returns:
            Example data matching the schema
        """
        if not self.config.generate_examples:
            return None

        schema_type = schema.get("type")

        if schema_type == "string":
            if "enum" in schema:
                return schema["enum"][0]
            return "string"
        elif schema_type == "integer":
            if "enum" in schema:
                return schema["enum"][0]
            return 0
        elif schema_type == "number":
            if "enum" in schema:
                return schema["enum"][0]
            return 0.0
        elif schema_type == "boolean":
            return True
        elif schema_type == "array":
            items_schema = schema.get("items", {"type": "string"})
            item_example = self.generate_example_data(items_schema)
            return [item_example] if item_example is not None else []
        elif schema_type == "object":
            properties = schema.get("properties", {})
            example = {}
            for prop_name, prop_schema in properties.items():
                prop_example = self.generate_example_data(prop_schema)
                if prop_example is not None:
                    example[prop_name] = prop_example
            return example
        elif schema_type == "null":
            return None

        # Handle refs
        if "$ref" in schema:
            # Can't generate examples for refs without resolving them
            return None

        # Handle oneOf/anyOf
        if schema.get("oneOf"):
            return self.generate_example_data(schema["oneOf"][0])

        return None
