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

    def set_description(self, description: str) -> Header:
        self.description = description
        return self

    def set_required(self, required: bool) -> Header:
        self.required = required
        return self

    def set_deprecated(self, deprecated: bool) -> Header:
        self.deprecated = deprecated
        return self

    def set_allow_empty_value(self, allow_empty_value: bool) -> Header:
        self.allow_empty_value = allow_empty_value
        return self

    def set_schema(self, schema: Schema) -> Header:
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
    ) -> Header:
        self.style = style
        return self

    def set_explode(self, explode: bool) -> Header:
        self.explode = explode
        return self

    def set_allow_reserved(self, allow_reserved: bool) -> Header:
        self.allow_reserved = allow_reserved
        return self

    def set_example(self, example: Any) -> Header:
        self.example = example
        return self

    def add_example(self, name: str, example: Example | Reference) -> Header:
        self.examples[name] = example
        return self

    def add_content(self, media_type: str, content: MediaType) -> Header:
        self.content[media_type] = content
        return self

    def to_dict(self) -> dict[str, Any]:
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
