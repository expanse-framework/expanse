from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.external_documentation import ExternalDocumentation


class ExternalDocumentation:
    """
    Allows referencing an external resource for extended documentation.
    """

    def __init__(self, url: str, description: str | None = None) -> None:
        """
        Initialize an ExternalDocumentation object.

        Args:
            url: The URL for the target documentation. This MUST be in the form of a URL.
            description: A description of the target documentation. CommonMark syntax MAY be used
                        for rich text representation.
        """
        self.url: str = url
        self.description: str | None = description

    def set_description(self, description: str) -> ExternalDocumentation:
        """
        Set a description of the target documentation.

        Args:
            description: A description of the target documentation.

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the ExternalDocumentation object to a dictionary representation."""
        result: dict[str, Any] = {"url": self.url}

        if self.description is not None:
            result["description"] = self.description

        return result

    def __repr__(self) -> str:
        return f"ExternalDocumentation(url='{self.url}')"


class Tag:
    """
    Adds metadata to a single tag that is used by the Operation Object.
    It is not mandatory to have a Tag Object per tag defined in the Operation Object instances.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize a Tag object.

        Args:
            name: The name of the tag.
        """
        self.name: str = name
        self.description: str | None = None
        self.external_docs: ExternalDocumentation | None = None

    def set_description(self, description: str) -> Tag:
        """
        Set a description for the tag.

        Args:
            description: A description for the tag. CommonMark syntax MAY be used
                        for rich text representation.

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def set_external_docs(self, external_docs: ExternalDocumentation) -> Tag:
        """
        Set additional external documentation for this tag.

        Args:
            external_docs: Additional external documentation for this tag.

        Returns:
            Self for method chaining
        """
        self.external_docs = external_docs
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Tag object to a dictionary representation."""
        result: dict[str, Any] = {"name": self.name}

        if self.description is not None:
            result["description"] = self.description

        if self.external_docs is not None:
            result["externalDocs"] = self.external_docs.to_dict()

        return result

    def __repr__(self) -> str:
        return f"Tag(name='{self.name}')"
