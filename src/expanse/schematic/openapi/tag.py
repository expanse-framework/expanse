from __future__ import annotations

from typing import Any


class ExternalDocumentation:
    """
    Allows referencing an external resource for extended documentation.
    """

    def __init__(self, url: str, description: str | None = None) -> None:
        self.url: str = url
        self.description: str | None = description

    def set_description(self, description: str) -> ExternalDocumentation:
        self.description = description
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"url": self.url}

        if self.description is not None:
            result["description"] = self.description

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExternalDocumentation:
        url: str = data["url"]
        description: str | None = data.get("description")

        instance = cls(url=url)
        if description is not None:
            instance.set_description(description)

        return instance

    def __repr__(self) -> str:
        return f"ExternalDocumentation(url='{self.url}')"


class Tag:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self.description: str | None = None
        self.external_docs: ExternalDocumentation | None = None

    def set_description(self, description: str) -> Tag:
        self.description = description
        return self

    def set_external_docs(self, external_docs: ExternalDocumentation) -> Tag:
        self.external_docs = external_docs
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name}

        if self.description is not None:
            result["description"] = self.description

        if self.external_docs is not None:
            result["externalDocs"] = self.external_docs.to_dict()

        return result

    def __repr__(self) -> str:
        return f"Tag(name='{self.name}')"
