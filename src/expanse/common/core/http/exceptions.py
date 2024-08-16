from collections.abc import MutableMapping
from http import HTTPStatus
from typing import Any


class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str | None = None,
        headers: MutableMapping[str, Any] | None = None,
    ) -> None:
        if detail is None:
            detail = HTTPStatus(status_code).phrase

        self.status_code = status_code
        self.detail = detail
        self.headers = headers

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"
