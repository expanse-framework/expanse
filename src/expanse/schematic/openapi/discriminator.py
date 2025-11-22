from __future__ import annotations

from typing import Any


class Discriminator:
    def __init__(self, property_name: str) -> None:
        self.property_name: str = property_name
        self.mapping: dict[str, str] = {}

    def add_mapping(self, value: str, schema_ref: str) -> Discriminator:
        self.mapping[value] = schema_ref
        return self

    def set_mapping(self, mapping: dict[str, str]) -> Discriminator:
        self.mapping = mapping
        return self

    def remove_mapping(self, value: str) -> Discriminator:
        self.mapping.pop(value, None)
        return self

    def get_mapping(self, value: str) -> str | None:
        return self.mapping.get(value)

    def clear_mapping(self) -> Discriminator:
        self.mapping.clear()
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"propertyName": self.property_name}

        if self.mapping:
            result["mapping"] = self.mapping

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Discriminator:
        discriminator = cls(property_name=data["propertyName"])
        mapping = data.get("mapping", {})
        discriminator.set_mapping(mapping)

        return discriminator

    def __contains__(self, value: str) -> bool:
        return value in self.mapping

    def __len__(self) -> int:
        return len(self.mapping)
