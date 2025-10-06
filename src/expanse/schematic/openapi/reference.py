from __future__ import annotations

from typing import Any


class Reference:
    """
    A simple object to allow referencing other components in the OpenAPI document,
    internally and externally.

    The $ref string value contains a URI, which identifies the location of the value being referenced.
    """

    def __init__(
        self, ref: str, summary: str | None = None, description: str | None = None
    ) -> None:
        """
        Initialize a Reference object.

        Args:
            ref: The reference identifier. This MUST be in the form of a URI.
            summary: A short summary which by default SHOULD override that of the referenced component.
            description: A description which by default SHOULD override that of the referenced component.
        """
        self.ref: str = ref
        self.summary: str | None = summary
        self.description: str | None = description

    def to_dict(self) -> dict[str, Any]:
        """Convert the Reference object to a dictionary representation."""
        result: dict[str, Any] = {"$ref": self.ref}

        if self.summary is not None:
            result["summary"] = self.summary

        if self.description is not None:
            result["description"] = self.description

        return result

    def __repr__(self) -> str:
        return f"Reference(ref='{self.ref}')"
