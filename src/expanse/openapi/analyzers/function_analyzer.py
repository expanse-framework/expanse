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
    from collections.abc import Callable

    from expanse.openapi.config import OpenAPIConfig


class ParameterInfo:
    """Information about a function parameter."""

    def __init__(
        self,
        name: str,
        annotation: type | str | None = None,
        default: Any = inspect.Parameter.empty,
        kind: str = "positional_or_keyword",
        schema_generator=None,
    ) -> None:
        """Initialize parameter information."""
        self.name = name
        self.annotation = annotation
        self.default = default
        self.kind = kind
        self.is_required = default is inspect.Parameter.empty
        self.description: str | None = None
        self.schema_generator = schema_generator

    def is_path_parameter(self) -> bool:
        """Check if this is a path parameter (usually extracted from URL)."""
        # Path parameters are typically positional and have no default
        # but should not be complex types like Pydantic models
        if not (
            self.is_required
            and self.kind
            in [
                "POSITIONAL_ONLY",
                "POSITIONAL_OR_KEYWORD",
            ]
        ):
            return False

        # Exclude Pydantic models and other complex types from path parameters
        if self._is_body_parameter():
            return False

        return True

    def is_query_parameter(self) -> bool:
        """Check if this is a query parameter."""
        # Query parameters often have defaults or are optional
        return not self.is_required or self._is_query_type()

    def _is_query_type(self) -> bool:
        """Check if the type suggests this is a query parameter."""
        if not self.annotation:
            return False

        # Check for common query parameter types
        annotation_str = str(self.annotation).lower()
        return any(
            query_type in annotation_str
            for query_type in ["query", "queryparams", "request.query"]
        )

    def get_openapi_type(self) -> dict[str, Any]:
        """Convert Python type to OpenAPI schema type."""
        if not self.annotation or self.annotation is inspect.Parameter.empty:
            return {"type": "string"}

        return self._python_type_to_openapi(self.annotation)

    def _python_type_to_openapi(self, annotation: Any) -> dict[str, Any]:
        """Convert Python type annotation to OpenAPI schema."""
        if annotation is None or annotation is type(None):
            return {"type": "null"}

        if annotation is str:
            return {"type": "string"}

        if annotation is int:
            return {"type": "integer"}

        if annotation is float:
            return {"type": "number"}

        if annotation is bool:
            return {"type": "boolean"}

        if annotation is list:
            return {"type": "array", "items": {"type": "string"}}

        if annotation is dict:
            return {"type": "object"}

        # Handle generic types
        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin is list:
            items_type = args[0] if args else str
            return {
                "type": "array",
                "items": self._python_type_to_openapi(items_type),
            }

        if origin is dict:
            return {"type": "object"}

        if origin is tuple:
            return {"type": "array"}

        # Handle Union types (including Optional) - both typing.Union and types.UnionType
        if origin is Union or (
            sys.version_info >= (3, 10) and isinstance(annotation, UnionType)
        ):
            if args and len(args) == 2 and type(None) in args:
                # This is Optional[T] which is Union[T, None]
                non_none_type = args[0] if args[1] is type(None) else args[1]
                schema = self._python_type_to_openapi(non_none_type)
                schema["nullable"] = True
                return schema
            elif args:
                # Multiple types union - use oneOf
                return {"oneOf": [self._python_type_to_openapi(arg) for arg in args]}

        # Handle None type
        if origin is type(None) or annotation is type(None):
            return {"type": "null"}

        # Handle string annotations
        if isinstance(annotation, str):
            return self._parse_string_annotation(annotation)

        # Handle custom classes (like Pydantic models)
        try:
            if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
                class_name = annotation.__name__
                # Generate the actual schema if we have a schema generator
                if self.schema_generator:
                    self.schema_generator.generate_pydantic_schema(annotation)
                return {"$ref": f"#/components/schemas/{class_name}"}
        except (TypeError, AttributeError):
            # annotation is not a class or doesn't support issubclass
            pass

        if hasattr(annotation, "__name__"):
            class_name = annotation.__name__
            if "model" in class_name.lower() or "schema" in class_name.lower():
                return {"$ref": f"#/components/schemas/{class_name}"}

        # Default fallback
        return {"type": "string"}

    def _parse_string_annotation(self, annotation: str) -> dict[str, Any]:
        """Parse string-based type annotations."""
        annotation = annotation.strip()

        if annotation in ["str", "string"]:
            return {"type": "string"}
        elif annotation in ["int", "integer"]:
            return {"type": "integer"}
        elif annotation in ["float", "number"]:
            return {"type": "number"}
        elif annotation in ["bool", "boolean"]:
            return {"type": "boolean"}
        elif annotation.startswith("list[") or annotation.startswith("List["):
            # Extract inner type
            inner_start = annotation.find("[") + 1
            inner_end = annotation.rfind("]")
            if inner_end > inner_start:
                inner_type = annotation[inner_start:inner_end].strip()
                return {
                    "type": "array",
                    "items": self._parse_string_annotation(inner_type),
                }
            return {"type": "array", "items": {"type": "string"}}
        elif annotation.startswith("dict[") or annotation.startswith("Dict["):
            return {"type": "object"}
        elif " | " in annotation:
            # Handle Union types written as X | Y
            parts = [part.strip() for part in annotation.split(" | ")]
            if len(parts) == 2 and "None" in parts:
                # Optional type
                non_none_type = parts[0] if parts[1] == "None" else parts[1]
                schema = self._parse_string_annotation(non_none_type)
                schema["nullable"] = True
                return schema
            else:
                # Multiple types union
                return {
                    "oneOf": [self._parse_string_annotation(part) for part in parts]
                }
        elif annotation.startswith("Optional["):
            # Extract inner type from Optional[T]
            inner_start = annotation.find("[") + 1
            inner_end = annotation.rfind("]")
            if inner_end > inner_start:
                inner_type = annotation[inner_start:inner_end].strip()
                schema = self._parse_string_annotation(inner_type)
                schema["nullable"] = True
                return schema
        elif annotation.startswith("Union["):
            # Extract types from Union[T, U, ...]
            inner_start = annotation.find("[") + 1
            inner_end = annotation.rfind("]")
            if inner_end > inner_start:
                inner_types = annotation[inner_start:inner_end].split(",")
                inner_types = [t.strip() for t in inner_types]
                if len(inner_types) == 2 and "None" in inner_types:
                    # Optional type
                    non_none_type = (
                        inner_types[0] if inner_types[1] == "None" else inner_types[1]
                    )
                    schema = self._parse_string_annotation(non_none_type)
                    schema["nullable"] = True
                    return schema
                else:
                    # Multiple types union
                    return {
                        "oneOf": [self._parse_string_annotation(t) for t in inner_types]
                    }

        # Check if this looks like a Pydantic model (ends with Model, contains Model, etc.)
        if (
            annotation.endswith("Model")
            or "Model" in annotation
            or annotation.endswith("Request")
            or annotation.endswith("Response")
            or annotation.endswith("Schema")
        ):
            # Try to generate schema if we have a schema generator and can resolve the class
            if self.schema_generator and hasattr(
                self, "_try_resolve_string_annotation"
            ):
                resolved_class = self._try_resolve_string_annotation(annotation)
                if resolved_class:
                    self.schema_generator.generate_pydantic_schema(resolved_class)
            return {"$ref": f"#/components/schemas/{annotation}"}

        return {"type": "string"}

    def _is_body_parameter(self) -> bool:
        """Check if parameter should be in request body."""
        if not self.annotation:
            return False

        # Check if it's a Pydantic model directly
        try:
            if inspect.isclass(self.annotation) and issubclass(
                self.annotation, BaseModel
            ):
                return True
        except (TypeError, AttributeError):
            pass

        # Handle Union types containing Pydantic models
        origin = get_origin(self.annotation)
        if origin is Union or (
            sys.version_info >= (3, 10) and isinstance(self.annotation, UnionType)
        ):
            args = get_args(self.annotation)
            for arg in args:
                if arg is not type(None):  # Skip None in Optional types
                    try:
                        if inspect.isclass(arg) and issubclass(arg, BaseModel):
                            return True
                    except (TypeError, AttributeError):
                        pass

        annotation_str = str(self.annotation).lower()

        # Check for common request body indicators in string annotations
        if isinstance(self.annotation, str):
            # For string annotations, check if it looks like a Pydantic model
            if (
                self.annotation.endswith("Model")
                or self.annotation.endswith("Request")
                or self.annotation.endswith("Response")
                or self.annotation.endswith("Schema")
                or "model" in annotation_str
            ):
                return True

            # Handle Union types that might contain Pydantic models
            if " | " in self.annotation or self.annotation.startswith("Union["):
                # Parse union types in string annotations
                if " | " in self.annotation:
                    parts = [p.strip() for p in self.annotation.split(" | ")]
                elif self.annotation.startswith("Union["):
                    inner_start = self.annotation.find("[") + 1
                    inner_end = self.annotation.rfind("]")
                    if inner_end > inner_start:
                        parts = [
                            p.strip()
                            for p in self.annotation[inner_start:inner_end].split(",")
                        ]
                    else:
                        parts = []
                else:
                    parts = []

                # Check if any part looks like a Pydantic model
                for part in parts:
                    if part != "None" and (
                        part.endswith("Model")
                        or part.endswith("Request")
                        or part.endswith("Response")
                        or part.endswith("Schema")
                    ):
                        return True

        # Check for common request body indicators
        body_indicators = [
            "model",
            "schema",
            "form",
            "json",
            "basemodel",
            "request.json",
            "request.form",
        ]

        return any(indicator in annotation_str for indicator in body_indicators)


