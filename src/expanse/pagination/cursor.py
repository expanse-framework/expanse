from __future__ import annotations

import base64
import json

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from expanse.pagination.exceptions import InvalidCursorParameter


if TYPE_CHECKING:
    from pydantic import BaseModel


class Cursor:
    def __init__(
        self,
        parameters: dict[str, Any],
        reversed: bool = False,
        schema: type[BaseModel] | None = None,
    ) -> None:
        self._parameters: dict[str, Any] = parameters.copy()
        self._reversed = reversed
        self.schema: type[BaseModel] | None = schema

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
        return Cursor(self._parameters, reversed=not self._reversed, schema=self.schema)

    def encode(self) -> str:
        if self.schema:
            parameters = self.schema.model_validate(self._parameters).model_dump(
                mode="json"
            )
        else:
            # Apply a naive encoding to make sure common parameters are JSON serializable
            parameters = {}
            for key, value in self._parameters.items():
                match key:
                    case "created" | "updated":
                        # Datetime are serialized as ISO 8601 strings
                        match value:
                            case datetime():
                                parameters[key] = value.isoformat()
                            case _:
                                parameters[key] = value
                    case _:
                        parameters[key] = value

        return base64.urlsafe_b64encode(
            json.dumps({"parameters": parameters, "reversed": self._reversed}).encode()
        ).decode()

    @classmethod
    def from_encoded(
        cls, encoded: str, schema: type[BaseModel] | None = None
    ) -> Cursor | None:
        try:
            decoded = base64.urlsafe_b64decode(encoded.encode()).decode()

            data = json.loads(decoded)
            parameters = data.get("parameters") or {}
            is_reversed = data.get("reversed") or False

            if schema:
                try:
                    parameters = schema.model_validate(parameters).model_dump()
                except Exception:
                    return None
            else:
                # Apply a naive decoding to restore common parameter types
                for key, value in parameters.items():
                    match key:
                        case "created" | "updated":
                            # Datetimes are unserialized back from ISO 8601 strings
                            match value:
                                case str():
                                    try:
                                        parameters[key] = datetime.fromisoformat(value)
                                    except ValueError:
                                        return None
                                case _:
                                    parameters[key] = value
                        case _:
                            parameters[key] = value

            return cls(parameters, is_reversed, schema=schema)
        except (ValueError, json.JSONDecodeError):
            return None

    def __repr__(self) -> str:
        return f"<Cursor parameters={self._parameters} reversed={self._reversed}>"

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Cursor):
            return NotImplemented

        return (
            self._parameters == value._parameters and self._reversed == value._reversed
        )
