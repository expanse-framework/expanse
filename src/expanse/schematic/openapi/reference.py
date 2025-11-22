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
        self.ref: str = ref
        self.summary: str | None = summary
        self.description: str | None = description

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"$ref": self.ref}

        if self.summary is not None:
            result["summary"] = self.summary

        if self.description is not None:
            result["description"] = self.description

        return result
