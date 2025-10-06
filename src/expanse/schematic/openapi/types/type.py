from __future__ import annotations

class Type:
    def __init__(self, type: str):
        self.type = type
        self.format = ""
        self.description = ""
        self.content_type = ""
        self.content_encoding = ""
        self.example = None
        self.default = None
        self.examples = []
        self.enum = []
        self.nullable = False

    def to_dict(self) -> dict:
        result = {"type": self.type if not self.nullable else [self.type, "null"]}

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

    def __repr__(self):
        return f"Type({self.type_name})"
