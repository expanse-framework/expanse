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
        self.requirements[name] = scopes or []
        return self

    def remove_requirement(self, name: str) -> SecurityRequirement:
        self.requirements.pop(name, None)
        return self

    def get_requirement(self, name: str) -> list[str] | None:
        return self.requirements.get(name)

    def has_requirement(self, name: str) -> bool:
        return name in self.requirements

    def clear(self) -> SecurityRequirement:
        self.requirements.clear()
        return self

    def is_empty(self) -> bool:
        return len(self.requirements) == 0

    def to_dict(self) -> dict[str, Any]:
        return dict(self.requirements)

    def __len__(self) -> int:
        return len(self.requirements)

    def __contains__(self, name: str) -> bool:
        return name in self.requirements

    def __iter__(self):
        return iter(self.requirements)
