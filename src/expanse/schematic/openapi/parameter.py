from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Literal


if TYPE_CHECKING:
    from types import EllipsisType

    from expanse.schematic.openapi.example import Example
    from expanse.schematic.openapi.media_type import MediaType
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.schema import Schema


class Parameter:
    """
    Describes a single operation parameter.

    A unique parameter is defined by a combination of a name and location.
    """

    def __init__(self, name: str, in_: Literal["query", "header", "path", "cookie"]):
        self.name: str = name
        self.in_: Literal["query", "header", "path", "cookie"] = in_
        self.required: bool = False
        self.deprecated: bool = False
        self.allow_empty_value: bool = False
        self.schema: Schema | Reference | None = None
        self.description: str = ""
        self.style: (
            Literal[
                "matrix",
                "label",
                "form",
                "simple",
                "spaceDelimited",
                "pipeDelimited",
                "deepObject",
            ]
            | None
        ) = None
        self.explode: bool | None = None
        self.allow_reserved: bool = False
        self.example: Any | EllipsisType = ...
        self.examples: dict[str, Example | Reference] = {}
        self.content: dict[str, MediaType] = {}

        if self.in_ == "path":
            self.required = True

    def set_description(self, description: str) -> Parameter:
        self.description = description
        return self

    def set_required(self, required: bool) -> Parameter:
        self.required = required
        return self

    def set_deprecated(self, deprecated: bool) -> Parameter:
        self.deprecated = deprecated
        return self

    def set_schema(self, schema: Schema | Reference) -> Parameter:
        self.schema = schema
        return self

    def add_example(self, name: str, example: Example | Reference) -> Parameter:
        self.examples[name] = example
        return self

    def add_content(self, media_type: str, content: MediaType) -> Parameter:
        self.content[media_type] = content
        return self

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "in": self.in_,
            "required": self.required,
        }

        if self.description:
            data["description"] = self.description

        if self.deprecated:
            data["deprecated"] = self.deprecated

        if self.allow_empty_value:
            data["allowEmptyValue"] = self.allow_empty_value

        if self.schema:
            data["schema"] = self.schema.to_dict()

        if self.style:
            data["style"] = self.style

        if self.explode is not None:
            data["explode"] = self.explode

        if self.allow_reserved:
            data["allowReserved"] = self.allow_reserved

        if self.example is not ...:
            data["example"] = self.example

        if self.examples:
            data["examples"] = {k: v.to_dict() for k, v in self.examples.items()}

        if self.content:
            data["content"] = {
                media_type: content.to_dict()
                for media_type, content in self.content.items()
            }

        return data
