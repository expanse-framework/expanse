from base64 import b64encode
from typing import Any


class Message:
    def __init__(self, payload: bytes, headers: dict | None = None) -> None:
        self.payload: bytes = payload
        self.headers: dict[str, Any] = headers or {}

    def dump(self) -> dict[str, Any]:
        return {
            "p": (b64encode(self.payload).decode()),
            "h": self._dump_headers(self.headers),
        }

    def _dump_headers(self, headers: dict[str, Any]) -> dict[str, str]:
        to_dump: dict[str, str] = {}

        for key, value in headers.items():
            if isinstance(value, bytes):
                to_dump[key] = b64encode(value).decode()
            else:
                to_dump[key] = value

        return to_dump

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.payload!r}, {self.headers!r})"
