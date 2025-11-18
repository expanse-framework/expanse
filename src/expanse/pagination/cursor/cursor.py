from __future__ import annotations

import base64
import json

from typing import Any

from expanse.pagination.cursor.exceptions import InvalidCursorParameter


class Cursor:
    def __init__(self, parameters: dict[str, Any], reversed: bool = False) -> None:
        self._parameters: dict[str, Any] = parameters.copy()
        self._reversed = reversed

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    def parameter(self, name: str) -> Any:
        if name not in self._parameters:
            raise InvalidCursorParameter(name)

        return self._parameters[name]

    def is_reversed(self) -> bool:
        return self._reversed

    def revert(self) -> Cursor:
        return Cursor(self._parameters, reversed=not self._reversed)

    def dump(self) -> str:
        return json.dumps({"parameters": self._parameters, "reversed": self._reversed})

    def encode(self) -> str:
        return base64.urlsafe_b64encode(self.dump().encode()).decode()

    @classmethod
    def load(cls, value: str) -> Cursor | None:
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return None

        parameters = data.get("parameters") or {}
        is_reversed = data.get("reversed") or False

        return cls(parameters, is_reversed)

    @classmethod
    def decode(cls, value: str) -> Cursor | None:
        try:
            decoded = base64.urlsafe_b64decode(value.encode()).decode()
            return cls.load(decoded)
        except ValueError:
            return None

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Cursor):
            return NotImplemented

        return (
            self._parameters == value._parameters and self._reversed == value._reversed
        )