class ReturnInfo:
    """Information about function return type."""

    def __init__(self, annotation: type | str | None = None) -> None:
        """Initialize return information."""
        self.annotation = annotation
        self.description: str | None = None

    def get_openapi_schema(self) -> dict[str, Any]:
        """Get OpenAPI schema for return type."""
        if not self.annotation or self.annotation is inspect.Parameter.empty:
            return {"type": "object"}

        param_info = ParameterInfo("return", self.annotation)
        return param_info.get_openapi_type()


class FunctionSignature:
    """Represents a function signature with analysis."""

    def __init__(
        self,
        func: Callable[..., Any],
        parameters: list[ParameterInfo],
        return_info: ReturnInfo,
    ) -> None:
        """Initialize function signature."""
        self.func = func
        self.parameters = parameters
        self.return_info = return_info
        self.is_async = inspect.iscoroutinefunction(func)

    def get_path_parameters(self) -> list[ParameterInfo]:
        """Get parameters that should be path parameters."""
        return [p for p in self.parameters if p.is_path_parameter()]

    def get_query_parameters(self) -> list[ParameterInfo]:
        """Get parameters that should be query parameters."""
        return [p for p in self.parameters if p.is_query_parameter()]

    def get_body_parameters(self) -> list[ParameterInfo]:
        """Get parameters that should be request body."""
        # Body parameters are typically complex types or explicitly marked
        body_params = []
        for param in self.parameters:
            if param._is_body_parameter():
                body_params.append(param)
        return body_params


