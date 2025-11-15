from __future__ import annotations

from typing import Any


class Type:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self.format: str | None = None
        self.description: str = ""
        self.content_media_type: str = ""
        self.content_encoding: str = ""
        self.example: Any = None
        self.default: Any = None
        self.examples: list[Any] = []
        self.enum: list[Any] = []
        self.nullable: bool = False

    def set_format(self, format: str) -> Type:
        self.format = format
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.name if not self.nullable else [self.name, "null"]
        }

        if self.format:
            result["format"] = self.format
        if self.description:
            result["description"] = self.description
        if self.content_media_type:
            result["contentMediaType"] = self.content_media_type
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
            result["nullable"] = True

        return result

    def __repr__(self):
        return f"Type({self.type})"
