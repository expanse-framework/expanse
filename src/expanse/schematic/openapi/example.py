from __future__ import annotations

from typing import Any


class Example:
    """
    Example Object for OpenAPI specification.
    """

    def __init__(
        self,
        value: Any = ...,
        summary: str | None = None,
        description: str | None = None,
        external_value: str | None = None,
    ):
        """
        Initialize an Example object.

        Args:
            value: Embedded literal example. The value field and external_value field are mutually exclusive.
            summary: Short description for the example.
            description: Long description for the example. CommonMark syntax MAY be used for rich text representation.
            external_value: A URI that points to the literal example. The value field and external_value field are mutually exclusive.
        """
        self.summary: str | None = summary
        self.description: str | None = description
        self.value: Any = value
        self.external_value: str | None = external_value

    def set_summary(self, summary: str) -> Example:
        """Set the summary for the example."""
        self.summary = summary
        return self

    def set_description(self, description: str) -> Example:
        """Set the description for the example."""
        self.description = description
        return self

    def set_value(self, value: Any) -> Example:
        """Set the embedded literal example value."""
        self.value = value
        return self

    def set_external_value(self, external_value: str) -> Example:
        """Set the URI that points to the literal example."""
        self.external_value = external_value
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Example object to a dictionary representation."""
        result: dict[str, Any] = {}
        if self.summary is not None:
            result["summary"] = self.summary
        if self.description is not None:
            result["description"] = self.description
        if self.value is not ...:
            result["value"] = self.value
        if self.external_value is not None:
            result["externalValue"] = self.external_value

        return result

    def __repr__(self) -> str:
        return f"Example(summary='{self.summary}')"