class FunctionAnalyzer:
    """Analyzes function signatures to extract OpenAPI information."""

    def __init__(self, config: OpenAPIConfig, schema_generator=None) -> None:
        """Initialize function analyzer."""
        self.config = config
        self.schema_generator = schema_generator

    def analyze_function(self, func: Callable[..., Any]) -> FunctionSignature:
        """
        Analyze a function and extract signature information.

        Args:
            func: The function to analyze

        Returns:
            FunctionSignature with extracted information
        """
        sig = inspect.signature(func)
        parameters = []

        for param_name, param in sig.parameters.items():
            # Skip 'self' and 'cls' parameters
            if param_name in ["self", "cls"]:
                continue

            param_info = ParameterInfo(
                name=param_name,
                annotation=param.annotation,
                default=param.default,
                kind=param.kind.name,
                schema_generator=getattr(self, "schema_generator", None),
            )
            parameters.append(param_info)

        # Analyze return type
        return_info = ReturnInfo(sig.return_annotation)

        return FunctionSignature(func, parameters, return_info)

    def extract_parameter_descriptions(
        self, func: Callable[..., Any], docstring: str | None = None
    ) -> dict[str, str]:
        """
        Extract parameter descriptions from function docstring.

        Args:
            func: The function to analyze
            docstring: Optional docstring (will extract from func if not provided)

        Returns:
            Dictionary mapping parameter names to descriptions
        """
        if not docstring:
            docstring = inspect.getdoc(func)

        if not docstring:
            return {}

        descriptions = {}

        # Simple regex patterns for common docstring formats
        patterns = [
            # Google style: Args: or Parameters:
            r"(?:Args?|Parameters?):\s*\n(.*?)(?:\n\n|\n[A-Z]|\Z)",
            # Sphinx style: :param name: description
            r":param\s+(\w+):\s*([^\n]+)",
            # NumPy style: Parameters section
            r"Parameters\s*\n\s*-+\s*\n(.*?)(?:\n\s*\n|\n[A-Z]|\Z)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, docstring, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 1:
                    # Google/NumPy style - parse the section
                    section = match.group(1)
                    param_descriptions = self._parse_parameter_section(section)
                    descriptions.update(param_descriptions)
                elif len(match.groups()) == 2:
                    # Sphinx style - direct param:description mapping
                    param_name, description = match.groups()
                    descriptions[param_name.strip()] = description.strip()

        return descriptions

    def _parse_parameter_section(self, section: str) -> dict[str, str]:
        """Parse a parameter section from docstring."""
        descriptions = {}

        # Look for parameter definitions like:
        # param_name: description
        # param_name (type): description
        lines = section.split("\n")
        current_param = None
        current_desc = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line starts a new parameter
            param_match = re.match(r"(\w+)(?:\s*\([^)]+\))?\s*:\s*(.*)", line)
            if param_match:
                # Save previous parameter if exists
                if current_param and current_desc:
                    descriptions[current_param] = " ".join(current_desc).strip()

                # Start new parameter
                current_param = param_match.group(1)
                desc_part = param_match.group(2)
                current_desc = [desc_part] if desc_part else []
            elif current_param:
                # Continue description for current parameter
                current_desc.append(line)

        # Save the last parameter
        if current_param and current_desc:
            descriptions[current_param] = " ".join(current_desc).strip()

        return descriptions

    def get_function_name(self, func: Callable[..., Any]) -> str:
        """Get the function name."""
        return getattr(func, "__name__", "unknown")

    def get_function_module(self, func: Callable[..., Any]) -> str | None:
        """Get the function module."""
        return getattr(func, "__module__", None)

    def is_handler_function(self, func: Callable[..., Any]) -> bool:
        """Check if function looks like a route handler."""
        if not callable(func):
            return False

        # Skip built-in functions and methods
        if inspect.isbuiltin(func) or inspect.ismethod(func):
            return False

        # Must be a regular function or coroutine
        return inspect.isfunction(func) or inspect.iscoroutinefunction(func)
