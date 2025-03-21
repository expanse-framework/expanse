import json

from base64 import b64decode
from base64 import b64encode
from base64 import urlsafe_b64decode
from base64 import urlsafe_b64encode
from typing import Any
from typing import Literal
from typing import overload


class Message:
    def __init__(self, payload: bytes, headers: dict | None = None) -> None:
        self.payload: bytes = payload
        self.headers: dict[str, Any] = headers or {}

    @classmethod
    @overload
    def load(
        cls, serialized: dict[str, Any], fmt: Literal["dict"] = "dict"
    ) -> "Message": ...

    @classmethod
    @overload
    def load(cls, serialized: str, fmt: Literal["base64"] = "base64") -> "Message": ...

    @classmethod
    @overload
    def load(cls, serialized: str, fmt: Literal["json"] = "json") -> "Message": ...

    @classmethod
    def load(
        cls,
        serialized: dict[str, Any] | str,
        fmt: Literal["dict", "json", "base64"] = "dict",
    ) -> "Message":
        match fmt:
            case "json":
                if not isinstance(serialized, str):
                    raise ValueError("Invalid format")

                serialized = json.loads(serialized)
            case "base64":
                if not isinstance(serialized, str):
                    raise ValueError("Invalid format")

                serialized = json.loads(urlsafe_b64decode(serialized.encode()).decode())

        if not isinstance(serialized, dict):
            raise ValueError("Invalid format")

        return cls(
            b64decode(serialized["p"]),
            cls._load_headers(serialized["h"]),
        )

    @staticmethod
    def _load_headers(headers: dict[str, Any]) -> dict[str, Any]:
        to_load: dict[str, Any] = {}

        for key, value in headers.items():
            if isinstance(value, str):
                to_load[key] = b64decode(value)

                continue

            to_load[key] = value

        return to_load

    @overload
    def dump(self, fmt: Literal["dict"] = "dict") -> dict[str, Any]: ...

    @overload
    def dump(self, fmt: Literal["json"] = "json") -> str: ...

    @overload
    def dump(self, fmt: Literal["base64"] = "base64") -> str: ...

    def dump(
        self, fmt: Literal["dict", "json", "base64"] = "dict"
    ) -> dict[str, Any] | str:
        dumped: dict[str, Any] = {
            "p": (b64encode(self.payload).decode()),
            "h": self._dump_headers(self.headers),
        }

        match fmt:
            case "dict":
                return dumped
            case "json":
                return json.dumps(dumped)
            case "base64":
                return urlsafe_b64encode(json.dumps(dumped).encode()).decode()
            case _:
                raise ValueError("Invalid format")

    def _dump_headers(self, headers: dict[str, Any]) -> dict[str, str]:
        to_dump: dict[str, str] = {}

        for key, value in headers.items():
            if isinstance(value, bytes):
                to_dump[key] = b64encode(value).decode()
            elif isinstance(value, str):
                to_dump[key] = b64encode(value.encode()).decode()
            else:
                to_dump[key] = value

        return to_dump

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.payload!r}, {self.headers!r})"
