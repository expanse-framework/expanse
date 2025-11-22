from __future__ import annotations

from typing import Any

from expanse.schematic.openapi.types.type import Type


class NumberType(Type):
    def __init__(self) -> None:
        super().__init__("number")
        self.minimum: float | None = None
        self.maximum: float | None = None
        self.exclusive_minimum: float | None = None
        self.exclusive_maximum: float | None = None
        self.multiple_of: float | None = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.exclusive_minimum is not None:
            result["exclusiveMinimum"] = self.exclusive_minimum
        if self.exclusive_maximum is not None:
            result["exclusiveMaximum"] = self.exclusive_maximum
        if self.multiple_of is not None:
            result["multipleOf"] = self.multiple_of

        return result
