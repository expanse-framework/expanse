from __future__ import annotations

from typing import Any


class ServerVariable:
    """
    An object representing a Server Variable for server URL template substitution.
    """

    def __init__(self, default: str, description: str | None = None) -> None:
        """
        Initialize a ServerVariable object.

        Args:
            default: The default value to use for substitution, which SHALL be sent
                    if an alternate value is not supplied.
            description: An optional description for the server variable.
        """
        self.default: str = default
        self.description: str | None = description
        self.enum: list[str] = []

    def set_enum(self, values: list[str]) -> "ServerVariable":
        """
        Set enumeration of string values to be used if the substitution options
        are from a limited set.

        Args:
            values: An enumeration of string values. The array MUST NOT be empty.

        Returns:
            Self for method chaining
        """
        if not values:
            raise ValueError("Enum values cannot be empty")
        self.enum = values
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the ServerVariable object to a dictionary representation."""
        result: dict[str, Any] = {"default": self.default}

        if self.enum:
            result["enum"] = self.enum

        if self.description is not None:
            result["description"] = self.description

        return result

    def __repr__(self) -> str:
        return f"ServerVariable(default='{self.default}')"


class Server:
    """
    An object representing a Server.
    """

    def __init__(self, url: str, description: str | None = None) -> None:
        """
        Initialize a Server object.

        Args:
            url: A URL to the target host. This URL supports Server Variables and MAY be
                relative, to indicate that the host location is relative to the location
                where the OpenAPI document is being served.
            description: An optional string describing the host designated by the URL.
        """
        self.url: str = url
        self.description: str | None = description
        self.variables: dict[str, ServerVariable] = {}

    def add_variable(self, name: str, variable: ServerVariable) -> "Server":
        """
        Add a server variable.

        Args:
            name: The variable name
            variable: The server variable definition

        Returns:
            Self for method chaining
        """
        self.variables[name] = variable
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Server object to a dictionary representation."""
        result: dict[str, Any] = {"url": self.url}

        if self.description is not None:
            result["description"] = self.description

        if self.variables:
            result["variables"] = {
                name: var.to_dict() for name, var in self.variables.items()
            }

        return result

    def __repr__(self) -> str:
        return f"Server(url='{self.url}')"
