from __future__ import annotations

from typing import Any

from expanse.schematic.openapi.types.type import Type


class ObjectType(Type):
    def __init__(self) -> None:
        super().__init__("object")
        self.properties: dict[str, Any] = {}
        self.required: list[str] = []
        self.additional_properties: Any = None
        self.min_properties: int | None = None
        self.max_properties: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        if self.properties:
            properties_dict = {}
            for name, prop in self.properties.items():
                if hasattr(prop, "to_dict"):
                    properties_dict[name] = prop.to_dict()
                else:
                    properties_dict[name] = prop
            result["properties"] = properties_dict

        if self.required:
            result["required"] = self.required

        if self.additional_properties is not None:
            if hasattr(self.additional_properties, "to_dict"):
                result["additionalProperties"] = self.additional_properties.to_dict()
            else:
                result["additionalProperties"] = self.additional_properties

        if self.min_properties is not None:
            result["minProperties"] = self.min_properties

        if self.max_properties is not None:
            result["maxProperties"] = self.max_properties

        return result
