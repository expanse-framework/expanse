from __future__ import annotations

from typing import Any

from expanse.schematic.openapi.types.type import Type


class StringType(Type):
    def __init__(self) -> None:
        super().__init__("string")
        self.min_length: int | None = None
        self.max_length: int | None = None
        self.pattern: str | None = None
        self.format: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        if self.min_length is not None:
            result["minLength"] = self.min_length
        if self.max_length is not None:
            result["maxLength"] = self.max_length
        if self.pattern:
            result["pattern"] = self.pattern

        return result

    def set_format(self, format: str) -> StringType:
        """
        Set the string format.

        Examples of valid format strings include:
        - "date" - full-date as defined by RFC3339
        - "date-time" - date-time as defined by RFC3339
        - "password" - hint to obscure the value
        - "byte" - base64 encoded characters
        - "binary" - binary data
        - "email" - email address
        - "uuid" - UUID string
        - "uri" - URI reference
        - "hostname" - hostname
        - "ipv4" - IPv4 address
        - "ipv6" - IPv6 address
        """
        self.format = format
        return self
