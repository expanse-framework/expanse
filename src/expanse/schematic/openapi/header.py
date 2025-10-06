from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Literal


if TYPE_CHECKING:
    from expanse.schematic.openapi.example import Example
    from expanse.schematic.openapi.media_type import MediaType
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.schema import Schema


class Header:
    """
    The Header Object follows the structure of the Parameter Object with the following changes:
    - name MUST NOT be specified, it is given in the corresponding headers map.
    - in MUST NOT be specified, it is implicitly in header.
    - All traits that are affected by the location MUST be applicable to a location of header.
    """

    def __init__(self) -> None:
        """Initialize a Header object."""
        self.description: str = ""
        self.required: bool = False
        self.deprecated: bool = False
        self.allow_empty_value: bool = False
        self.schema: Schema | None = None
        self.style: (
            Literal[
                "simple",
                "form",
                "matrix",
                "label",
                "spaceDelimited",
                "pipeDelimited",
                "deepObject",
            ]
            | None
        ) = None
        self.explode: bool | None = None
        self.allow_reserved: bool = False
        self.example: Any = ...
        self.examples: dict[str, Example | Reference] = {}
        self.content: dict[str, MediaType] = {}

    def set_description(self, description: str) -> "Header":
        """
        Set a brief description of the header.

        Args:
            description: A brief description of the header. This could contain examples of use.
                        CommonMark syntax MAY be used for rich text representation.

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def set_required(self, required: bool) -> "Header":
        """
        Set whether this header is mandatory.

        Args:
            required: Determines whether this header is mandatory.

        Returns:
            Self for method chaining
        """
        self.required = required
        return self

    def set_deprecated(self, deprecated: bool) -> "Header":
        """
        Set whether this header is deprecated.

        Args:
            deprecated: Specifies that a header is deprecated and SHOULD be transitioned out of usage.

        Returns:
            Self for method chaining
        """
        self.deprecated = deprecated
        return self

    def set_allow_empty_value(self, allow_empty_value: bool) -> "Header":
        """
        Set the ability to pass empty-valued headers.

        Args:
            allow_empty_value: Sets the ability to pass empty-valued headers.

        Returns:
            Self for method chaining
        """
        self.allow_empty_value = allow_empty_value
        return self

    def set_schema(self, schema: "Schema") -> "Header":
        """
        Set the schema defining the type used for the header.

        Args:
            schema: The schema defining the type used for the header.

        Returns:
            Self for method chaining
        """
        self.schema = schema
        return self

    def set_style(
        self,
        style: Literal[
            "simple",
            "form",
            "matrix",
            "label",
            "spaceDelimited",
            "pipeDelimited",
            "deepObject",
        ],
    ) -> "Header":
        """
        Set how the header value will be serialized.

        Args:
            style: Describes how the header value will be serialized depending on the type
                  of the header value.

        Returns:
            Self for method chaining
        """
        self.style = style
        return self

    def set_explode(self, explode: bool) -> "Header":
        """
        Set whether header values of type array or object generate separate headers.

        Args:
            explode: When this is true, header values of type array or object generate
                    separate headers for each value of the array or key-value pair of the map.

        Returns:
            Self for method chaining
        """
        self.explode = explode
        return self

    def set_allow_reserved(self, allow_reserved: bool) -> "Header":
        """
        Set whether reserved characters should be allowed.

        Args:
            allow_reserved: Determines whether the header value SHOULD allow reserved characters.

        Returns:
            Self for method chaining
        """
        self.allow_reserved = allow_reserved
        return self

    def set_example(self, example: Any) -> "Header":
        """
        Set an example of the header's potential value.

        Args:
            example: Example of the header's potential value.

        Returns:
            Self for method chaining
        """
        self.example = example
        return self

    def add_example(self, name: str, example: "Example | Reference") -> "Header":
        """
        Add a named example of the header's potential value.

        Args:
            name: The example name
            example: The example object or reference

        Returns:
            Self for method chaining
        """
        self.examples[name] = example
        return self

    def add_content(self, media_type: str, content: "MediaType") -> "Header":
        """
        Add content description for the header.

        Args:
            media_type: The media type
            content: The media type object describing the content

        Returns:
            Self for method chaining
        """
        self.content[media_type] = content
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Header object to a dictionary representation."""
        result: dict[str, Any] = {}

        if self.description:
            result["description"] = self.description

        if self.required:
            result["required"] = self.required

        if self.deprecated:
            result["deprecated"] = self.deprecated

        if self.allow_empty_value:
            result["allowEmptyValue"] = self.allow_empty_value

        if self.schema is not None:
            result["schema"] = self.schema.to_dict()

        if self.style is not None:
            result["style"] = self.style

        if self.explode is not None:
            result["explode"] = self.explode

        if self.allow_reserved:
            result["allowReserved"] = self.allow_reserved

        if self.example is not ...:
            result["example"] = self.example

        if self.examples:
            result["examples"] = {
                name: example.to_dict() for name, example in self.examples.items()
            }

        if self.content:
            result["content"] = {
                media_type: content.to_dict()
                for media_type, content in self.content.items()
            }

        return result

    def __repr__(self) -> str:
        return f"Header(description='{self.description}')"
