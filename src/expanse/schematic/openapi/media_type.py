from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.example import Example
    from expanse.schematic.openapi.header import Header
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.schema import Schema


class Encoding:
    """
    A single encoding definition applied to a single schema property.
    """

    def __init__(self, content_type: str | None = None) -> None:
        """
        Initialize an Encoding object.

        Args:
            content_type: The Content-Type for encoding a specific property.
                         Default value depends on the property type.
        """
        self.content_type: str | None = content_type
        self.headers: dict[str, Header | Reference] = {}
        self.style: str | None = None
        self.explode: bool | None = None
        self.allow_reserved: bool = False

    def set_style(self, style: str) -> Encoding:
        """
        Set how a specific property value will be serialized.

        Args:
            style: The serialization style (form, simple, etc.)

        Returns:
            Self for method chaining
        """
        self.style = style
        return self

    def set_explode(self, explode: bool) -> Encoding:
        """
        Set whether property values of type array or object generate separate parameters.

        Args:
            explode: Whether to explode array/object values

        Returns:
            Self for method chaining
        """
        self.explode = explode
        return self

    def set_allow_reserved(self, allow_reserved: bool) -> Encoding:
        """
        Set whether reserved characters should be allowed without percent-encoding.

        Args:
            allow_reserved: Whether to allow reserved characters

        Returns:
            Self for method chaining
        """
        self.allow_reserved = allow_reserved
        return self

    def add_header(self, name: str, header: Header | Reference) -> Encoding:
        """
        Add a header to the encoding.

        Args:
            name: The header name
            header: The header definition or reference

        Returns:
            Self for method chaining
        """
        self.headers[name] = header
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Encoding object to a dictionary representation."""
        result: dict[str, Any] = {}

        if self.content_type is not None:
            result["contentType"] = self.content_type

        if self.headers:
            result["headers"] = {
                name: header.to_dict() for name, header in self.headers.items()
            }

        if self.style is not None:
            result["style"] = self.style

        if self.explode is not None:
            result["explode"] = self.explode

        if self.allow_reserved:
            result["allowReserved"] = self.allow_reserved

        return result

    def __repr__(self) -> str:
        return f"Encoding(content_type='{self.content_type}')"


class MediaType:
    """
    Each Media Type Object provides schema and examples for the media type identified by its key.
    """

    def __init__(self, schema: Schema | None = None) -> None:
        """
        Initialize a MediaType object.

        Args:
            schema: The schema defining the content of the request, response, or parameter.
        """
        self.schema: Schema | None = schema
        self.example: Any = None
        self.examples: dict[str, Example | Reference] = {}
        self.encoding: dict[str, Encoding] = {}

    def set_schema(self, schema: Schema) -> MediaType:
        """
        Set the schema for this media type.

        Args:
            schema: The schema defining the content

        Returns:
            Self for method chaining
        """
        self.schema = schema
        return self

    def set_example(self, example: Any) -> MediaType:
        """
        Set an example of the media type.

        Args:
            example: Example of the media type. The example object SHOULD be in the
                    correct format as specified by the media type.

        Returns:
            Self for method chaining
        """
        self.example = example
        return self

    def add_example(self, name: str, example: Example | Reference) -> MediaType:
        """
        Add a named example of the media type.

        Args:
            name: The example name
            example: The example object or reference

        Returns:
            Self for method chaining
        """
        self.examples[name] = example
        return self

    def add_encoding(self, property_name: str, encoding: Encoding) -> MediaType:
        """
        Add encoding information for a property.

        Args:
            property_name: The property name (must exist in the schema)
            encoding: The encoding definition

        Returns:
            Self for method chaining
        """
        self.encoding[property_name] = encoding
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the MediaType object to a dictionary representation."""
        result: dict[str, Any] = {}

        if self.schema is not None:
            result["schema"] = self.schema.to_dict()

        if self.example is not None:
            result["example"] = self.example

        if self.examples:
            result["examples"] = {
                name: example.to_dict() for name, example in self.examples.items()
            }

        if self.encoding:
            result["encoding"] = {
                name: encoding.to_dict() for name, encoding in self.encoding.items()
            }

        return result

    def __repr__(self) -> str:
        return f"MediaType(schema={self.schema})"
