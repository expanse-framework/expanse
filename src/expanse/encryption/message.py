import json

from base64 import b64decode
from base64 import b64encode
from base64 import urlsafe_b64decode
from base64 import urlsafe_b64encode
from typing import Any
from typing import TypedDict

from expanse.encryption.errors import MessageDecodeError


class Content(TypedDict):
    p: str
    h: dict[str, Any]


class Message:
    def __init__(self, payload: bytes, headers: dict | None = None) -> None:
        self.payload: bytes = payload
        self.headers: dict[str, Any] = headers or {}

    @classmethod
    def load(cls, value: str) -> "Message":
        try:
            content: Content = json.loads(value)
        except json.JSONDecodeError:
            raise MessageDecodeError("Invalid message format")

        return cls(
            b64decode(content["p"]),
            cls._load_headers(content["h"]),
        )

    @classmethod
    def decode(cls, value: str) -> "Message":
        try:
            decoded = urlsafe_b64decode(value.encode()).decode()
        except Exception:
            raise MessageDecodeError("Invalid message")

        return cls.load(decoded)

    @staticmethod
    def _load_headers(headers: dict[str, Any]) -> dict[str, Any]:
        to_load: dict[str, Any] = {}

        for key, value in headers.items():
            if isinstance(value, str):
                to_load[key] = b64decode(value)

                continue

            to_load[key] = value

        return to_load

    def dump(self) -> str:
        """
        Dump the message as a JSON string.
        """
        dumped: dict[str, Any] = {
            "p": (b64encode(self.payload).decode()),
            "h": self._dump_headers(self.headers),
        }

        return json.dumps(dumped)

    def encode(self) -> str:
        """
        Encode the message as a base64 string.
        """
        return urlsafe_b64encode(self.dump().encode()).decode()

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
