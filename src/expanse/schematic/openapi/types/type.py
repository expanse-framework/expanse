from __future__ import annotations

from typing import Any
from typing import Self


class Type:
    """Base class for OpenAPI type definitions."""

    def __init__(self, name: str) -> None:
        """
        Initialize a Type.

        Args:
            type_name: The JSON Schema type name (string, number, integer, boolean, array, object)
        """
        self.name = name
        self.format: str | None = None
        self.description: str = ""
        self.content_type: str = ""
        self.content_encoding: str = ""
        self.example: Any = None
        self.default: Any = None
        self.examples: list[Any] = []
        self.enum: list[Any] = []
        self.nullable: bool = False

    def set_format(self, format: str) -> Self:
        """Set the format for this type (e.g., 'date-time', 'email', 'uuid')."""
        self.format = format
        return self

    def set_description(self, description: str) -> Self:
        """Set the description for this type."""
        self.description = description
        return self

    def set_nullable(self, nullable: bool) -> Self:
        """Set whether this type can be null."""
        self.nullable = nullable
        return self

    def set_example(self, example: Any) -> Self:
        """Set an example value."""
        self.example = example
        return self

    def set_default(self, default: Any) -> Self:
        """Set a default value."""
        self.default = default
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result: dict[str, Any] = {
            "type": self.name if not self.nullable else [self.name, "null"]
        }

        if self.format:
            result["format"] = self.format
        if self.description:
            result["description"] = self.description
        if self.content_type:
            result["contentType"] = self.content_type
        if self.content_encoding:
            result["contentEncoding"] = self.content_encoding
        if self.example is not None:
            result["example"] = self.example
        if self.default is not None:
            result["default"] = self.default
        if self.examples:
            result["examples"] = self.examples
        if self.enum:
            result["enum"] = self.enum
        if self.nullable:
            result["nullable"] = self.nullable

        return result

    def __repr__(self) -> str:
        return f"Type({self.name})"


class StringType(Type):
    """String type."""

    def __init__(self) -> None:
        super().__init__("string")


class IntegerType(Type):
    """Integer type."""

    def __init__(self) -> None:
        super().__init__("integer")


class NumberType(Type):
    """Number (float) type."""

    def __init__(self) -> None:
        super().__init__("number")


class BooleanType(Type):
    """Boolean type."""

    def __init__(self) -> None:
        super().__init__("boolean")


class ArrayType(Type):
    """Array type."""

    def __init__(self) -> None:
        super().__init__("array")


class ObjectType(Type):
    """Object type."""

    def __init__(self) -> None:
        super().__init__("object")
