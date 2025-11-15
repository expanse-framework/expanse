from __future__ import annotations

from typing import Any


class ServerVariable:
    """
    An object representing a Server Variable for server URL template substitution.
    """

    def __init__(self, default: str, description: str | None = None) -> None:
        self.default: str = default
        self.description: str | None = description
        self.enum: list[str] = []

    def set_enum(self, values: list[str]) -> ServerVariable:
        if not values:
            raise ValueError("Enum values cannot be empty")
        self.enum = values
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"default": self.default}

        if self.enum:
            result["enum"] = self.enum

        if self.description is not None:
            result["description"] = self.description

        return result

    def __repr__(self) -> str:
        return f"ServerVariable(default='{self.default}')"


class Server:
    def __init__(self, url: str, description: str | None = None) -> None:
        self.url: str = url
        self.description: str | None = description
        self.variables: dict[str, ServerVariable] = {}

    def add_variable(self, name: str, variable: ServerVariable) -> Server:
        self.variables[name] = variable
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"url": self.url}

        if self.description is not None:
            result["description"] = self.description

        if self.variables:
            result["variables"] = {
                name: var.to_dict() for name, var in self.variables.items()
            }

        return result
