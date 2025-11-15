from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.example import Example
    from expanse.schematic.openapi.header import Header
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.schema import Schema


class Encoding:
    def __init__(self, content_type: str | None = None) -> None:
        self.content_type: str | None = content_type
        self.headers: dict[str, Header | Reference] = {}
        self.style: str | None = None
        self.explode: bool | None = None
        self.allow_reserved: bool = False

    def set_style(self, style: str) -> Encoding:
        self.style = style
        return self

    def set_explode(self, explode: bool) -> Encoding:
        self.explode = explode
        return self

    def set_allow_reserved(self, allow_reserved: bool) -> Encoding:
        self.allow_reserved = allow_reserved
        return self

    def add_header(self, name: str, header: Header | Reference) -> Encoding:
        self.headers[name] = header
        return self

    def to_dict(self) -> dict[str, Any]:
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


class MediaType:
    def __init__(self, schema: Schema | Reference | None = None) -> None:
        self.schema: Schema | Reference | None = schema
        self.example: Any = None
        self.examples: dict[str, Example | Reference] = {}
        self.encoding: dict[str, Encoding] = {}

    def set_schema(self, schema: Schema) -> MediaType:
        self.schema = schema
        return self

    def set_example(self, example: Any) -> MediaType:
        self.example = example
        return self

    def add_example(self, name: str, example: Example | Reference) -> MediaType:
        self.examples[name] = example
        return self

    def add_encoding(self, property_name: str, encoding: Encoding) -> MediaType:
        self.encoding[property_name] = encoding
        return self

    def to_dict(self) -> dict[str, Any]:
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
