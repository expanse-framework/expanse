from __future__ import annotations

from typing import Any


class SecurityRequirement:
    """
    Lists the required security schemes to execute this operation.
    The name used for each property MUST correspond to a security scheme declared
    in the Security Schemes under the Components Object.

    Security Requirement Objects that contain multiple schemes require that all schemes
    MUST be satisfied for a request to be authorized. This enables support for scenarios
    where multiple query parameters or HTTP headers are required to convey security information.

    When a list of Security Requirement Objects is defined on the OpenAPI Object or Operation Object,
    only one of the Security Requirement Objects in the list needs to be satisfied to authorize the request.
    """

    def __init__(self) -> None:
        """Initialize a SecurityRequirement object."""
        self.requirements: dict[str, list[str]] = {}

    def add_requirement(
        self, name: str, scopes: list[str] | None = None
    ) -> SecurityRequirement:
        """
        Add a security requirement.

        Args:
            name: The name MUST correspond to a security scheme which is declared
                 in the Security Schemes under the Components Object.
            scopes: If the security scheme is of type "oauth2" or "openIdConnect",
                   then the value is a list of scope names required for the execution,
                   and the list MAY be empty if authorization does not require a specified scope.
                   For other security scheme types, the array MAY contain a list of role names
                   which are required for the execution, but are not otherwise defined or
                   exchanged in-band.

        Returns:
            Self for method chaining
        """
        self.requirements[name] = scopes or []
        return self

    def remove_requirement(self, name: str) -> SecurityRequirement:
        """
        Remove a security requirement.

        Args:
            name: The name of the security requirement to remove

        Returns:
            Self for method chaining
        """
        self.requirements.pop(name, None)
        return self

    def get_requirement(self, name: str) -> list[str] | None:
        """
        Get the scopes/roles for a security requirement.

        Args:
            name: The name of the security requirement

        Returns:
            The list of scopes/roles if the requirement exists, None otherwise
        """
        return self.requirements.get(name)

    def has_requirement(self, name: str) -> bool:
        """
        Check if a security requirement exists.

        Args:
            name: The name of the security requirement

        Returns:
            True if the requirement exists, False otherwise
        """
        return name in self.requirements

    def clear(self) -> SecurityRequirement:
        """
        Clear all security requirements.

        Returns:
            Self for method chaining
        """
        self.requirements.clear()
        return self

    def is_empty(self) -> bool:
        """
        Check if this security requirement is empty.

        Returns:
            True if no security requirements are defined, False otherwise
        """
        return len(self.requirements) == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert the SecurityRequirement object to a dictionary representation."""
        return dict(self.requirements)

    def __repr__(self) -> str:
        if self.is_empty():
            return "SecurityRequirement(empty)"
        else:
            return f"SecurityRequirement({len(self.requirements)} requirements)"

    def __len__(self) -> int:
        """Get the number of security requirements."""
        return len(self.requirements)

    def __contains__(self, name: str) -> bool:
        """Check if a security requirement exists."""
        return name in self.requirements

    def __iter__(self):
        """Iterate over security requirement names."""
        return iter(self.requirements)
