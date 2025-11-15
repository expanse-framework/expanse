from __future__ import annotations

from typing import Any


class Example:
    def __init__(
        self,
        value: Any = ...,
        summary: str | None = None,
        description: str | None = None,
        external_value: str | None = None,
    ) -> None:
        self.summary: str | None = summary
        self.description: str | None = description
        self.value: Any = value
        self.external_value: str | None = external_value

    def set_summary(self, summary: str) -> Example:
        self.summary = summary
        return self

    def set_description(self, description: str) -> Example:
        self.description = description
        return self

    def set_value(self, value: Any) -> Example:
        self.value = value
        return self

    def set_external_value(self, external_value: str) -> Example:
        self.external_value = external_value
        return self

    def to_dict(self) -> dict[str, Any]:
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
